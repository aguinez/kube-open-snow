# kubeSol/projects/cli_handlers.py
"""
Handlers for KubeSol project and environment CLI commands.
These functions bridge the parsed command from the CLI/parser
to the core logic in manager.py and update the shell's context.
"""
from tabulate import tabulate
from kubeSol.projects import manager
from kubeSol.projects.context import KubeSolContext
from kubeSol.constants import DEFAULT_NAMESPACE, DEFAULT_PROJECT_ENVIRONMENT
# We should try to avoid direct k8s_api calls from handlers; manager should mediate.
# from kubeSol.engine import k8s_api

# Note: The 'context' object (instance of KubeSolContext) will be managed by the shell
# and passed to these handler functions.

def handle_create_project(parsed_args: dict, context: KubeSolContext):
    """Handles the CREATE PROJECT <project_name> command."""
    # --- BEGIN DEBUG PRINTS for "Project name is required" issue ---
    print(f"DEBUG_HANDLER: Inside handle_create_project.")
    print(f"DEBUG_HANDLER: Type of parsed_args received: {type(parsed_args)}")
    print(f"DEBUG_HANDLER: Content of parsed_args received: {parsed_args!r}")
    
    key_to_check = "user_project_name" # Key from transformer for create_project_cmd
    print(f"DEBUG_HANDLER: Attempting to get key: '{key_to_check}'")
    
    project_name_to_create = parsed_args.get(key_to_check)
    
    print(f"DEBUG_HANDLER: Value of project_name_to_create: {project_name_to_create!r}")
    print(f"DEBUG_HANDLER: Type of project_name_to_create: {type(project_name_to_create)}")
    print(f"DEBUG_HANDLER: Boolean evaluation of (not project_name_to_create): {not project_name_to_create}")
    # --- END DEBUG PRINTS ---

    if not project_name_to_create: 
        print("❌ Error: Project name must be provided for CREATE PROJECT. (Value was falsy)")
        return
    
    # Call the manager function to perform the action
    proj_id, def_env, def_ns, user_proj_name = manager.create_new_project(user_project_name=project_name_to_create)
    
    if proj_id and def_ns and def_env and user_proj_name: # If project and default env creation was successful
        # If no specific project context was active before, or if it's a different project,
        # offer to switch to the new one.
        if not context.is_project_context_active() or context.project_id != proj_id:
            confirm_use = input(f"Project '{user_proj_name}' created. Switch to its default environment '{def_env}' (namespace '{def_ns}')? (y/n): ").strip().lower()
            if confirm_use == 'y':
                context.set_project_env_context(user_proj_name, proj_id, def_env, def_ns)

def handle_create_environment(parsed_args: dict, context: KubeSolContext):
    """Handles CREATE ENV <env_name> [FOR PROJECT <project_name> | FOR THIS PROJECT] [DEPENDING FROM ENV <parent_env_name>]"""
    env_name_to_create = parsed_args.get("env_name")
    project_specifier = parsed_args.get("project_name_specifier")
    parent_env_name = parsed_args.get("parent_env_name") # <--- Capturar el nombre del entorno padre

    if not env_name_to_create:
        print("❌ Error: Environment name must be provided for CREATE ENV.")
        return

    target_project_id = None
    target_user_project_name = None

    if project_specifier:
        if project_specifier.upper() == "THIS_PROJECT_CONTEXT":
            if not context.is_project_context_active():
                print("❌ 'FOR THIS PROJECT' specified, but no KubeSol project context is currently set.")
                print("   Use 'USE PROJECT <name> ENV <name>' first, or specify 'FOR PROJECT <name>'.")
                return
            target_project_id = context.project_id
            target_user_project_name = context.user_project_name
        else:
            target_user_project_name = project_specifier
            target_project_id = manager._resolve_project_id_from_display_name(target_user_project_name)
            if not target_project_id:
                return
    else:
        if not context.is_project_context_active():
            print("❌ Project not specified for CREATE ENV and no active KubeSol project context.")
            print("   Use 'FOR PROJECT <name>' or set a context with 'USE PROJECT ... ENV ...' first.")
            return
        print(f"ℹ️ No project specified for CREATE ENV, using current project context: '{context.user_project_name}'.")
        target_project_id = context.project_id
        target_user_project_name = context.user_project_name

    if not target_project_id or not target_user_project_name:
        print("❌ Internal Error: Could not determine target project ID or display name for creating environment.")
        return

    # Llamar a la función del manager con el nuevo parámetro parent_env_name
    manager.add_environment_to_project(
        project_id=target_project_id,
        user_project_name=target_user_project_name,
        new_env_name=env_name_to_create,
        parent_env_name=parent_env_name # <--- Pasar el entorno padre
    )

