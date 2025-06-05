# kubeSol/projects/manager.py
"""
Core logic for managing KubeSol projects and environments.
Interacts with the k8s_api module to manipulate namespaces and their labels.
"""
import uuid
import re # Import re for sanitizing environment names in _get_physical_namespace_name
from kubeSol.engine import k8s_api 
from kubeSol.constants import (
    PROJECT_ID_LABEL_KEY, 
    PROJECT_NAME_LABEL_KEY, 
    ENVIRONMENT_LABEL_KEY,
    DEFAULT_PROJECT_ENVIRONMENT,
    GITHUB_REPO_PREFIX,
    GITHUB_DEFAULT_BRANCH_NAME,
    GITHUB_DEV_BRANCH_NAME,
    PROJECT_REPO_NAME_LABEL_KEY,
    GITHUB_SCRIPTS_FOLDER,
    PROJECT_REPO_URL_ANNOTATION_KEY
)
from kubeSol.integrations import github_api

# --- Internal Helper Functions ---

def _generate_project_id() -> str:
    return f"proj-{uuid.uuid4().hex[:12]}"

def _get_physical_namespace_name(project_id: str, environment_name: str) -> str:
    env_name_sanitized = re.sub(r'[^a-z0-9-]+', '-', environment_name).strip('-')
    if not env_name_sanitized: env_name_sanitized = "env"
    return f"{project_id}-{env_name_sanitized}"[:63]

def _check_project_display_name_exists(user_project_name_lower: str) -> str | None:
    label_selector = f"{PROJECT_NAME_LABEL_KEY}={user_project_name_lower}"
    namespaces = k8s_api.list_k8s_namespaces(label_selector=label_selector)
    project_ids_found = set()
    if namespaces:
        for ns_obj in namespaces:
            if ns_obj.metadata and ns_obj.metadata.labels:
                proj_id = ns_obj.metadata.labels.get(PROJECT_ID_LABEL_KEY)
                if proj_id: project_ids_found.add(proj_id)
    if not project_ids_found: return None
    if len(project_ids_found) > 1:
        print(f"⚠️ Warning: Project name '{user_project_name_lower}' associated with multiple IDs: {project_ids_found}.")
    return list(project_ids_found)[0]


def _resolve_project_id_from_display_name(user_project_name_lower: str) -> str | None:
    """
    Finds the unique project_id for a given user_project_name.
    Returns project_id if found and unique, else None.
    """
    label_selector = f"{PROJECT_NAME_LABEL_KEY}={user_project_name_lower}"
    namespaces = k8s_api.list_k8s_namespaces(label_selector=label_selector)

    project_ids = set()
    if namespaces:
        for ns_obj in namespaces:
            if ns_obj.metadata and ns_obj.metadata.labels and PROJECT_ID_LABEL_KEY in ns_obj.metadata.labels:
                project_ids.add(ns_obj.metadata.labels[PROJECT_ID_LABEL_KEY])

    if not project_ids:
        print(f"ℹ️ Project with display name '{user_project_name_lower}' not found.")
        return None
    if len(project_ids) > 1:
        print(f"❌ Error: Ambiguous project display name '{user_project_name_lower}'. Multiple project IDs found: {project_ids}.")
        print(f"   This indicates an inconsistent state. Please resolve label conflicts or use Project ID for operations.")
        return None
    return list(project_ids)[0]

def _get_project_github_repo_name(project_display_name: str) -> str:
    """Genera el nombre del repositorio de GitHub para un proyecto."""
    sanitized_name = re.sub(r'[^a-z0-9-]+', '-', project_display_name.lower()).strip('-')
    return f"{GITHUB_REPO_PREFIX}{sanitized_name}"

def _get_github_branch_name_for_env(env_name: str) -> str:
    """Mapea un nombre de entorno a un nombre de rama de GitHub si es necesario."""
    # Podrías tener lógica más compleja aquí, ej. 'prod' -> 'master', 'dev' -> 'develop'
    # Por ahora, simplemente sanitizamos el nombre del entorno.
    return re.sub(r'[^a-z0-9-]+', '-', env_name.lower()).strip('-')

