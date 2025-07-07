# kubesol/modules/projects/handlers.py
"""
Handlers for KubeSol project and environment CLI commands.
These functions bridge the parsed command from the commands.py module
to the core logic in manager.py and update the shell's context.
"""
from tabulate import tabulate

# Actualizado: Importaciones para el manager y el contexto
from kubesol.modules.projects import manager
from kubesol.core.context import KubeSolContext
from kubesol.constants import DEFAULT_NAMESPACE, DEFAULT_PROJECT_ENVIRONMENT

# Nota: El objeto 'context' (instancia de KubeSolContext) será gestionado por el shell
# y pasado a estas funciones manejadoras.

def handle_create_project(parsed_args: dict, context: KubeSolContext):
    """
    Handles the CREATE PROJECT <project_name> command.
    Assumes parsed_args already has 'project_name' validado.
    """
    project_name_to_create = parsed_args.get("project_name")
    
    # Llama a la función del manager para realizar la acción
    proj_id, def_env, def_ns, user_proj_name = manager.create_new_project(user_project_name=project_name_to_create)
    
    if proj_id and def_ns and def_env and user_proj_name: # Si la creación del proyecto y el entorno por defecto fue exitosa
        # Si no había un contexto de proyecto activo, o si es un proyecto diferente,
        # ofrece cambiar al nuevo.
        if not context.is_project_context_active() or context.project_id != proj_id:
            confirm_use = input(f"Project '{user_proj_name}' created. Switch to its default environment '{def_env}' (namespace '{def_ns}')? (y/n): ").strip().lower()
            if confirm_use == 'y':
                context.set_project_env_context(user_proj_name, proj_id, def_env, def_ns)

def handle_create_environment(parsed_args: dict, context: KubeSolContext):
    """
    Handles CREATE ENV <env_name> [FOR PROJECT <project_name> | FOR THIS PROJECT] [DEPENDS ON <parent_env_name>]
    Assumes parsed_args has 'env_name' y project_specifier resuelto.
    """
    env_name_to_create = parsed_args.get("env_name")
    project_specifier = parsed_args.get("project_name_specifier")
    depends_on_env_name = parsed_args.get("depends_on_env")

    target_project_id = None
    target_user_project_name = None

    if project_specifier == "THIS_PROJECT_CONTEXT":
        if not context.is_project_context_active():
            print("❌ 'FOR THIS PROJECT' especificado, pero no hay un contexto de proyecto KubeSol actualmente establecido.")
            print("   Usa 'USE PROJECT <nombre> ENV <nombre>' primero, o especifica 'FOR PROJECT <nombre>'.")
            return
        target_project_id = context.project_id
        target_user_project_name = context.user_project_name
    elif project_specifier: # Es un nombre de proyecto específico
        target_user_project_name = project_specifier
        target_project_id = manager._resolve_project_id_from_display_name(target_user_project_name)
        if not target_project_id:
            return
    else: # Implícitamente 'FOR THIS PROJECT' si no hay especificador y el contexto está establecido
        if not context.is_project_context_active():
            print("❌ Proyecto no especificado para CREATE ENV y no hay un contexto de proyecto KubeSol activo.")
            print("   Usa 'FOR PROJECT <nombre>' o establece un contexto con 'USE PROJECT ... ENV ...' primero.")
            return
        print(f"ℹ️ Proyecto no especificado para CREATE ENV, usando el contexto de proyecto actual: '{context.user_project_name}'.")
        target_project_id = context.project_id
        target_user_project_name = context.user_project_name

    if not target_project_id or not target_user_project_name:
        print("❌ Error Interno: No se pudo determinar el ID del proyecto o el nombre a mostrar para crear el entorno.")
        return

    # Llama a la función del manager con todos los parámetros determinados
    manager.add_environment_to_project(
        project_id=target_project_id,
        user_project_name=target_user_project_name,
        new_env_name=env_name_to_create,
        depends_on_env_name=depends_on_env_name
    )

