# kubeSol/plugins/core/script_plugin.py
"""
Script Plugin for KubeSol

Handles script management and execution operations including CREATE SCRIPT, 
DELETE SCRIPT, UPDATE SCRIPT, EXECUTE SCRIPT, LIST SCRIPT, and GET SCRIPT.
This plugin extracts the script-related functionality from the monolithic codebase.
"""

from typing import Dict, List, Any, Callable, Tuple
import logging

from kubeSol.core.plugin_system.plugin_interface import ScriptPlugin as BaseScriptPlugin, PluginMetadata
from kubeSol.core.context import KubeSolContext

logger = logging.getLogger(__name__)

class ScriptPlugin(BaseScriptPlugin):
    """
    Plugin for managing scripts (PYTHON, PYSPARK) and their execution.
    
    This plugin provides the grammar rules, command handlers, and validation
    for script operations.
    """
    
    def __init__(self):
        super().__init__()
        self._supported_script_types = ["PYTHON", "PYSPARK", "SQL_SPARK"]
        self._supported_engines = ["K8S_JOB", "SPARK_OPERATOR"]
    
    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata"""
        return PluginMetadata(
            name="ScriptPlugin",
            version="1.0.0",
            description="Core script management and execution plugin for PYTHON, PYSPARK scripts",
            author="KubeSol Team",
            dependencies=[]
        )
    
    def get_grammar_rules(self) -> Dict[str, str]:
        """Return grammar rules for script operations"""
        return {
            # Script commands
            "create_script_command": "CREATE_KW SCRIPT_KW NAME TYPE_KW script_type_value [ENGINE_KW script_engine_value] WITH_KW script_content_fields",
            "list_scripts_command": "LIST_KW SCRIPT_KW \"S\"?",
            "delete_script_command": "DELETE_KW SCRIPT_KW NAME",
            "update_script_command": "UPDATE_KW SCRIPT_KW NAME SET_KW script_update_fields",
            "execute_script_command": "EXECUTE_KW SCRIPT_KW NAME [with_args_clause] [with_params_cm_clause] (secret_mount_clause)*",
            "get_script_command": "GET_KW SCRIPT_KW NAME",
            
            # Script content and update fields
            "script_content_fields": "script_content_field (\",\" script_content_field)*",
            "script_content_field": "\"CODE\"i \"=\" ESCAPED_STRING | \"CODE_FROM_FILE\"i \"=\" ESCAPED_STRING | \"PARAMS_SPEC\"i \"=\" ESCAPED_STRING | \"DESCRIPTION\"i \"=\" ESCAPED_STRING",
            "script_update_fields": "script_update_field (\",\" script_update_field)*", 
            "script_update_field": "\"CODE\"i \"=\" ESCAPED_STRING | \"PARAMS_SPEC\"i \"=\" ESCAPED_STRING | \"DESCRIPTION\"i \"=\" ESCAPED_STRING | \"ENGINE\"i \"=\" script_engine_value",
            
            # Script types and engines
            "script_type_value": "PYTHON_KW | PYSPARK_KW | SQL_SPARK_KW",
            "script_engine_value": "K8S_JOB_KW | SPARK_OPERATOR_KW",
            
            # Execute clauses
            "with_args_clause": "WITH_KW ARGS_KW \"(\" custom_params \")\"",
            "custom_params": "custom_param (\",\" custom_param)*",
            "custom_param": "NAME \"=\" ESCAPED_STRING",
            "with_params_cm_clause": "WITH_KW PARAMS_FROM_CONFIGMAP_KW NAME [KEY_PREFIX_KW ESCAPED_STRING]",
            "secret_mount_clause": "WITH_KW SECRET_KW NAME KEY_KW ESCAPED_STRING AS_KW ESCAPED_STRING",
            
            # Keywords
            "SCRIPT_KW": "\"SCRIPT\"i",
            "EXECUTE_KW": "\"EXECUTE\"i",
            "LIST_KW": "\"LIST\"i",
            "GET_KW": "\"GET\"i",
            "TYPE_KW": "\"TYPE\"i",
            "ENGINE_KW": "\"ENGINE\"i",
            "SET_KW": "\"SET\"i",
            "ARGS_KW": "\"ARGS\"i",
            "PARAMS_FROM_CONFIGMAP_KW": "\"PARAMS_FROM_CONFIGMAP\"i",
            "KEY_PREFIX_KW": "\"KEY_PREFIX\"i",
            "AS_KW": "\"AS\"i",
            "KEY_KW": "\"KEY\"i",
            "PYTHON_KW": "\"PYTHON\"i",
            "PYSPARK_KW": "\"PYSPARK\"i", 
            "SQL_SPARK_KW": "\"SQL_SPARK\"i",
            "K8S_JOB_KW": "\"K8S_JOB\"i",
            "SPARK_OPERATOR_KW": "\"SPARK_OPERATOR\"i"
        }
    
    def get_command_handlers(self) -> Dict[Tuple[str, str], Callable]:
        """Return command handlers for script operations"""
        return {
            ("CREATE", "SCRIPT"): self._handle_create_script,
            ("DELETE", "SCRIPT"): self._handle_delete_script,
            ("UPDATE", "SCRIPT"): self._handle_update_script,
            ("EXECUTE", "SCRIPT"): self._handle_execute_script,
            ("LIST", "SCRIPT"): self._handle_list_scripts,
            ("GET", "SCRIPT"): self._handle_get_script
        }
    
    def get_constants(self) -> Dict[str, Any]:
        """Return constants defined by this plugin"""
        return {
            # Actions
            "ACTION_EXECUTE": "EXECUTE",
            "ACTION_LIST": "LIST",
            "ACTION_GET": "GET",
            
            # Resource Types
            "RESOURCE_SCRIPT": "SCRIPT",
            
            # Script Types
            "SCRIPT_TYPE_PYTHON": "PYTHON",
            "SCRIPT_TYPE_PYSPARK": "PYSPARK", 
            "SCRIPT_TYPE_SQL_SPARK": "SQL_SPARK",
            
            # Script Engines
            "SCRIPT_ENGINE_K8S_JOB": "K8S_JOB",
            "SCRIPT_ENGINE_SPARK_OPERATOR": "SPARK_OPERATOR",
            
            # ConfigMap keys for scripts
            "SCRIPT_CM_PREFIX": "kubesol-script-",
            "SCRIPT_CM_LABEL_ROLE": "kubesol-role",
            "SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT": "script",
            "SCRIPT_CM_KEY_CODE": "code",
            "SCRIPT_CM_KEY_CODE_FROM_FILE": "codeFromFilePath",
            "SCRIPT_CM_KEY_TYPE": "scriptType",
            "SCRIPT_CM_KEY_ENGINE": "engine",
            "SCRIPT_CM_KEY_PARAMS_SPEC": "paramsSpec",
            "SCRIPT_CM_KEY_DESCRIPTION": "description"
        }
    
    def get_transformer_methods(self) -> Dict[str, Callable]:
        """Return transformer methods for grammar rules"""
        return {
            "create_script": self._transform_create_script,
            "list_scripts": self._transform_list_scripts,
            "delete_script": self._transform_delete_script,
            "update_script": self._transform_update_script,
            "execute_script": self._transform_execute_script,
            "get_script_command": self._transform_get_script,
            "script_content_fields": self._transform_script_content_fields,
            "script_update_fields": self._transform_script_update_fields,
            "script_type_value": self._transform_script_type_value,
            "script_engine_value": self._transform_script_engine_value,
            "with_args_clause": self._transform_with_args_clause,
            "with_params_cm_clause": self._transform_with_params_cm_clause,
            "secret_mount_clause": self._transform_secret_mount_clause,
            "custom_params": self._transform_custom_params,
            "custom_param": self._transform_custom_param,
            "PYTHON_KW": lambda token: "PYTHON",
            "PYSPARK_KW": lambda token: "PYSPARK",
            "SQL_SPARK_KW": lambda token: "SQL_SPARK",
            "K8S_JOB_KW": lambda token: "K8S_JOB",
            "SPARK_OPERATOR_KW": lambda token: "SPARK_OPERATOR"
        }
    
    def get_supported_script_types(self) -> List[str]:
        """Return list of supported script types"""
        return self._supported_script_types.copy()
    
    def get_supported_execution_engines(self) -> List[str]:
        """Return list of supported execution engines"""
        return self._supported_engines.copy()
    
    def validate_script_code(self, script_type: str, code: str) -> bool:
        """Validate script code for a specific script type"""
        if script_type not in self._supported_script_types:
            logger.error(f"Unsupported script type: {script_type}")
            return False
        
        if not code or not code.strip():
            logger.error("Script code cannot be empty")
            return False
        
        # Basic validation - could be extended with syntax checking
        if script_type == "PYTHON":
            return self._validate_python_code(code)
        elif script_type == "PYSPARK":
            return self._validate_pyspark_code(code)
        elif script_type == "SQL_SPARK":
            return self._validate_sql_spark_code(code)
        
        return True
    
    def prepare_execution_environment(self, script_name: str, script_type: str, engine: str) -> Dict[str, Any]:
        """Prepare the execution environment for a script"""
        if engine not in self._supported_engines:
            raise ValueError(f"Unsupported execution engine: {engine}")
        
        env_config = {
            "script_name": script_name,
            "script_type": script_type,
            "engine": engine,
            "namespace": "default"  # Will be overridden by context
        }
        
        if engine == "K8S_JOB":
            env_config.update({
                "image": self._get_docker_image_for_script_type(script_type),
                "command": self._get_container_command_for_script_type(script_type)
            })
        
        return env_config
    
    def _validate_python_code(self, code: str) -> bool:
        """Basic Python code validation"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            logger.error(f"Python syntax error: {e}")
            return False
    
    def _validate_pyspark_code(self, code: str) -> bool:
        """Basic PySpark code validation"""
        # For now, just validate as Python code
        return self._validate_python_code(code)
    
    def _validate_sql_spark_code(self, code: str) -> bool:
        """Basic SQL Spark code validation"""
        # Basic validation - check for SQL keywords
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']
        code_upper = code.upper()
        return any(keyword in code_upper for keyword in sql_keywords)
    
    def _get_docker_image_for_script_type(self, script_type: str) -> str:
        """Get appropriate Docker image for script type"""
        if script_type == "PYTHON":
            return "cloudsaur/arrow-to-gcs:latest"
        elif script_type in ["PYSPARK", "SQL_SPARK"]:
            return "cloudsaur/arrow-to-gcs:latest"
        else:
            return "python:3.9-slim"
    
    def _get_container_command_for_script_type(self, script_type: str) -> List[str]:
        """Get container command for script type"""
        return ["python", "/kubesol_scripts/code"]
    
    # Transformer methods
    def _transform_create_script(self, *args):
        """Transform CREATE SCRIPT commands"""
        # Handle variable number of arguments due to optional ENGINE clause
        create_kw = args[0]
        script_kw = args[1] 
        script_name = args[2]
        type_kw = args[3]
        script_type = args[4]
        
        # Check if ENGINE clause is present
        if len(args) >= 8 and args[5] is not None:  # ENGINE clause present
            engine_kw = args[5]
            script_engine = args[6]
            with_kw = args[7]
            script_content = args[8] if len(args) > 8 else {}
        else:  # No ENGINE clause
            script_engine = None
            with_kw = args[5]
            script_content = args[6] if len(args) > 6 else {}
        
        details = script_content.copy()
        details["scriptType"] = script_type
        
        if script_engine:
            details["engine"] = script_engine
        
        return {
            "action": "CREATE",
            "type": "SCRIPT",
            "name": script_name.lower(),
            "details": details
        }
    
    def _transform_list_scripts(self, list_kw, script_kw, plural_s=None):
        """Transform LIST SCRIPTS commands"""
        return {"action": "LIST", "type": "SCRIPT"}
    
    def _transform_delete_script(self, delete_kw, script_kw, script_name):
        """Transform DELETE SCRIPT commands"""
        return {"action": "DELETE", "type": "SCRIPT", "name": script_name.lower()}
    
    def _transform_update_script(self, update_kw, script_kw, script_name, set_kw, updates_dict):
        """Transform UPDATE SCRIPT commands"""
        return {
            "action": "UPDATE",
            "type": "SCRIPT", 
            "name": script_name.lower(),
            "updates": updates_dict
        }
    
    def _transform_execute_script(self, execute_kw, script_kw, script_name, *optional_clauses):
        """Transform EXECUTE SCRIPT commands"""
        instruction = {
            "action": "EXECUTE",
            "type": "SCRIPT",
            "name": script_name.lower(),
            "custom_args": None,
            "args_from_configmap": None,
            "secret_mounts": []
        }
        
        for clause_result in optional_clauses:
            if clause_result and isinstance(clause_result, dict):
                if "custom_args" in clause_result:
                    instruction["custom_args"] = clause_result["custom_args"]
                elif "args_from_configmap" in clause_result:
                    instruction["args_from_configmap"] = clause_result["args_from_configmap"]
                elif clause_result.get("type") == "secret_mount_spec":
                    instruction["secret_mounts"].append(clause_result)
        
        return instruction
    
    def _transform_get_script(self, get_kw, script_kw, script_name):
        """Transform GET SCRIPT commands"""
        return {"action": "GET", "type": "SCRIPT", "name": script_name.lower()}
    
    def _transform_script_content_fields(self, field_tuples_list):
        """Transform script content fields"""
        return dict(field_tuples_list)
    
    def _transform_script_update_fields(self, field_tuples_list):
        """Transform script update fields"""
        return dict(field_tuples_list)
    
    def _transform_script_type_value(self, *items):
        """Transform script type values"""
        return items[0] if items else None
    
    def _transform_script_engine_value(self, *items):
        """Transform script engine values"""
        return items[0] if items else None
    
    def _transform_with_args_clause(self, with_kw, args_kw, params_dict):
        """Transform WITH ARGS clauses"""
        return {"custom_args": params_dict}
    
    def _transform_with_params_cm_clause(self, with_kw, params_from_cm_kw, cm_name, optional_key_prefix=None):
        """Transform WITH PARAMS_FROM_CONFIGMAP clauses"""
        res = {"cm_name": cm_name}
        if optional_key_prefix:
            res["key_prefix"] = optional_key_prefix[1] if isinstance(optional_key_prefix, list) else optional_key_prefix
        return {"args_from_configmap": res}
    
    def _transform_secret_mount_clause(self, with_kw, secret_kw, secret_name, key_kw, key_in_secret, as_kw, mount_path):
        """Transform secret mount clauses"""
        return {
            "type": "secret_mount_spec",
            "secret_name": secret_name,
            "key_in_secret": key_in_secret,
            "mount_path_in_pod": mount_path
        }
    
    def _transform_custom_params(self, param_list):
        """Transform custom parameters"""
        return dict(param_list)
    
    def _transform_custom_param(self, name_str, value_str):
        """Transform individual custom parameters"""
        return (name_str, value_str)
    
    # Command handlers
    def _handle_create_script(self, parsed_args: dict, context: KubeSolContext):
        """Handle CREATE SCRIPT commands"""
        from kubeSol.engine import k8s_api
        
        script_name = parsed_args.get("name")
        details = parsed_args.get("details", {})
        namespace = context.current_namespace
        
        script_type = details.get("scriptType")
        if not script_type:
            print("❌ Error: Script type is required.")
            return
        
        # Handle code from file if specified
        if "codeFromFilePath" in details:
            file_path = details["codeFromFilePath"]
            try:
                with open(file_path, 'r') as f:
                    code_content = f.read()
                details["code"] = code_content
                del details["codeFromFilePath"]
                print(f"ℹ️ Loaded script code from file: {file_path}")
            except Exception as e:
                print(f"❌ Error reading code from file '{file_path}': {e}")
                return
        
        code = details.get("code")
        if not code:
            print("❌ Error: Script code is required.")
            return
        
        if not self.validate_script_code(script_type, code):
            print("❌ Error: Script code validation failed.")
            return
        
        print(f"Creating script '{script_name}' of type '{script_type}' in namespace '{namespace}'...")
        
        try:
            success = k8s_api.create_script_configmap(
                script_name=script_name,
                namespace=namespace,
                script_data=details
            )
            
            if success:
                print(f"✅ Script '{script_name}' created successfully.")
            else:
                print(f"❌ Failed to create script '{script_name}'.")
                
        except Exception as e:
            print(f"❌ Error creating script '{script_name}': {e}")
            logger.error(f"Error creating script '{script_name}': {e}")
    
    def _handle_delete_script(self, parsed_args: dict, context: KubeSolContext):
        """Handle DELETE SCRIPT commands"""
        from kubeSol.engine import k8s_api
        
        script_name = parsed_args.get("name")
        namespace = context.current_namespace
        
        print(f"Deleting script '{script_name}' from namespace '{namespace}'...")
        
        try:
            success = k8s_api.delete_script_configmap(
                script_name=script_name,
                namespace=namespace
            )
            
            if success:
                print(f"✅ Script '{script_name}' deleted successfully.")
            else:
                print(f"❌ Failed to delete script '{script_name}'.")
                
        except Exception as e:
            print(f"❌ Error deleting script '{script_name}': {e}")
            logger.error(f"Error deleting script '{script_name}': {e}")
    
    def _handle_update_script(self, parsed_args: dict, context: KubeSolContext):
        """Handle UPDATE SCRIPT commands"""
        from kubeSol.engine import k8s_api
        
        script_name = parsed_args.get("name")
        updates = parsed_args.get("updates", {})
        namespace = context.current_namespace
        
        if not updates:
            print("❌ Error: No updates specified.")
            return
        
        # Validate code if being updated
        if "code" in updates:
            # We need to get the current script type to validate
            current_script = k8s_api.get_script_configmap(script_name, namespace)
            if current_script:
                script_type = current_script.get("scriptType", "PYTHON")
                if not self.validate_script_code(script_type, updates["code"]):
                    print("❌ Error: Updated script code validation failed.")
                    return
        
        print(f"Updating script '{script_name}' in namespace '{namespace}'...")
        
        try:
            success = k8s_api.update_script_configmap(
                script_name=script_name,
                namespace=namespace,
                updates=updates
            )
            
            if success:
                print(f"✅ Script '{script_name}' updated successfully.")
            else:
                print(f"❌ Failed to update script '{script_name}'.")
                
        except Exception as e:
            print(f"❌ Error updating script '{script_name}': {e}")
            logger.error(f"Error updating script '{script_name}': {e}")
    
    def _handle_execute_script(self, parsed_args: dict, context: KubeSolContext):
        """Handle EXECUTE SCRIPT commands"""
        from kubeSol.engine import script_runner
        
        script_name = parsed_args.get("name")
        custom_args = parsed_args.get("custom_args", {})
        args_from_configmap = parsed_args.get("args_from_configmap")
        secret_mounts = parsed_args.get("secret_mounts", [])
        namespace = context.current_namespace
        
        print(f"Executing script '{script_name}' in namespace '{namespace}'...")
        
        try:
            # Get script data
            from kubeSol.engine import k8s_api
            script_data = k8s_api.get_script_configmap(script_name, namespace)
            
            if not script_data:
                print(f"❌ Script '{script_name}' not found.")
                return
            
            # Resolve parameters
            resolved_params = custom_args.copy()
            
            if args_from_configmap:
                cm_name = args_from_configmap["cm_name"]
                key_prefix = args_from_configmap.get("key_prefix", "")
                
                cm_params = k8s_api.get_configmap_params(cm_name, namespace, key_prefix)
                if cm_params:
                    resolved_params.update(cm_params)
            
            # Execute the script
            script_runner.run_script_as_k8s_job(
                cli_script_name=script_name,
                script_cm_data=script_data,
                resolved_parameters=resolved_params,
                namespace=namespace,
                secret_mounts=secret_mounts
            )
            
        except Exception as e:
            print(f"❌ Error executing script '{script_name}': {e}")
            logger.error(f"Error executing script '{script_name}': {e}")
    
    def _handle_list_scripts(self, parsed_args: dict, context: KubeSolContext):
        """Handle LIST SCRIPTS commands"""
        from kubeSol.engine import k8s_api
        
        namespace = context.current_namespace
        
        print(f"Listing scripts in namespace '{namespace}'...")
        
        try:
            scripts = k8s_api.list_script_configmaps(namespace)
            
            if not scripts:
                print("ℹ️ No scripts found.")
                return
            
            print(f"\nScripts in namespace '{namespace}':")
            for script_name, script_data in scripts.items():
                script_type = script_data.get("scriptType", "Unknown")
                engine = script_data.get("engine", "K8S_JOB")
                description = script_data.get("description", "No description")
                print(f"  - {script_name} ({script_type}, {engine}): {description}")
                
        except Exception as e:
            print(f"❌ Error listing scripts: {e}")
            logger.error(f"Error listing scripts: {e}")
    
    def _handle_get_script(self, parsed_args: dict, context: KubeSolContext):
        """Handle GET SCRIPT commands"""
        from kubeSol.engine import k8s_api
        
        script_name = parsed_args.get("name")
        namespace = context.current_namespace
        
        print(f"Getting script '{script_name}' from namespace '{namespace}'...")
        
        try:
            script_data = k8s_api.get_script_configmap(script_name, namespace)
            
            if not script_data:
                print(f"❌ Script '{script_name}' not found.")
                return
            
            print(f"\nScript Details: {script_name}")
            print(f"  Type: {script_data.get('scriptType', 'Unknown')}")
            print(f"  Engine: {script_data.get('engine', 'K8S_JOB')}")
            print(f"  Description: {script_data.get('description', 'No description')}")
            
            if script_data.get('paramsSpec'):
                print(f"  Parameters: {script_data['paramsSpec']}")
            
            code = script_data.get('code', '')
            if code:
                print(f"  Code ({len(code)} characters):")
                print("    " + "\n    ".join(code.split('\n')[:10]))  # Show first 10 lines
                if len(code.split('\n')) > 10:
                    print("    ...")
                
        except Exception as e:
            print(f"❌ Error getting script '{script_name}': {e}")
            logger.error(f"Error getting script '{script_name}': {e}")