# --- Public Management Functions ---

def create_new_project(user_project_name: str) -> tuple[str | None, str | None, str | None, str | None]:
    print(f"Attempting to create new project with display name: '{user_project_name}'...")
    existing_project_id = _check_project_display_name_exists(user_project_name)
    if existing_project_id:
        print(f"❌ Error: Project with display name '{user_project_name}' already exists (ID: '{existing_project_id}').")
        return None, None, None, None

    project_id = _generate_project_id()
    default_env = DEFAULT_PROJECT_ENVIRONMENT
    namespace_name = _get_physical_namespace_name(project_id, default_env)

    project_repo_name = _get_project_github_repo_name(user_project_name)
    project_repo_url = None

    # 1. Crear el repositorio de GitHub
    print(f"ℹ️ Creating GitHub repository '{project_repo_name}' for project '{user_project_name}'...")
    project_repo_url = github_api.create_github_repository(
        repo_name=project_repo_name,
        description=f"KubeSol project '{user_project_name}' (ID: {project_id})"
    )
    if not project_repo_url:
        print(f"❌ Failed to create GitHub repository '{project_repo_name}'. Aborting project creation.")
        return None, None, None, None

    # 2. Empujar un commit inicial a la rama por defecto (main)
    # Esto es CRUCIAL para que el repositorio no esté vacío y se puedan crear ramas a partir de ella.
    readme_content = f"# KubeSol Project: {user_project_name}\n\nThis repository holds scripts and configurations for the KubeSol project '{user_project_name}'.\n"
    if not github_api.create_or_update_github_file(
        repo_name=project_repo_name,
        branch_name=GITHUB_DEFAULT_BRANCH_NAME, # 'main'
        file_path="README.md",
        commit_message="Initial commit: Add README.md",
        content=readme_content
    ):
        print(f"❌ Failed to push initial commit to '{GITHUB_DEFAULT_BRANCH_NAME}' branch in '{project_repo_name}'. Aborting project creation.")
        # Considerar cleanup: borrar repo de github si falla el commit inicial
        return None, None, None, None
    print(f"✅ Initial commit pushed to '{GITHUB_DEFAULT_BRANCH_NAME}' branch in '{project_repo_name}'.")


    # 3. Crear la rama de desarrollo (develop) en GitHub
    dev_git_branch_name = GITHUB_DEV_BRANCH_NAME # Esta es la rama 'develop'
    if not github_api.create_github_branch(
        repo_name=project_repo_name,
        branch_name=dev_git_branch_name,
        base_branch=GITHUB_DEFAULT_BRANCH_NAME # Ahora 'main' tiene un commit y esto debería funcionar
    ):
        print(f"❌ Failed to create '{dev_git_branch_name}' branch in GitHub repository '{project_repo_name}'. Aborting project creation.")
        # Considerar cleanup: borrar repo de github si no se creó la rama
        return None, None, None, None
    print(f"✅ GitHub branch '{dev_git_branch_name}' created in '{project_repo_name}'.")


    # 4. Crear el namespace de Kubernetes
    labels = {
        PROJECT_ID_LABEL_KEY: project_id,
        PROJECT_NAME_LABEL_KEY: user_project_name,
        ENVIRONMENT_LABEL_KEY: default_env,
        PROJECT_REPO_NAME_LABEL_KEY: project_repo_name, # <--- Sigue siendo LABEL
    }
    annotations = { # <--- NUEVO: Las URLs como ANOTACIONES
        PROJECT_REPO_URL_ANNOTATION_KEY: project_repo_url #
    }

    if k8s_api.create_k8s_namespace(name=namespace_name, labels=labels, annotations=annotations): # <--- Pasar annotations
        print(f"✅ Project '{user_project_name}' (ID: {project_id}) created.")
        print(f"   Default environment '{default_env}' (Namespace: '{namespace_name}') created and labeled.")
        print(f"   GitHub repository: {project_repo_url} (Branches: {GITHUB_DEFAULT_BRANCH_NAME}, {dev_git_branch_name})")
        return project_id, default_env, namespace_name, user_project_name
    
    print(f"❌ Failed to create default namespace '{namespace_name}' for project '{user_project_name}'. Aborting.")
    # Considerar cleanup: borrar repo y ramas de github si no se creó el namespace
    return None, None, None, None