def handle_list_projects(parsed_args: dict, context: KubeSolContext):
    projects_data = manager.get_all_project_details() 
    if not projects_data:
        print("ℹ️ No KubeSol projects found.")
        return
    
    # Nuevos headers y datos para la tabla
    headers = ["Project Display Name", "Project ID", "Environments"] 
    table_data = []
    for p_info in projects_data:
        # Unir los nombres de entorno en un string separado por comas
        # environment_names es una lista de strings (ya en minúsculas desde el manager)
        environments_str = ", ".join(p_info.get("environment_names", []))
        if not environments_str: environments_str = "-" # Si no hay entornos

        table_data.append([
            p_info.get("project_display_name", "N/A"), 
            p_info.get("project_id", "N/A"),
            environments_str # Mostrar la lista de entornos
        ])
    
    print("\n KubeSol Projects:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def handle_get_project(parsed_args: dict, context: KubeSolContext):
    """Handles GET PROJECT <name> or GET THIS PROJECT."""
    project_specifier = parsed_args.get("project_name_specifier")
    target_user_project_name_to_query = None

    if project_specifier == "THIS_PROJECT_CONTEXT":
        if not context.is_project_context_active() or not context.user_project_name:
            print("❌ 'GET THIS PROJECT' used, but no project context is currently active.")
            print("   Use 'USE PROJECT <name> ENV <name>' to set a context.")
            return
        target_user_project_name_to_query = context.user_project_name
        print(f"ℹ️ 'GET THIS PROJECT' resolved to current project: '{target_user_project_name_to_query}'")
    elif project_specifier: 
        target_user_project_name_to_query = project_specifier
    else: 
        if not context.is_project_context_active() or not context.user_project_name:
            print("❌ Project name not specified and no project context is active for GET PROJECT.")
            return
        print(f"ℹ️ No project name specified for GET PROJECT, using current project context: '{context.user_project_name}'.")
        target_user_project_name_to_query = context.user_project_name
    
    environments_data = manager.get_environments_for_project(user_project_name=target_user_project_name_to_query)
    
    if environments_data:
        # Determine display name and ID from the first environment, assuming consistency for the queried project
        proj_id_display = environments_data[0].get('project_id', 'N/A')
        # Use the display name that was actually queried or from context if it was "THIS_PROJECT_CONTEXT"
        # The labels might have a slightly different casing if manually changed, so manager might return the actual label value.
        actual_display_name_from_results = environments_data[0].get('project_display_name', target_user_project_name_to_query)

        print(f"\nEnvironments for Project: '{actual_display_name_from_results}' (ID: {proj_id_display})")
        headers = ["Environment", "Namespace Name", "Status", "Created At"]
        table_data = []
        for e_info in environments_data:
            table_data.append([
                e_info.get("environment", "N/A"), 
                e_info.get("namespace", "N/A"), 
                e_info.get("status", "N/A"), 
                e_info.get("created", "N/A")
            ])
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    # else: manager.get_environments_for_project already prints "not found" or "no environments"

def handle_update_project(parsed_args: dict, context: KubeSolContext):
    """Handles UPDATE PROJECT <old_name> TO <new_name>."""
    old_display_name = parsed_args.get("old_project_name")
    new_display_name = parsed_args.get("new_project_name")

    if not old_display_name or not new_display_name:
        print("❌ Both old and new project display names must be provided for UPDATE PROJECT.")
        return
    if old_display_name == new_display_name:
        print(f"ℹ️ Project display name is already '{new_display_name}'. No update performed.")
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
            # set_project_env_context already prints "Context set to..."
        else:
             print(f"ℹ️ Project display name updated. Current shell context was for '{old_display_name}', but full context details (ID/env) were unclear. Please use 'USE PROJECT' to refresh if needed.")


def handle_drop_project(parsed_args: dict, context: KubeSolContext):
    """Handles DROP PROJECT <project_name>."""
    project_name_to_drop = parsed_args.get("user_project_name")
    if not project_name_to_drop:
        print("❌ Project name must be provided for DROP PROJECT.")
        return
    
    was_current_project = (context.is_project_context_active() and context.user_project_name == project_name_to_drop)
    
    # Confirmation is handled inside manager.delete_whole_project
    success = manager.delete_whole_project(user_project_name=project_name_to_drop)
    
    if success and was_current_project:
        print(f"ℹ️ Project '{project_name_to_drop}' was the active project. Context has been cleared to default.")
        context.clear_project_context()


def handle_drop_environment(parsed_args: dict, context: KubeSolContext):
    """Handles DROP ENVIRONMENT <env_name> [FROM PROJECT <name> | FROM THIS PROJECT]."""
    env_name_to_drop = parsed_args.get("env_name")
    project_specifier = parsed_args.get("project_name_specifier")

    if not env_name_to_drop:
        print("❌ Environment name must be provided for DROP ENVIRONMENT.")
        return

    target_project_id = None
    target_user_project_name = None

    if project_specifier and project_specifier.upper() == "THIS_PROJECT_CONTEXT":
        if not context.is_project_context_active():
            print("❌ 'FROM THIS PROJECT' specified, but no project context is set.")
            return
        target_project_id = context.project_id
        target_user_project_name = context.user_project_name
    elif project_specifier:
        target_user_project_name = project_specifier
        target_project_id = manager._resolve_project_id_from_display_name(target_user_project_name)
        if not target_project_id: # Manager function already printed message
            return 
    else: # Implicit THIS PROJECT if context is set
        if not context.is_project_context_active():
            print("❌ Project not specified for DROP ENVIRONMENT and no active context. Use 'FROM PROJECT <name>' or 'USE PROJECT ...' first.")
            return
        print(f"ℹ️ No project specified for DROP ENV, using current project context: '{context.user_project_name}'.")
        target_project_id = context.project_id
        target_user_project_name = context.user_project_name

    if not target_project_id or not target_user_project_name: # Should be caught by above logic
        print("❌ Could not determine target project for dropping environment.")
        return

    # Confirmation is handled inside manager.delete_project_environment
    success = manager.delete_project_environment(
        project_id=target_project_id, 
        user_project_name_for_msg=target_user_project_name, 
        env_name=env_name_to_drop
    )
    
    if success and context.project_id == target_project_id and context.environment_name == env_name_to_drop:
        print(f"ℹ️ Environment '{env_name_to_drop}' of project '{target_user_project_name}' was the current active environment.")
        # Reset environment part of the context, keep project if possible
        context.environment_name = None 
        context.current_namespace = DEFAULT_NAMESPACE # Default, or try to find another env for this project
        
        # Try to set context to project's default environment if it exists
        if context.project_id and context.user_project_name:
            default_env_physical_ns_name = manager._get_physical_namespace_name(context.project_id, DEFAULT_PROJECT_ENVIRONMENT)
            # We need to check if this namespace actually exists. This check should ideally be in manager or context.
            # For now, we'll assume manager.resolve_project_and_environment_namespaces can verify.
            # A simpler approach: set namespace to something generic or prompt user.
            # Let's just update the prompt based on the cleared environment.
            context.set_namespace_context(context.current_namespace) # This will clear project/env name if ns is default
                                                                    # or just set namespace and clear env name.
            print(f"   Current environment context cleared. Namespace set to '{context.current_namespace}'.")
            print(f"   You may want to 'USE PROJECT {context.user_project_name} ENV <another_env>' or 'USE PROJECT ... ENV dev'.")
        else: # Should not happen if context.project_id was valid
            context.clear_project_context()


def handle_use_project_environment(parsed_args: dict, context: KubeSolContext):
    """Handles USE PROJECT <project_name> ENV <env_name>."""
    project_name_to_use = parsed_args.get("user_project_name")
    env_name_to_use = parsed_args.get("env_name")

    if not project_name_to_use or not env_name_to_use:
        print("❌ Both project display name and environment name are required for USE command.")
        return
    
    # manager.resolve_project_and_environment_namespaces returns (proj_id, user_proj_name, physical_ns, error_msg)
    proj_id, resolved_user_proj_name, physical_ns, error_msg = manager.resolve_project_and_environment_namespaces(
        user_project_name=project_name_to_use,
        environment_name=env_name_to_use
    )
    
    if error_msg:
        print(f"❌ {error_msg}")
        return
    
    if proj_id and physical_ns and resolved_user_proj_name: # Success from manager
        context.set_project_env_context(resolved_user_proj_name, proj_id, env_name_to_use, physical_ns)
    # else: manager.resolve_project_and_environment_namespaces would have returned an error_msg