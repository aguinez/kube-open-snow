# kubeSol/plugins/core/project_plugin.py
"""
Project Plugin for KubeSol

Handles project and environment management operations including CREATE PROJECT, 
CREATE ENV, LIST PROJECTS, GET PROJECT, UPDATE PROJECT, DROP PROJECT, DROP ENV,
and USE PROJECT ENV commands.
This plugin extracts the project-related functionality from the monolithic codebase.
"""

from typing import Dict, List, Any, Callable, Tuple
import logging
import re

from kubeSol.core.plugin_system.plugin_interface import ProjectPlugin as BaseProjectPlugin, PluginMetadata
from kubeSol.core.context import KubeSolContext

logger = logging.getLogger(__name__)

class ProjectPlugin(BaseProjectPlugin):
    """
    Plugin for managing projects and environments.
    
    This plugin provides the grammar rules, command handlers, and validation
    for project and environment operations.
    """
    
    def __init__(self):
        super().__init__()
        self._supported_operations = [
            "CREATE_PROJECT", "CREATE_ENV", "LIST_PROJECTS", "GET_PROJECT", 
            "UPDATE_PROJECT", "DROP_PROJECT", "DROP_ENV", "USE_PROJECT_ENV"
        ]
    
    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata"""
        return PluginMetadata(
            name="ProjectPlugin",
            version="1.0.0",
            description="Core project and environment management plugin",
            author="KubeSol Team",
            dependencies=[]
        )
    
    def get_grammar_rules(self) -> Dict[str, str]:
        """Return grammar rules for project operations"""
        return {
            # Project and environment commands
            "create_project_command": "CREATE_KW PROJECT_KW NAME",
            "create_env_command": "CREATE_KW ENV_KW NAME [project_target_clause] [depends_on_clause]",
            "list_projects_command": "LIST_KW PROJECT_KW \"S\"?",
            "get_project_command": "GET_KW get_target_choice",
            "update_project_command": "UPDATE_KW PROJECT_KW NAME TO_KW NAME",
            "drop_project_command": "DROP_KW PROJECT_KW NAME",
            "drop_env_command": "DROP_KW ENV_KW NAME [project_target_clause]",
            "use_project_env_command": "USE_KW PROJECT_KW NAME ENV_KW NAME",
            
            # Target and dependency clauses
            "project_target_clause": "(FOR_KW | FROM_KW) (project_target_clause_project_name_ref | project_target_clause_this_project_ref)",
            "project_target_clause_project_name_ref": "PROJECT_KW NAME",
            "project_target_clause_this_project_ref": "THIS_KW PROJECT_KW",
            "depends_on_clause": "\"DEPENDS\"i \"ON\"i NAME",
            
            # GET command target choices
            "get_target_choice": "get_project_by_name_payload | get_this_project_payload",
            "get_project_by_name_payload": "PROJECT_KW NAME",
            "get_this_project_payload": "THIS_KW PROJECT_KW",
            
            # Keywords
            "PROJECT_KW": "\"PROJECT\"i",
            "ENV_KW": "\"ENV\"i | \"ENVIRONMENT\"i",
            "USE_KW": "\"USE\"i",
            "DROP_KW": "\"DROP\"i",
            "FOR_KW": "\"FOR\"i",
            "FROM_KW": "\"FROM\"i",
            "THIS_KW": "\"THIS\"i",
            "TO_KW": "\"TO\"i"
        }
    
    def get_command_handlers(self) -> Dict[Tuple[str, str], Callable]:
        """Return command handlers for project operations"""
        return {
            ("CREATE_PROJECT", "PROJECT_LOGICAL"): self._handle_create_project,
            ("CREATE_ENV", "ENVIRONMENT_LOGICAL"): self._handle_create_environment,
            ("LIST_PROJECTS", "PROJECT_LOGICAL"): self._handle_list_projects,
            ("GET_PROJECT", "PROJECT_LOGICAL"): self._handle_get_project,
            ("UPDATE_PROJECT", "PROJECT_LOGICAL"): self._handle_update_project,
            ("DROP_PROJECT", "PROJECT_LOGICAL"): self._handle_drop_project,
            ("DROP_ENV", "ENVIRONMENT_LOGICAL"): self._handle_drop_environment,
            ("USE_PROJECT_ENV", "PROJECT_LOGICAL"): self._handle_use_project_environment
        }
    
    def get_constants(self) -> Dict[str, Any]:
        """Return constants defined by this plugin"""
        return {
            # Actions
            "ACTION_CREATE_PROJECT": "CREATE_PROJECT",
            "ACTION_CREATE_ENV": "CREATE_ENV",
            "ACTION_LIST_PROJECTS": "LIST_PROJECTS",
            "ACTION_GET_PROJECT": "GET_PROJECT",
            "ACTION_UPDATE_PROJECT": "UPDATE_PROJECT",
            "ACTION_DROP_PROJECT": "DROP_PROJECT",
            "ACTION_DROP_ENV": "DROP_ENV",
            "ACTION_USE_PROJECT_ENV": "USE_PROJECT_ENV",
            
            # Logical Types
            "LOGICAL_TYPE_PROJECT": "PROJECT_LOGICAL",
            "LOGICAL_TYPE_ENVIRONMENT": "ENVIRONMENT_LOGICAL",
            
            # Project Management Constants
            "DEFAULT_PROJECT_ENVIRONMENT": "dev",
            
            # Labels and annotations
            "PROJECT_ID_LABEL_KEY": "kubesol.io/project-id",
            "PROJECT_NAME_LABEL_KEY": "kubesol.io/project-name",
            "ENVIRONMENT_LABEL_KEY": "kubesol.io/environment",
            "ENVIRONMENT_DEPENDS_ON_LABEL_KEY": "kubesol.io/depends-on",
            "PROJECT_REPO_NAME_LABEL_KEY": "kubesol.io/github-repo-name",
            "PROJECT_REPO_URL_ANNOTATION_KEY": "kubesol.io/github-repo-url",
            
            # GitHub constants
            "GITHUB_ORG_OR_USER": "aguinez",
            "GITHUB_TOKEN_SECRET_NAME": "kubesol-github-token",
            "GITHUB_REPO_PREFIX": "kubesol-project-",
            "GITHUB_DEFAULT_BRANCH_NAME": "main",
            "GITHUB_DEV_BRANCH_NAME": "develop",
            "GITHUB_SCRIPTS_FOLDER": "scripts"
        }
    
    def get_transformer_methods(self) -> Dict[str, Callable]:
        """Return transformer methods for grammar rules"""
        return {
            "create_project_command": self._transform_create_project,
            "create_env_command": self._transform_create_env,
            "list_projects_command": self._transform_list_projects,
            "get_project_command": self._transform_get_project,
            "update_project_command": self._transform_update_project,
            "drop_project_command": self._transform_drop_project,
            "drop_env_command": self._transform_drop_env,
            "use_project_env_command": self._transform_use_project_env,
            "project_target_clause": self._transform_project_target_clause,
            "project_target_clause_project_name_ref": self._transform_project_name_ref,
            "project_target_clause_this_project_ref": self._transform_this_project_ref,
            "depends_on_clause": self._transform_depends_on_clause,
            "get_target_choice": self._transform_get_target_choice,
            "get_project_by_name_payload": self._transform_get_project_by_name,
            "get_this_project_payload": self._transform_get_this_project,
            "PROJECT_KW": lambda token: token.value.upper(),
            "ENV_KW": lambda token: token.value.upper(),
            "USE_KW": lambda token: token.value.upper(),
            "DROP_KW": lambda token: token.value.upper(),
            "FOR_KW": lambda token: token.value.upper(),
            "FROM_KW": lambda token: token.value.upper(),
            "THIS_KW": lambda token: token.value.upper(),
            "TO_KW": lambda token: token.value.upper()
        }
    
    def get_supported_project_operations(self) -> List[str]:
        """Return list of supported project operations"""
        return self._supported_operations.copy()
    
    def validate_project_name(self, project_name: str) -> bool:
        """Validate a project name according to plugin rules"""
        if not project_name or not project_name.strip():
            logger.error("Project name cannot be empty")
            return False
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$', project_name):
            logger.error(f"Project name '{project_name}' contains invalid characters")
            return False
        
        # Check length constraints
        if len(project_name) > 50:
            logger.error(f"Project name '{project_name}' is too long (max 50 characters)")
            return False
        
        return True
    
    def validate_environment_name(self, env_name: str) -> bool:
        """Validate an environment name according to plugin rules"""
        if not env_name or not env_name.strip():
            logger.error("Environment name cannot be empty")
            return False
        
        # Check for valid characters (alphanumeric, hyphens)
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$', env_name):
            logger.error(f"Environment name '{env_name}' contains invalid characters")
            return False
        
        # Check length constraints
        if len(env_name) > 20:
            logger.error(f"Environment name '{env_name}' is too long (max 20 characters)")
            return False
        
        return True
    
    # Transformer methods
    def _transform_create_project(self, transformer_self, children):
        """Transform CREATE PROJECT commands"""
        # children is a list: ['CREATE', 'PROJECT', 'myproject']
        # Extract the project name (last element)
        project_name = children[-1]
        return {
            "action": "CREATE_PROJECT",
            "type": "PROJECT_LOGICAL",
            "user_project_name": str(project_name).lower()
        }
    
    def _transform_create_env(self, create_kw, env_kw, env_name, project_specifier=None, depends_on_env=None):
        """Transform CREATE ENV commands"""
        return {
            "action": "CREATE_ENV",
            "type": "ENVIRONMENT_LOGICAL",
            "env_name": env_name.lower(),
            "project_name_specifier": project_specifier,
            "depends_on_env": depends_on_env.lower() if depends_on_env else None
        }
    
    def _transform_list_projects(self, list_kw, project_kw, plural_s=None):
        """Transform LIST PROJECTS commands"""
        return {"action": "LIST_PROJECTS", "type": "PROJECT_LOGICAL"}
    
    def _transform_get_project(self, get_kw, target_payload):
        """Transform GET PROJECT commands"""
        target_kind = target_payload["target_kind"]
        result = {"type": target_kind}
        
        if target_kind == "PROJECT_LOGICAL":
            result["action"] = "GET_PROJECT"
            result["project_name_specifier"] = target_payload["project_name_specifier"]
        else:
            result["action"] = "ERROR_UNKNOWN_GET_TARGET"
            result["error_details"] = target_payload
        
        return result
    
    def _transform_update_project(self, update_kw, project_kw, old_name, to_kw, new_name):
        """Transform UPDATE PROJECT commands"""
        return {
            "action": "UPDATE_PROJECT",
            "type": "PROJECT_LOGICAL",
            "old_project_name": old_name.lower(),
            "new_project_name": new_name.lower()
        }
    
    def _transform_drop_project(self, drop_kw, project_kw, project_name):
        """Transform DROP PROJECT commands"""
        return {
            "action": "DROP_PROJECT",
            "type": "PROJECT_LOGICAL",
            "user_project_name": project_name.lower()
        }
    
    def _transform_drop_env(self, drop_kw, env_kw, env_name, project_specifier=None):
        """Transform DROP ENV commands"""
        return {
            "action": "DROP_ENV",
            "type": "ENVIRONMENT_LOGICAL",
            "env_name": env_name.lower(),
            "project_name_specifier": project_specifier
        }
    
    def _transform_use_project_env(self, use_kw, project_kw, project_name, env_kw_val, env_name):
        """Transform USE PROJECT ENV commands"""
        return {
            "action": "USE_PROJECT_ENV",
            "type": "PROJECT_LOGICAL",
            "user_project_name": project_name.lower(),
            "env_name": env_name.lower()
        }
    
    def _transform_project_target_clause(self, for_or_from_kw, project_specifier):
        """Transform project target clauses"""
        return project_specifier
    
    def _transform_project_name_ref(self, project_kw, name):
        """Transform PROJECT NAME references"""
        return name.lower()
    
    def _transform_this_project_ref(self, this_kw, project_kw):
        """Transform THIS PROJECT references"""
        return "THIS_PROJECT_CONTEXT"
    
    def _transform_depends_on_clause(self, depends_literal, on_literal, env_name):
        """Transform DEPENDS ON clauses"""
        return env_name
    
    def _transform_get_target_choice(self, target_payload):
        """Transform GET target choices"""
        return target_payload
    
    def _transform_get_project_by_name(self, project_kw, project_name):
        """Transform GET PROJECT NAME"""
        return {
            "target_kind": "PROJECT_LOGICAL",
            "project_name_specifier": project_name.lower()
        }
    
    def _transform_get_this_project(self, this_kw, project_kw):
        """Transform GET THIS PROJECT"""
        return {
            "target_kind": "PROJECT_LOGICAL",
            "project_name_specifier": "THIS_PROJECT_CONTEXT"
        }
    
    # Command handlers - these will use the existing project management functionality
    def _handle_create_project(self, parsed_args: dict, context: KubeSolContext):
        """Handle CREATE PROJECT commands"""
        from kubeSol.projects import manager
        
        project_name = parsed_args.get("user_project_name")
        
        if not project_name:
            print("❌ Error: Project name must be provided for CREATE PROJECT.")
            return
        
        if not self.validate_project_name(project_name):
            print("❌ Error: Invalid project name.")
            return
        
        # Call the manager function to perform the action
        proj_id, def_env, def_ns, user_proj_name = manager.create_new_project(user_project_name=project_name)
        
        if proj_id and def_ns and def_env and user_proj_name:
            # Offer to switch to the new project
            if not context.is_project_context_active() or context.project_id != proj_id:
                confirm_use = input(f"Project '{user_proj_name}' created. Switch to its default environment '{def_env}' (namespace '{def_ns}')? (y/n): ").strip().lower()
                if confirm_use == 'y':
                    context.set_project_env_context(user_proj_name, proj_id, def_env, def_ns)
    
    def _handle_create_environment(self, parsed_args: dict, context: KubeSolContext):
        """Handle CREATE ENV commands"""
        from kubeSol.projects import manager
        
        env_name = parsed_args.get("env_name")
        project_specifier = parsed_args.get("project_name_specifier")
        depends_on_env = parsed_args.get("depends_on_env")
        
        if not env_name:
            print("❌ Error: Environment name must be provided for CREATE ENV.")
            return
        
        if not self.validate_environment_name(env_name):
            print("❌ Error: Invalid environment name.")
            return
        
        # Determine target project
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
        
        # Call manager function with depends_on_env parameter
        manager.add_environment_to_project(
            project_id=target_project_id,
            user_project_name=target_user_project_name,
            new_env_name=env_name,
            depends_on_env_name=depends_on_env
        )
    
    def _handle_list_projects(self, parsed_args: dict, context: KubeSolContext):
        """Handle LIST PROJECTS commands"""
        from kubeSol.projects import manager
        from tabulate import tabulate
        
        projects_data = manager.get_all_project_details()
        
        if not projects_data:
            print("ℹ️ No KubeSol projects found.")
            return
        
        headers = ["Project Display Name", "Project ID", "Environments"]
        table_data = []
        
        for p_info in projects_data:
            environments_str = ", ".join(p_info.get("environment_names", []))
            if not environments_str:
                environments_str = "-"
            
            table_data.append([
                p_info.get("project_display_name", "N/A"),
                p_info.get("project_id", "N/A"),
                environments_str
            ])
        
        print("\n KubeSol Projects:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def _handle_get_project(self, parsed_args: dict, context: KubeSolContext):
        """Handle GET PROJECT commands"""
        from kubeSol.projects import manager
        from tabulate import tabulate
        
        project_specifier = parsed_args.get("project_name_specifier")
        target_user_project_name = None
        
        if project_specifier == "THIS_PROJECT_CONTEXT":
            if not context.is_project_context_active() or not context.user_project_name:
                print("❌ 'GET THIS PROJECT' used, but no project context is currently active.")
                print("   Use 'USE PROJECT <name> ENV <name>' to set a context.")
                return
            target_user_project_name = context.user_project_name
            print(f"ℹ️ 'GET THIS PROJECT' resolved to current project: '{target_user_project_name}'")
        elif project_specifier:
            target_user_project_name = project_specifier
        else:
            if not context.is_project_context_active() or not context.user_project_name:
                print("❌ Project name not specified and no project context is active for GET PROJECT.")
                return
            print(f"ℹ️ No project name specified for GET PROJECT, using current project context: '{context.user_project_name}'.")
            target_user_project_name = context.user_project_name
        
        environments_data = manager.get_environments_for_project(user_project_name=target_user_project_name)
        
        if environments_data:
            proj_id_display = environments_data[0].get('project_id', 'N/A')
            actual_display_name = environments_data[0].get('project_display_name', target_user_project_name)
            
            print(f"\nEnvironments for Project: '{actual_display_name}' (ID: {proj_id_display})")
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
    
    def _handle_update_project(self, parsed_args: dict, context: KubeSolContext):
        """Handle UPDATE PROJECT commands"""
        from kubeSol.projects import manager
        
        old_display_name = parsed_args.get("old_project_name")
        new_display_name = parsed_args.get("new_project_name")
        
        if not old_display_name or not new_display_name:
            print("❌ Both old and new project display names must be provided for UPDATE PROJECT.")
            return
        
        if not self.validate_project_name(old_display_name) or not self.validate_project_name(new_display_name):
            print("❌ Error: Invalid project name(s).")
            return
        
        if old_display_name == new_display_name:
            print(f"ℹ️ Project display name is already '{new_display_name}'. No update performed.")
            return
        
        success = manager.update_project_display_name_label(
            old_display_name=old_display_name,
            new_display_name=new_display_name
        )
        
        # Update context if necessary
        if success and context.is_project_context_active() and context.user_project_name == old_display_name:
            if context.project_id and context.environment_name and context.current_namespace:
                context.set_project_env_context(
                    user_project_name=new_display_name,
                    project_id=context.project_id,
                    environment_name=context.environment_name,
                    namespace=context.current_namespace
                )
            else:
                print(f"ℹ️ Project display name updated. Current shell context was for '{old_display_name}', but full context details were unclear. Please use 'USE PROJECT' to refresh if needed.")
    
    def _handle_drop_project(self, parsed_args: dict, context: KubeSolContext):
        """Handle DROP PROJECT commands"""
        from kubeSol.projects import manager
        
        project_name = parsed_args.get("user_project_name")
        
        if not project_name:
            print("❌ Project name must be provided for DROP PROJECT.")
            return
        
        was_current_project = (context.is_project_context_active() and context.user_project_name == project_name)
        
        success = manager.delete_whole_project(user_project_name=project_name)
        
        if success and was_current_project:
            print(f"ℹ️ Project '{project_name}' was the active project. Context has been cleared to default.")
            context.clear_project_context()
    
    def _handle_drop_environment(self, parsed_args: dict, context: KubeSolContext):
        """Handle DROP ENV commands"""
        from kubeSol.projects import manager
        
        env_name = parsed_args.get("env_name")
        project_specifier = parsed_args.get("project_name_specifier")
        
        if not env_name:
            print("❌ Environment name must be provided for DROP ENVIRONMENT.")
            return
        
        # Determine target project (similar logic to create_environment)
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
            if not target_project_id:
                return
        else:
            if not context.is_project_context_active():
                print("❌ Project not specified for DROP ENVIRONMENT and no active context. Use 'FROM PROJECT <name>' or 'USE PROJECT ...' first.")
                return
            print(f"ℹ️ No project specified for DROP ENV, using current project context: '{context.user_project_name}'.")
            target_project_id = context.project_id
            target_user_project_name = context.user_project_name
        
        if not target_project_id or not target_user_project_name:
            print("❌ Could not determine target project for dropping environment.")
            return
        
        success = manager.delete_project_environment(
            project_id=target_project_id,
            user_project_name_for_msg=target_user_project_name,
            env_name=env_name
        )
        
        # Update context if current environment was deleted
        if success and context.project_id == target_project_id and context.environment_name == env_name:
            print(f"ℹ️ Environment '{env_name}' of project '{target_user_project_name}' was the current active environment.")
            from kubeSol.constants import DEFAULT_NAMESPACE, DEFAULT_PROJECT_ENVIRONMENT
            
            context.environment_name = None
            context.current_namespace = DEFAULT_NAMESPACE
            context.set_namespace_context(context.current_namespace)
            print(f"   Current environment context cleared. Namespace set to '{context.current_namespace}'.")
            print(f"   You may want to 'USE PROJECT {context.user_project_name} ENV <another_env>' or 'USE PROJECT ... ENV dev'.")
    
    def _handle_use_project_environment(self, parsed_args: dict, context: KubeSolContext):
        """Handle USE PROJECT ENV commands"""
        from kubeSol.projects import manager
        
        project_name = parsed_args.get("user_project_name")
        env_name = parsed_args.get("env_name")
        
        if not project_name or not env_name:
            print("❌ Both project display name and environment name are required for USE command.")
            return
        
        if not self.validate_project_name(project_name) or not self.validate_environment_name(env_name):
            print("❌ Error: Invalid project or environment name.")
            return
        
        proj_id, resolved_user_proj_name, physical_ns, error_msg = manager.resolve_project_and_environment_namespaces(
            user_project_name=project_name,
            environment_name=env_name
        )
        
        if error_msg:
            print(f"❌ {error_msg}")
            return
        
        if proj_id and physical_ns and resolved_user_proj_name:
            context.set_project_env_context(resolved_user_proj_name, proj_id, env_name, physical_ns)