def add_environment_to_project(project_id: str, user_project_name: str, new_env_name: str, parent_env_name: str | None = None) -> str | None:
    print(f"Attempting to add environment '{new_env_name}' to project '{user_project_name}' (ID: {project_id})...")
    if not project_id or not user_project_name:
        print("❌ Internal Error: Project ID or Project Name not provided to add_environment_to_project.")
        return None

    namespace_name = _get_physical_namespace_name(project_id, new_env_name)
    existing_ns = k8s_api.get_k8s_namespace(namespace_name)
    if existing_ns:
        print(f"ℹ️ Environment '{new_env_name}' (Namespace: '{namespace_name}') already exists for project '{user_project_name}'.")
        return namespace_name

    project_repo_name = None
    project_repo_url = None

    project_namespaces = k8s_api.list_k8s_namespaces(label_selector=f"{PROJECT_ID_LABEL_KEY}={project_id}")
    if project_namespaces:
        first_ns_labels = project_namespaces[0].metadata.labels
        first_ns_annotations = project_namespaces[0].metadata.annotations # Obtener anotaciones
        project_repo_name = first_ns_labels.get(PROJECT_REPO_NAME_LABEL_KEY)
        project_repo_url = first_ns_annotations.get(PROJECT_REPO_URL_ANNOTATION_KEY) # <--- Leer de ANOTACION
        
    if not project_repo_name or not project_repo_url: # project_repo_url también es necesario
        print(f"❌ Error: Could not determine GitHub repository name or URL for project '{user_project_name}' (ID: {project_id}). "
              "Please ensure the project's namespaces are correctly labeled/annotated.")
        return None

    new_env_git_branch_name = _get_github_branch_name_for_env(new_env_name)
    base_git_branch_name = GITHUB_DEFAULT_BRANCH_NAME

    if parent_env_name:
        base_git_branch_name = _get_github_branch_name_for_env(parent_env_name)
        print(f"ℹ️ Creating GitHub branch '{new_env_git_branch_name}' based on parent environment '{parent_env_name}' (Git branch: '{base_git_branch_name}')...")
        if not github_api.create_github_branch(
            repo_name=project_repo_name,
            branch_name=new_env_git_branch_name,
            base_branch=base_git_branch_name
        ):
            print(f"❌ Failed to create GitHub branch '{new_env_git_branch_name}' from '{base_git_branch_name}'. Aborting environment creation.")
            return None
        print(f"✅ GitHub branch '{new_env_git_branch_name}' created in '{project_repo_name}'.")
    else:
        print(f"ℹ️ No parent environment specified. Creating GitHub branch '{new_env_git_branch_name}' from default branch '{GITHUB_DEFAULT_BRANCH_NAME}'...")
        if not github_api.create_github_branch(
            repo_name=project_repo_name,
            branch_name=new_env_git_branch_name,
            base_branch=GITHUB_DEFAULT_BRANCH_NAME
        ):
            print(f"❌ Failed to create GitHub branch '{new_env_git_branch_name}' from '{GITHUB_DEFAULT_BRANCH_NAME}'. Aborting environment creation.")
            return None
        print(f"✅ GitHub branch '{new_env_git_branch_name}' created in '{project_repo_name}'.")

    labels = {
        PROJECT_ID_LABEL_KEY: project_id,
        PROJECT_NAME_LABEL_KEY: user_project_name,
        ENVIRONMENT_LABEL_KEY: new_env_name,
        PROJECT_REPO_NAME_LABEL_KEY: project_repo_name, # <--- Sigue siendo LABEL
    }
    annotations = { # <--- NUEVO: Las URLs como ANOTACIONES
        PROJECT_REPO_URL_ANNOTATION_KEY: project_repo_url #
    }

    if k8s_api.create_k8s_namespace(name=namespace_name, labels=labels, annotations=annotations): # <--- Pasar annotations
        print(f"✅ Environment '{new_env_name}' created for project '{user_project_name}' (Namespace: '{namespace_name}').")
        print(f"   Associated GitHub branch: {new_env_git_branch_name}")
        return namespace_name
    
    print(f"❌ Failed to create namespace '{namespace_name}' for environment '{new_env_name}'. Aborting.")
    return None