def handle_list_projects(parsed_args: dict, context: KubeSolContext):
    """Handles the LIST PROJECTS command."""
    projects_data = manager.get_all_project_details()
    if not projects_data:
        print("ℹ️ No se encontraron proyectos KubeSol.")
        return
    
    headers = ["Nombre del Proyecto", "ID del Proyecto", "Entornos"]
    table_data = []
    for p_info in projects_data:
        environments_str = ", ".join(p_info.get("environment_names", []))
        if not environments_str: environments_str = "-"

        table_data.append([
            p_info.get("project_display_name", "N/A"),
            p_info.get("project_id", "N/A"),
            environments_str
        ])
    
    print("\n Proyectos KubeSol:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def handle_get_project(parsed_args: dict, context: KubeSolContext):
    """Handles GET PROJECT <name> or GET THIS PROJECT."""
    project_specifier = parsed_args.get("project_name_specifier")
    target_user_project_name_to_query = None

    if project_specifier == "THIS_PROJECT_CONTEXT":
        if not context.is_project_context_active() or not context.user_project_name:
            print("❌ 'GET THIS PROJECT' usado, pero no hay un contexto de proyecto activo actualmente.")
            print("   Usa 'USE PROJECT <nombre> ENV <nombre>' para establecer un contexto.")
            return
        target_user_project_name_to_query = context.user_project_name
        print(f"ℹ️ 'GET THIS PROJECT' resuelto al proyecto actual: '{target_user_project_name_to_query}'")
    elif project_specifier:
        target_user_project_name_to_query = project_specifier
    else: # Recurso al contexto activo si no se especifica
        if not context.is_project_context_active() or not context.user_project_name:
            print("❌ Nombre de proyecto no especificado y no hay un contexto de proyecto activo para GET PROJECT.")
            return
        print(f"ℹ️ Nombre de proyecto no especificado para GET PROJECT, usando el contexto de proyecto actual: '{context.user_project_name}'.")
        target_user_project_name_to_query = context.user_project_name
    
    environments_data = manager.get_environments_for_project(user_project_name=target_user_project_name_to_query)
    
    if environments_data:
        proj_id_display = environments_data[0].get('project_id', 'N/A')
        actual_display_name_from_results = environments_data[0].get('project_display_name', target_user_project_name_to_query)

        print(f"\nEntornos para el Proyecto: '{actual_display_name_from_results}' (ID: {proj_id_display})")
        headers = ["Entorno", "Nombre del Namespace", "Estado", "Creado En"]
        table_data = []
        for e_info in environments_data:
            table_data.append([
                e_info.get("environment", "N/A"), 
                e_info.get("namespace", "N/A"), 
                e_info.get("status", "N/A"), 
                e_info.get("created", "N/A")
            ])
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    # else: manager.get_environments_for_project ya imprime "no encontrado" o "sin entornos"

def handle_update_project(parsed_args: dict, context: KubeSolContext):
    """
    Handles UPDATE PROJECT <old_name> TO <new_name>.
    Assumes parsed_args already has 'old_project_name' y 'new_project_name'.
    """
    old_display_name = parsed_args.get("old_project_name")
    new_display_name = parsed_args.get("new_project_name")

    if old_display_name == new_display_name:
        print(f"ℹ️ El nombre a mostrar del proyecto ya es '{new_display_name}'. No se realizó ninguna actualización.")
        return
        
    success = manager.update_project_display_name_label(
        old_display_name=old_display_name, 
        new_display_name=new_display_name
    )
    
    if success and context.is_project_context_active() and context.user_project_name == old_display_name:
        if context.project_id and context.environment_name and context.current_namespace:
            context.set_project_env_context(
                user_project_name=new_display_name, 
                project_id=context.project_id, 
                environment_name=context.environment_name, 
                namespace=context.current_namespace 
            )
        else:
             print(f"ℹ️ Nombre a mostrar del proyecto actualizado. El contexto actual de la shell era para '{old_display_name}', pero los detalles completos del contexto (ID/entorno) no estaban claros. Por favor, usa 'USE PROJECT' para actualizar si es necesario.")


def handle_drop_project(parsed_args: dict, context: KubeSolContext):
    """
    Handles DROP PROJECT <project_name>.
    Assumes parsed_args already has 'project_name'.
    """
    project_name_to_drop = parsed_args.get("project_name")
    
    was_current_project = (context.is_project_context_active() and context.user_project_name == project_name_to_drop)
    
    # La confirmación se maneja dentro de manager.delete_whole_project
    success = manager.delete_whole_project(user_project_name=project_name_to_drop)
    
    if success and was_current_project:
        print(f"ℹ️ El proyecto '{project_name_to_drop}' era el proyecto activo. El contexto ha sido limpiado a los valores por defecto.")
        context.clear_project_context()


def handle_drop_environment(parsed_args: dict, context: KubeSolContext):
    """
    Handles DROP ENVIRONMENT <env_name> [FROM PROJECT <name> | FROM THIS PROJECT].
    Assumes parsed_args has 'env_name' y project_specifier resuelto.
    """
    env_name_to_drop = parsed_args.get("env_name")
    project_specifier = parsed_args.get("project_name_specifier")

    target_project_id = None
    target_user_project_name = None

    if project_specifier == "THIS_PROJECT_CONTEXT":
        if not context.is_project_context_active():
            print("❌ 'FROM THIS PROJECT' especificado, pero no hay un contexto de proyecto establecido.")
            return
        target_project_id = context.project_id
        target_user_project_name = context.user_project_name
    elif project_specifier:
        target_user_project_name = project_specifier
        target_project_id = manager._resolve_project_id_from_display_name(target_user_project_name)
        if not target_project_id:
            return
    else: # Implícito THIS PROJECT si el contexto está establecido
        if not context.is_project_context_active():
            print("❌ Proyecto no especificado para DROP ENVIRONMENT y no hay un contexto activo. Usa 'FROM PROJECT <nombre>' o 'USE PROJECT ...' primero.")
            return
        print(f"ℹ️ Proyecto no especificado para DROP ENV, usando el contexto de proyecto actual: '{context.user_project_name}'.")
        target_project_id = context.project_id
        target_user_project_name = context.user_project_name

    if not target_project_id or not target_user_project_name:
        print("❌ No se pudo determinar el proyecto objetivo para eliminar el entorno.")
        return

    # La confirmación se maneja dentro de manager.delete_project_environment
    success = manager.delete_project_environment(
        project_id=target_project_id,
        user_project_name_for_msg=target_user_project_name,
        env_name=env_name_to_drop
    )
    
    if success and context.project_id == target_project_id and context.environment_name == env_name_to_drop:
        print(f"ℹ️ El entorno '{env_name_to_drop}' del proyecto '{target_user_project_name}' era el entorno activo actual.")
        context.environment_name = None
        context.current_namespace = DEFAULT_NAMESPACE
        
        if context.project_id and context.user_project_name:
            context.set_namespace_context(context.current_namespace)
            print(f"   Contexto de entorno actual limpiado. Namespace establecido a '{context.current_namespace}'.")
            print(f"   Quizás quieras 'USE PROJECT {context.user_project_name} ENV <otro_entorno>' o 'USE PROJECT ... ENV dev'.")
        else:
            context.clear_project_context()


def handle_use_project_environment(parsed_args: dict, context: KubeSolContext):
    """
    Handles USE PROJECT <project_name> ENV <env_name>.
    Assumes parsed_args has 'project_name' y 'env_name'.
    """
    project_name_to_use = parsed_args.get("project_name")
    env_name_to_use = parsed_args.get("env_name")

    proj_id, resolved_user_proj_name, physical_ns, error_msg = manager.resolve_project_and_environment_namespaces(
        user_project_name=project_name_to_use,
        environment_name=env_name_to_use
    )
    
    if error_msg:
        print(f"❌ {error_msg}")
        return
    
    if proj_id and physical_ns and resolved_user_proj_name: # Éxito desde el manager
        context.set_project_env_context(resolved_user_proj_name, proj_id, env_name_to_use, physical_ns)