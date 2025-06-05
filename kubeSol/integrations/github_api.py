from github import Github, UnknownObjectException, GithubException
from github.AuthenticatedUser import AuthenticatedUser # Importar este tipo específico
from github.Organization import Organization # Importar este tipo específico
from github.NamedUser import NamedUser # Para referencia, pero no se usará create_repo en este
import os
import base64
from kubeSol.constants import GITHUB_ORG_OR_USER, GITHUB_TOKEN_SECRET_NAME, PROJECT_ID_LABEL_KEY, PROJECT_NAME_LABEL_KEY

try:
    from kubeSol.engine import k8s_api
except ImportError as e:
    print(f"🚨 Critical ImportError: Could not load kubeSol.engine.k8s_api module: {e}")
    k8s_api = None # Asegurarse de que k8s_api sea None si la importación falla

_github_client = None

def _get_github_client():
    global _github_client
    if _github_client is None:
        try:
            secret_data = k8s_api.get_secret_data(name=GITHUB_TOKEN_SECRET_NAME, namespace='argocd')
            if not secret_data or 'token' not in secret_data:
                raise ValueError(f"GitHub token not found in Secret '{GITHUB_TOKEN_SECRET_NAME}' in namespace 'argocd' or missing 'token' key.")
            
            github_token = secret_data['token']
            _github_client = Github(github_token)
            
            user = _github_client.get_user()
            print(f"✅ GitHub client initialized successfully for user: {user.login}")
            
        except UnknownObjectException:
            print(f"❌ GitHub token invalid or insufficient permissions for user or organization access.")
            _github_client = None
        except GithubException as e:
            print(f"❌ GitHub API error during client initialization: {e}")
            _github_client = None
        except ValueError as e:
            print(f"❌ Configuration error for GitHub client: {e}")
            _github_client = None
        except Exception as e:
            print(f"❌ Unexpected error during GitHub client initialization: {type(e).__name__} - {e}")
            _github_client = None
    return _github_client


def _get_target_entity(client: Github):
    """
    Returns the target entity (AuthenticatedUser or Organization) where repos/branches will be managed.
    Handles GITHUB_ORG_OR_USER configuration.
    """
    if not client: return None
    
    if GITHUB_ORG_OR_USER:
        try:
            # Intentar obtener como organización
            org = client.get_organization(GITHUB_ORG_OR_USER)
            return org
        except UnknownObjectException:
            # Si no es una organización, y GITHUB_ORG_OR_USER es el mismo que el usuario autenticado,
            # usamos el objeto AuthenticatedUser.
            authenticated_user = client.get_user()
            if authenticated_user.login == GITHUB_ORG_OR_USER:
                return authenticated_user
            else:
                print(f"❌ Configured GitHub entity '{GITHUB_ORG_OR_USER}' is not an organization, and does not match the authenticated user '{authenticated_user.login}'. Cannot operate on arbitrary users.")
                return None
        except Exception as e:
            print(f"❌ Error resolving target GitHub entity '{GITHUB_ORG_OR_USER}': {e}")
            return None
    else:
        # Si no se especifica GITHUB_ORG_OR_USER, operamos bajo el usuario autenticado.
        return client.get_user()

def _get_repo_object(client: Github, repo_name: str):
    """
    Retrieves the GitHub Repository object.
    Uses _get_target_entity to determine where to look for the repo.
    """
    target_entity = _get_target_entity(client)
    if not target_entity: return None

    try:
        if isinstance(target_entity, Organization):
            return target_entity.get_repo(repo_name)
        elif isinstance(target_entity, AuthenticatedUser):
            return target_entity.get_repo(repo_name)
        else:
            print(f"❌ Internal Error: Unexpected target entity type: {type(target_entity)}")
            return None
    except UnknownObjectException:
        print(f"🤷 Repository '{repo_name}' not found under '{target_entity.login}'.")
        return None
    except GithubException as e:
        print(f"❌ GitHub API error getting repository '{repo_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error getting repository '{repo_name}': {type(e).__name__} - {e}")
        return None

def _get_organization_or_user(client):
    """Gets the target organization or user object from GitHub."""
    try:
        if GITHUB_ORG_OR_USER:
            # Check if it's an organization or a user
            try:
                org = client.get_organization(GITHUB_ORG_OR_USER)
                return org
            except UnknownObjectException:
                # If not an org, try as user
                user = client.get_user(GITHUB_ORG_OR_USER)
                return user
        else:
            return client.get_user() # Default to authenticated user
    except Exception as e:
        print(f"❌ Error getting GitHub organization/user '{GITHUB_ORG_OR_USER}': {e}")
        return None