def update_project_display_name_label(old_display_name: str, new_display_name: str) -> bool:
    # ... (lógica existente, añadir update del repo name en GitHub si el repo name también cambia,
    # aunque no es común renombrar repos de GitHub al cambiar el display name)
    # Por ahora, solo se actualiza la etiqueta en los namespaces. El nombre del repo de GitHub
    # se mantiene como el original.
    # Si quisieras renombrar el repo de GitHub, sería una operación separada y compleja en la API de GitHub.
    # ... (resto de la función)
    if old_display_name == new_display_name:
        print(f"ℹ️ New display name ('{new_display_name}') is the same as the old one ('{old_display_name}'). No update performed.")
        return True # No change needed, considered a success.

    print(f"Attempting to update project display name from '{old_display_name}' to '{new_display_name}'...")

    project_id_to_update = _resolve_project_id_from_display_name(old_display_name)
    if not project_id_to_update:
        return False

    new_name_existing_project_id = _check_project_display_name_exists(new_display_name)
    if new_name_existing_project_id and new_name_existing_project_id != project_id_to_update:
        print(f"❌ Cannot update display name to '{new_display_name}': this name is already in use by project ID '{new_name_existing_project_id}'.")
        print(f"   KubeSol project display names must be unique.")
        return False

    label_selector_for_id = f"{PROJECT_ID_LABEL_KEY}={project_id_to_update}"
    namespaces_to_update = k8s_api.list_k8s_namespaces(label_selector=label_selector_for_id)
    
    if not namespaces_to_update:
        print(f"ℹ️ No namespaces found for project ID '{project_id_to_update}' (originally display name '{old_display_name}').")
        return True

    updated_ns_count = 0
    total_ns_to_update = len(namespaces_to_update)
    print(f"Found {total_ns_to_update} environment(s) for project ID '{project_id_to_update}'. Attempting to update their display name label...")

    for ns_obj in namespaces_to_update:
        ns_name = ns_obj.metadata.name
        # También actualiza el PROJECT_REPO_NAME_LABEL_KEY si el nombre del repositorio depende del display_name
        # Pero el nombre del repo se basa en el nombre del proyecto original, no cambia con el display name.
        # Solo actualizamos el label PROJECT_NAME_LABEL_KEY
        if k8s_api.update_k8s_namespace_labels(ns_name, {PROJECT_NAME_LABEL_KEY: new_display_name}):
            updated_ns_count += 1
        else:
            print(f"⚠️ Failed to update label for namespace '{ns_name}'.")
            
    if updated_ns_count == total_ns_to_update:
        print(f"✅ Successfully updated project display name to '{new_display_name}' for all {updated_ns_count} namespace(s) of project ID '{project_id_to_update}'.")
        return True
    elif updated_ns_count > 0:
        print(f"⚠️ Partially updated project display name. Only {updated_ns_count} out of {total_ns_to_update} namespaces were updated for project ID '{project_id_to_update}'.")
        return False
    else:
        print(f"❌ No namespace display name labels were successfully updated for project ID '{project_id_to_update}'.")
        return False

def get_all_project_details() -> list[dict]:
    """Retrieves details of all KubeSol projects, including environment names."""
    namespaces = k8s_api.list_k8s_namespaces(label_selector=PROJECT_ID_LABEL_KEY)
    projects_data = {} # Key: project_id, Value: {"display_names": set(), "environments": set()}
    
    if namespaces:
        for ns_obj in namespaces:
            labels = ns_obj.metadata.labels
            if labels:
                proj_id = labels.get(PROJECT_ID_LABEL_KEY)
                proj_name_label = labels.get(PROJECT_NAME_LABEL_KEY)
                env_name_label = labels.get(ENVIRONMENT_LABEL_KEY)
                if proj_id: 
                    if proj_id not in projects_data:
                        projects_data[proj_id] = {"display_names": set(), "environments": set()}
                    if proj_name_label:
                         projects_data[proj_id]["display_names"].add(proj_name_label)
                    if env_name_label:
                        projects_data[proj_id]["environments"].add(env_name_label) # Almacenar nombres de entorno
    
    output_list = []
    for proj_id, data in projects_data.items():
        display_name_str = ", ".join(sorted(list(data["display_names"]))) if data["display_names"] else "[No Display Name Label]"
        if len(data["display_names"]) > 1: display_name_str += " (Warning: Inconsistent display names for this ID)"
        
        # MODIFICADO: Añadir lista de nombres de entornos
        environment_names_list = sorted(list(data["environments"]))
        
        output_list.append({
            "project_id": proj_id, 
            "project_display_name": display_name_str,
            "environment_count": len(environment_names_list),
            "environment_names": environment_names_list # NUEVA CLAVE
        })
            
    return sorted(output_list, key=lambda x: x["project_display_name"])

def get_environments_for_project(user_project_name: str) -> list[dict] | None:
    # user_project_name ya viene en minúsculas
    # ... (lógica como antes, ya debería funcionar con nombres en minúsculas para la búsqueda por etiquetas) ...
    project_id = _resolve_project_id_from_display_name(user_project_name)
    if not project_id: return None 
    label_selector_for_id = f"{PROJECT_ID_LABEL_KEY}={project_id}"
    namespaces = k8s_api.list_k8s_namespaces(label_selector=label_selector_for_id)
    environments_info = []
    # ... (el resto de la función como estaba, ya que obtiene los valores de las etiquetas, que ahora serán minúsculas) ...
    if namespaces:
        for ns_obj in namespaces:
            labels = ns_obj.metadata.labels
            if labels:
                env_name = labels.get(ENVIRONMENT_LABEL_KEY)
                actual_display_name = labels.get(PROJECT_NAME_LABEL_KEY, user_project_name) 
                if env_name:
                    environments_info.append({
                        "environment": env_name, "namespace": ns_obj.metadata.name,
                        "project_id": project_id, "project_display_name": actual_display_name,
                        "status": ns_obj.status.phase if ns_obj.status else "N/A",
                        "created": ns_obj.metadata.creation_timestamp.isoformat() if ns_obj.metadata.creation_timestamp else "N/A" })
    if not environments_info: print(f"ℹ️ No environments found for project '{user_project_name}' (ID: {project_id})."); return None
    return sorted(environments_info, key=lambda x: x["environment"])