def create_github_repository(repo_name: str, description: str = "") -> str | None:
    """Creates a new GitHub repository."""
    client = _get_github_client()
    if not client: return None

    target_entity = _get_target_entity(client)
    if not target_entity: return None

    try:
        print(f"ℹ️ Attempting to create GitHub repository '{repo_name}' under '{target_entity.login}'...")
        
        # Llama a create_repo en el objeto de entidad correcto
        if isinstance(target_entity, Organization):
            repo = target_entity.create_repo(repo_name, description=description, private=False)
        elif isinstance(target_entity, AuthenticatedUser):
            repo = target_entity.create_repo(repo_name, description=description, private=False)
        else:
            print(f"❌ Internal Error: Cannot create repository on unexpected entity type: {type(target_entity)}")
            return None
            
        print(f"✅ GitHub repository '{repo.full_name}' created successfully: {repo.html_url}")
        return repo.html_url
    except GithubException as e:
        if e.status == 422 and "name already exists" in e.data.get('message', ''):
            print(f"ℹ️ GitHub repository '{repo_name}' already exists. Skipping creation.")
            repo = _get_repo_object(client, repo_name) # Usar la nueva auxiliar para obtener el repo existente
            if repo: return repo.html_url
            else: return None
        print(f"❌ Error creating GitHub repository '{repo_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error creating GitHub repository '{repo_name}': {type(e).__name__} - {e}")
        return None


def create_github_branch(repo_name: str, branch_name: str, base_branch: str) -> bool:
    """Creates a new branch in a GitHub repository from a base branch."""
    client = _get_github_client()
    if not client: return False

    repo = _get_repo_object(client, repo_name) # Usar la nueva auxiliar
    if not repo: return False

    try:
        base_branch_ref = repo.get_git_ref(f"heads/{base_branch}")
        base_commit_sha = base_branch_ref.object.sha

        print(f"ℹ️ Attempting to create branch '{branch_name}' from '{base_branch}' (SHA: {base_commit_sha}) in repo '{repo_name}'...")
        repo.create_git_ref(f"refs/heads/{branch_name}", base_commit_sha)
        print(f"✅ GitHub branch '{branch_name}' created successfully in '{repo_name}'.")
        return True
    except UnknownObjectException:
        print(f"❌ Base branch '{base_branch}' not found in repository '{repo_name}'. Cannot create new branch '{branch_name}'.")
        return False
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in e.data.get('message', ''):
            print(f"ℹ️ GitHub branch '{branch_name}' already exists in '{repo_name}'. Skipping creation.")
            return True
        print(f"❌ Error creating GitHub branch '{branch_name}' in '{repo_name}': {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating GitHub branch '{branch_name}' in '{repo_name}': {type(e).__name__} - {e}")
        return False


# --- Funciones adicionales para el futuro (PUSH de scripts y PRs) ---
# Estas funciones se usarán para el comando PROMOTE, pero se pueden añadir después de lo básico.

def get_file_content_from_github(repo_name: str, branch_name: str, file_path: str) -> str | None:
    client = _get_github_client()
    if not client: return None

    repo = _get_repo_object(client, repo_name) # Usar la nueva auxiliar
    if not repo: return None

    try:
        contents = repo.get_contents(file_path, ref=branch_name)
        if isinstance(contents, list):
            print(f"❌ '{file_path}' is a directory, not a file, in branch '{branch_name}' of '{repo_name}'.")
            return None
        return base64.b64decode(contents.content).decode('utf-8')
    except UnknownObjectException:
        print(f"ℹ️ File '{file_path}' not found in branch '{branch_name}' of '{repo_name}'.")
        return None
    except GithubException as e:
        print(f"❌ GitHub API error getting file '{file_path}' from '{repo_name}/{branch_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error getting file content from GitHub: {type(e).__name__} - {e}")
        return None

def create_or_update_github_file(repo_name: str, branch_name: str, file_path: str, commit_message: str, content: str) -> bool:
    """Creates or updates a file in a specific branch in a GitHub repository."""
    client = _get_github_client()
    if not client: return False

    repo = _get_repo_object(client, repo_name)
    if not repo: return False

    try:
        file_obj = None # Inicializar file_obj a None
        
        try:
            # Intenta obtener el contenido del archivo.
            file_obj = repo.get_contents(file_path, ref=branch_name)
        except UnknownObjectException:
            # El archivo no existe. Esto es el path esperado para crear un nuevo archivo.
            # file_obj permanece None, lo que nos llevará al bloque 'else' para crear.
            pass
        except GithubException as e:
            # Manejar el caso específico de un repositorio completamente vacío.
            if e.status == 404 and "This repository is empty." in e.data.get('message', ''):
                print(f"ℹ️ Repository '{repo_name}' is empty. Proceeding to create the first file '{file_path}'.")
                # file_obj permanece None, lo que nos llevará al bloque 'else' para crear.
            else:
                # Si es otra GithubException 404 (o cualquier otra), re-lanzarla
                # para que sea capturada por el bloque externo y reportada como un error.
                raise e

        if file_obj:
            # Si file_obj no es None, significa que el archivo existe, procedemos a actualizarlo.
            # Asegúrate de que no sea una lista (caso de directorio)
            if isinstance(file_obj, list):
                 print(f"❌ Cannot update: '{file_path}' is a directory, not a file, in branch '{branch_name}' of '{repo_name}'.")
                 return False

            existing_content = base64.b64decode(file_obj.content).decode('utf-8')
            if existing_content == content:
                print(f"ℹ️ File '{file_path}' in branch '{branch_name}' is already identical. Skipping update.")
                return True
            
            repo.update_file(file_path, commit_message, content, file_obj.sha, branch=branch_name)
            print(f"✅ File '{file_path}' updated successfully in branch '{branch_name}' of '{repo_name}'.")
        else:
            # Si file_obj es None, significa que el archivo no existe (o el repo está vacío), lo creamos.
            repo.create_file(file_path, commit_message, content, branch=branch_name)
            print(f"✅ File '{file_path}' created successfully in branch '{branch_name}' of '{repo_name}'.")
        
        return True
    except GithubException as e:
        print(f"❌ GitHub API error creating/updating file '{file_path}' in '{repo_name}/{branch_name}': {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating/updating GitHub file: {type(e).__name__} - {e}")
        return False