def delete_whole_project(user_project_name: str, force_delete: bool = False) -> bool:
    project_id = _resolve_project_id_from_display_name(user_project_name)
    if not project_id: return False

    label_selector_for_id = f"{PROJECT_ID_LABEL_KEY}={project_id}"
    namespaces_to_delete = k8s_api.list_k8s_namespaces(label_selector=label_selector_for_id)
    
    project_repo_name = None
    project_repo_url = None
    if namespaces_to_delete:
        first_ns_labels = namespaces_to_delete[0].metadata.labels
        project_repo_name = first_ns_labels.get(PROJECT_REPO_NAME_LABEL_KEY)
        
        first_ns_annotations = namespaces_to_delete[0].metadata.annotations # NUEVO
        project_repo_url = first_ns_annotations.get(PROJECT_REPO_URL_ANNOTATION_KEY) # NUEVO

    if not namespaces_to_delete:
        print(f"ℹ️ No environments for project '{user_project_name}' (ID: {project_id}). Nothing to delete."); return True
    
    print(f"🚨 Project '{user_project_name}' (ID: {project_id}) environments to be DELETED:");
    for ns in namespaces_to_delete: print(f"  - NS: {ns.metadata.name} (Env: {ns.metadata.labels.get(ENVIRONMENT_LABEL_KEY, 'N/A')})")
    if project_repo_name:
        repo_link = f" ({project_repo_url})" if project_repo_url else ""
        print(f"   Associated GitHub repository: '{project_repo_name}'{repo_link} WILL NOT BE DELETED AUTOMATICALLY.")
        print("   Please delete the GitHub repository manually if desired.")

    if not force_delete:
        confirm = input(f"CONFIRM DELETION of ALL listed namespaces for project '{user_project_name}' by typing project name: ")
        if confirm != user_project_name: print("Deletion cancelled."); return False

    deleted_count, failed_names = 0, []
    for ns in namespaces_to_delete:
        if k8s_api.delete_k8s_namespace(ns.metadata.name): deleted_count += 1
        else: failed_names.append(ns.metadata.name)
    
    if failed_names: print(f"❌ Finished. {deleted_count} env(s) deleted. Failed: {failed_names}"); return False
    print(f"✅ Project '{user_project_name}' and its {deleted_count} environment(s) deleted."); return True



def delete_project_environment(project_id: str, user_project_name_for_msg: str, env_name: str, force_delete: bool = False) -> bool:
    namespace_name = _get_physical_namespace_name(project_id, env_name)
    ns_obj = k8s_api.get_k8s_namespace(namespace_name)
    
    if not ns_obj:
        print(f"❌ NS '{namespace_name}' for env '{env_name}' of project '{user_project_name_for_msg}' not found."); return False
    
    labels = ns_obj.metadata.labels
    annotations = ns_obj.metadata.annotations # NUEVO: Obtener anotaciones
    if not (labels and labels.get(PROJECT_ID_LABEL_KEY) == project_id and labels.get(ENVIRONMENT_LABEL_KEY) == env_name):
        print(f"❌ Safety check: NS '{namespace_name}' labels don't match project ID '{project_id}' / env '{env_name}'. Labels: {labels}. Aborting."); return False

    project_repo_name = labels.get(PROJECT_REPO_NAME_LABEL_KEY)
    project_repo_url = annotations.get(PROJECT_REPO_URL_ANNOTATION_KEY) # NUEVO: Obtener URL de anotación
    env_git_branch_name = _get_github_branch_name_for_env(env_name)

    if not force_delete:
        confirm_msg = f"CONFIRM DELETION of env '{env_name}' (NS '{namespace_name}') for project '{user_project_name_for_msg}'"
        if project_repo_name:
            repo_link = f" ({project_repo_url})" if project_repo_url else ""
            confirm_msg += f"\n   Associated GitHub branch '{env_git_branch_name}' in repo '{project_repo_name}'{repo_link} WILL NOT BE DELETED AUTOMATICALLY."
            confirm_msg += "\n   Please delete the GitHub branch manually if desired."
        confirm = input(f"{confirm_msg}\nType 'yes': ")
        if confirm.lower() != 'yes': print("Deletion cancelled."); return False

    if k8s_api.delete_k8s_namespace(namespace_name):
        print(f"✅ Env '{env_name}' (NS '{namespace_name}') deleted."); return True
    return False

def resolve_project_and_environment_namespaces(user_project_name: str, environment_name: str) -> tuple[str | None, str | None, str | None, str | None]:
    project_id = _resolve_project_id_from_display_name(user_project_name)
    if not project_id: return None, None, None, f"Project '{user_project_name}' not found or ambiguous."
    physical_namespace = _get_physical_namespace_name(project_id, environment_name)
    ns_obj = k8s_api.get_k8s_namespace(physical_namespace)
    if not ns_obj: return project_id, user_project_name, None, f"Env '{environment_name}' (NS '{physical_namespace}') not found for project '{user_project_name}' (ID: {project_id})."
    # Consistency check for labels (optional, for stricter validation)
    # ...
    return project_id, user_project_name, physical_namespace, None