def create_or_update_github_file(repo_name: str, branch_name: str, file_path: str, commit_message: str, content: str) -> bool:
    """
    Creates or updates a file in a specific branch in a GitHub repository.
    This version prioritizes creation for initial pushes to empty repos.
    """
    client = _get_github_client()
    if not client: return False

    repo = _get_repo_object(client, repo_name)
    if not repo: return False

    try:
        # PRIMER INTENTO: Crear el archivo. Esto es lo que debe suceder si el repo está vacío
        # o si el archivo no existe.
        print(f"ℹ️ Attempting to create file '{file_path}' in branch '{branch_name}' of '{repo_name}'...")
        repo.create_file(file_path, commit_message, content, branch=branch_name)
        print(f"✅ File '{file_path}' created successfully in branch '{branch_name}' of '{repo_name}'.")
        return True
    except GithubException as e:
        # Si la creación falla, puede ser por varias razones.
        # El caso más común para un fallo de 'create_file' después de un intento inicial
        # es que el archivo ya existe (e.g., status 422 - Unprocessable Entity).
        # También puede haber otros errores.
        if e.status == 422: # Típicamente indica que el recurso ya existe o hay un problema de validación
            # Intentamos obtener el archivo. Si lo obtenemos, significa que ya existe y debemos actualizarlo.
            print(f"ℹ️ Creation failed (status 422). Assuming file '{file_path}' already exists in branch '{branch_name}'. Attempting to update...")
            
            try:
                file_obj = repo.get_contents(file_path, ref=branch_name)
                # Asegúrate de que no sea una lista (caso de directorio)
                if isinstance(file_obj, list):
                     print(f"❌ Cannot update: '{file_path}' is a directory, not a file, in branch '{branch_name}' of '{repo_name}'.")
                     return False

                existing_content = base64.b64decode(file_obj.content).decode('utf-8')
                if existing_content == content:
                    print(f"ℹ️ File '{file_path}' in branch '{branch_name}' is already identical. Skipping update.")
                    return True
                
                repo.update_file(file_path, commit_message, content, file_obj.sha, branch=branch_name)
                print(f"✅ File '{file_path}' updated successfully in branch '{branch_name}' of '{repo_name}'.")
                return True
            except UnknownObjectException:
                # Esto no debería pasar si el 422 indicó que el archivo ya existía,
                # pero si ocurriera, significa que el archivo realmente no está allí
                # o no es accesible por alguna razón.
                print(f"❌ Error: File '{file_path}' was reported as existing but could not be retrieved for update (UnknownObjectException).")
                return False
            except GithubException as update_e:
                print(f"❌ GitHub API error updating file '{file_path}' in '{repo_name}/{branch_name}': {update_e}")
                return False
        else:
            # Otro tipo de GithubException que no es 422 (conflicto/existencia),
            # es un error real en la operación de creación.
            print(f"❌ GitHub API error creating/updating file '{file_path}' in '{repo_name}/{branch_name}': {e}")
            return False
    except Exception as e:
        # Captura cualquier otra excepción inesperada
        print(f"❌ Unexpected error creating/updating GitHub file: {type(e).__name__} - {e}")
        return False

def create_github_pull_request(repo_name: str, title: str, head_branch: str, base_branch: str, body: str = "") -> str | None:
    client = _get_github_client()
    if not client: return None

    repo = _get_repo_object(client, repo_name) # Usar la nueva auxiliar
    if not repo: return None

    try:
        print(f"ℹ️ Attempting to create Pull Request from '{head_branch}' to '{base_branch}' in '{repo_name}'...")
        pr = repo.create_pull(title=title, body=body, head=head_branch, base=base_branch)
        print(f"✅ Pull Request created successfully: {pr.html_url}")
        return pr.html_url
    except GithubException as e:
        print(f"❌ GitHub API error creating Pull Request from '{head_branch}' to '{base_branch}' in '{repo_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error creating GitHub Pull Request: {type(e).__name__} - {e}")
        return None