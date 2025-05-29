# kubeSol/engine/executor.py
from kubeSol.parser.parser import parse_sql
from kubeSol.engine import k8s_api
from kubeSol.engine import script_runner
import os
import base64 
from kubeSol.constants import (
    ACTION_CREATE, ACTION_DELETE, ACTION_UPDATE, ACTION_GET, ACTION_LIST, ACTION_EXECUTE,
    RESOURCE_SECRET, RESOURCE_CONFIGMAP, RESOURCE_PARAMETER, RESOURCE_SCRIPT,
    FIELD_SCRIPT, DEFAULT_NAMESPACE,
    SCRIPT_CM_KEY_CODE, SCRIPT_CM_KEY_TYPE, SCRIPT_CM_KEY_ENGINE, 
    SCRIPT_CM_KEY_PARAMS_SPEC, SCRIPT_CM_KEY_DESCRIPTION, SCRIPT_CM_KEY_CODE_FROM_FILE,
    SCRIPT_ENGINE_K8S_JOB, SCRIPT_ENGINE_SPARK_OPERATOR # Added SPARK_OPERATOR for completeness
)
from kubernetes.client.exceptions import ApiException as K8sApiException 

# --- Command Handler Functions ---

def _handle_create_secret(name: str, fields: dict, namespace: str):
    """
    Handles the CREATE SECRET command.
    Distinguishes between plain string data and data from local files (prefixed with 'file_').
    """
    string_data_payload = {}
    b64_data_payload = {} 
    has_file_fields = False # Flag to determine if any file_ fields were processed

    for key, value in fields.items():
        if key.startswith("file_"):
            has_file_fields = True
            actual_key_in_secret = key[len("file_"):]
            if not actual_key_in_secret: 
                print(f"⚠️ Invalid key format for file-based secret data: '{key}'. Must be 'file_yourKeyName'. Skipping.")
                continue
            
            local_file_path = value
            try:
                print(f"ℹ️ Reading content for secret key '{actual_key_in_secret}' from file: {local_file_path}")
                with open(local_file_path, 'rb') as f_stream: 
                    file_content_bytes = f_stream.read()
                b64_data_payload[actual_key_in_secret] = base64.b64encode(file_content_bytes).decode('utf-8')
            except FileNotFoundError:
                raise ValueError(f"File not found at path: '{local_file_path}' for secret key '{actual_key_in_secret}'.")
            except Exception as e:
                raise ValueError(f"Error reading file '{local_file_path}' for secret key '{actual_key_in_secret}': {e}")
        else:
            string_data_payload[key] = value
    
    # If file fields were processed, or if string_data is empty (meaning only file fields or no fields)
    # use the function that supports mixed data. Otherwise, use the simpler original create_secret.
    if has_file_fields or not string_data_payload and b64_data_payload : 
        k8s_api.create_secret_with_mixed_data(
            name=name,
            string_data_payload=string_data_payload if string_data_payload else None,
            b64_data_payload=b64_data_payload if b64_data_payload else None, 
            namespace=namespace
        )
    elif string_data_payload: # Only string data fields were provided
        k8s_api.create_secret( # Call original function for stringData only
            name=name,
            data=string_data_payload, 
            namespace=namespace
        )
    else: # No fields provided at all (empty WITH clause)
        # Decide behavior: error, or create empty secret? For now, let k8s_api handle if it allows empty.
        # Calling create_secret_with_mixed_data with both None will likely create an empty data/stringData secret.
        k8s_api.create_secret_with_mixed_data(name=name, string_data_payload=None, b64_data_payload=None, namespace=namespace)


def _handle_create_parameter(name, fields, namespace):
    script_content_value = fields.get(FIELD_SCRIPT) 
    if script_content_value is None:
        raise ValueError(f"Field '{FIELD_SCRIPT}' is required for creating a {RESOURCE_PARAMETER}.")
    k8s_api.create_parameter(name=name, script_content=script_content_value, namespace=namespace)

def _handle_create_configmap(name, fields, namespace):
    k8s_api.create_configmap(name=name, data=fields, namespace=namespace)

def _handle_delete_secret(name, resource_type, namespace): 
    k8s_api.delete_secret(name=name, namespace=namespace)

def _handle_delete_parameter(name, resource_type, namespace): 
    k8s_api.delete_secret(name=name, namespace=namespace) 

def _handle_delete_configmap(name, resource_type, namespace): 
    k8s_api.delete_configmap(name=name, namespace=namespace)

def _handle_update_secret(name, fields, namespace):
    # Note: If update_secret needs to support file-based updates,
    # it would require similar logic to _handle_create_secret and
    # a corresponding k8s_api.update_secret_with_mixed_data function.
    # For now, assuming it updates with string data only.
    k8s_api.update_secret(name=name, data=fields, namespace=namespace)


def _handle_update_parameter(name, fields, namespace):
    script_content_value = fields.get(FIELD_SCRIPT) 
    if script_content_value is None:
        raise ValueError(f"Field '{FIELD_SCRIPT}' is required for updating a {RESOURCE_PARAMETER}.")
    k8s_api.update_parameter(name=name, script_content=script_content_value, namespace=namespace)

def _handle_update_configmap(name, fields, namespace):
    k8s_api.update_configmap(name=name, data=fields, namespace=namespace)

# --- SCRIPT resource handlers ---

def _handle_create_script(name: str, details: dict, namespace: str):
    """Handles the creation of a SCRIPT resource."""
    final_script_details_for_cm = details.copy() 

    code_inline = final_script_details_for_cm.get(SCRIPT_CM_KEY_CODE)
    code_from_file_path = final_script_details_for_cm.pop(SCRIPT_CM_KEY_CODE_FROM_FILE, None)

    if code_inline and code_from_file_path:
        raise ValueError(f"Cannot specify '{SCRIPT_CM_KEY_CODE}' and '{SCRIPT_CM_KEY_CODE_FROM_FILE}' simultaneously for script '{name}'.")

    if code_from_file_path:
        try:
            abs_file_path = os.path.abspath(code_from_file_path)
            print(f"ℹ️ Reading script code for '{name}' from file: {abs_file_path}")
            with open(abs_file_path, 'r', encoding='utf-8') as f_stream: 
                actual_script_code = f_stream.read() 
            final_script_details_for_cm[SCRIPT_CM_KEY_CODE] = actual_script_code
        except FileNotFoundError:
            raise ValueError(f"Script file not found at path: '{code_from_file_path}' (resolved to '{abs_file_path}') for script '{name}'.")
        except Exception as e:
            raise ValueError(f"Error reading script file '{code_from_file_path}' for script '{name}': {e}")
    elif not code_inline: 
        raise ValueError(f"Either '{SCRIPT_CM_KEY_CODE}' (inline code) or '{SCRIPT_CM_KEY_CODE_FROM_FILE}' (file path) must be specified for script '{name}'.")

    if final_script_details_for_cm.get(SCRIPT_CM_KEY_CODE) is None: 
         raise ValueError(f"Internal Error: Script code is missing for script '{name}' after processing CODE/CODE_FROM_FILE.")
    if not final_script_details_for_cm.get(SCRIPT_CM_KEY_TYPE): # Using direct import
        raise ValueError(f"Field '{SCRIPT_CM_KEY_TYPE}' (script type) is required for creating script '{name}'.")
    
    # Use direct imports for SCRIPT_CM_KEY_ENGINE and SCRIPT_ENGINE_K8S_JOB
    if not final_script_details_for_cm.get(SCRIPT_CM_KEY_ENGINE): 
        final_script_details_for_cm[SCRIPT_CM_KEY_ENGINE] = SCRIPT_ENGINE_K8S_JOB 
        print(f"ℹ️ Engine not specified for script '{name}', defaulting to '{SCRIPT_ENGINE_K8S_JOB}'.")

    print(f"[DEBUG EXECUTOR] Calling k8s_api.create_script_configmap for script: '{name}' in ns '{namespace}'. Details: {list(final_script_details_for_cm.keys())}")
    k8s_api.create_script_configmap(script_name=name, script_details=final_script_details_for_cm, namespace=namespace)
    print(f"[DEBUG EXECUTOR] Returned from k8s_api.create_script_configmap for script: '{name}'.")


def _handle_get_script(name: str, namespace: str):
    """Handles retrieving and displaying a SCRIPT resource."""
    script_data_map = k8s_api.get_script_configmap_data(script_name=name, namespace=namespace) 
    if script_data_map:
        cm_display_name = script_data_map.get('_cm_name', k8s_api.get_script_cm_name(name))
        print(f"📄 Script '{name}' details (from ConfigMap '{cm_display_name}'):")
        for key, value in script_data_map.items():
            if key == SCRIPT_CM_KEY_CODE: # Using direct import
                print(f"  {key}:\n---\n{value}\n---")
            elif key.startswith('_'): 
                continue
            else:
                print(f"  {key}: {value}")

def _handle_list_scripts(namespace: str):
    """Handles listing all SCRIPT resources in a namespace."""
    scripts_list = k8s_api.list_script_configmaps_data(namespace=namespace) 
    if not scripts_list:
        print(f"ℹ️ No scripts found in namespace '{namespace}'.")
        return
    print(f"📜 Scripts in namespace '{namespace}':")
    for script_data_item in scripts_list: 
        display_name = script_data_item.get('_script_name_from_cm', 'N/A') 
        # Using direct imports for constants
        script_type = script_data_item.get(SCRIPT_CM_KEY_TYPE, 'N/A') 
        script_engine = script_data_item.get(SCRIPT_CM_KEY_ENGINE, 'N/A') 
        description = script_data_item.get(SCRIPT_CM_KEY_DESCRIPTION, '') 
        actual_cm_name = script_data_item.get('_cm_name', 'N/A') 
        print(f"  - Name: {display_name} (Type: {script_type}, Engine: {script_engine}, Description: '{description}') (CM: {actual_cm_name})")


def _handle_delete_script(name: str, namespace: str):
    """Handles deleting a SCRIPT resource."""
    k8s_api.delete_script_configmap(script_name=name, namespace=namespace)

def _handle_update_script(name: str, updates_dict: dict, namespace: str): 
    """Handles updating a SCRIPT resource."""
    if not updates_dict:
        print(f"⚠️ No fields specified to update for script '{name}'. Nothing to do.")
        return
    
    print(f"ℹ️ Attempting to update script '{name}' in namespace '{namespace}' with fields: {list(updates_dict.keys())}")
    k8s_api.update_script_configmap(script_name=name, updates=updates_dict, namespace=namespace)


def _resolve_parameters_from_configmap(cm_name_for_params: str, key_prefix: str, namespace: str) -> dict:
    """Helper to read parameters from a specified ConfigMap."""
    resolved_params = {} 
    try:
        core_api_client = k8s_api.get_api_client() 
        parameter_cm_object = core_api_client.read_namespaced_config_map(name=cm_name_for_params, namespace=namespace) 
        if parameter_cm_object.data:
            for key, value in parameter_cm_object.data.items():
                if key.startswith(key_prefix):
                    param_name = key[len(key_prefix):]
                    resolved_params[param_name] = value
            print(f"ℹ️ Loaded {len(resolved_params)} parameters from ConfigMap '{cm_name_for_params}' with prefix '{key_prefix}'.")
        else:
            print(f"⚠️ ConfigMap '{cm_name_for_params}' for parameters is empty or has no data field.")
    except K8sApiException as e: 
        k8s_api._print_api_exception_details(e, f"Error reading parameters ConfigMap '{cm_name_for_params}'")
    return resolved_params


def _handle_execute_script(
    script_name_to_exec: str,
    parsed_instruction_details: dict, 
    namespace: str
):
    print(f"🚀 Attempting to execute script '{script_name_to_exec}' in namespace '{namespace}'...")
    
    custom_args_map = parsed_instruction_details.get("custom_args")
    args_from_cm_details = parsed_instruction_details.get("args_from_configmap")
    secret_mounts_list = parsed_instruction_details.get("secret_mounts", []) 

    script_cm_data_map = k8s_api.get_script_configmap_data(script_name=script_name_to_exec, namespace=namespace)
    if not script_cm_data_map:
        print(f"❌ Cannot execute script '{script_name_to_exec}': Script ConfigMap data not found.")
        return

    final_resolved_parameters = {}
    if args_from_cm_details:
        cm_name = args_from_cm_details.get("cm_name")
        key_prefix_str = args_from_cm_details.get("key_prefix", "")
        if cm_name:
            cm_loaded_params = _resolve_parameters_from_configmap(cm_name, key_prefix_str, namespace)
            final_resolved_parameters.update(cm_loaded_params)
    
    if custom_args_map:
        final_resolved_parameters.update(custom_args_map)

    # CORRECTED: Use direct constant names due to 'from ... import ...' style
    script_engine_type = script_cm_data_map.get(SCRIPT_CM_KEY_ENGINE, SCRIPT_ENGINE_K8S_JOB) 
    
    print(f"ℹ️ Script '{script_name_to_exec}' using engine: '{script_engine_type}'.")
    if final_resolved_parameters:
        print(f"   With resolved parameters: {list(final_resolved_parameters.keys())}")
    if secret_mounts_list:
        print(f"   With {len(secret_mounts_list)} secret mount(s) requested.")

    # CORRECTED: Use direct constant name
    if script_engine_type == SCRIPT_ENGINE_K8S_JOB:
        script_runner.run_script_as_k8s_job(
            cli_script_name=script_name_to_exec,
            script_cm_data=script_cm_data_map,
            resolved_parameters=final_resolved_parameters,
            namespace=namespace,
            secret_mounts=secret_mounts_list 
        )
    elif script_engine_type == SCRIPT_ENGINE_SPARK_OPERATOR: # Example for future
        print(f"ℹ️ Engine '{SCRIPT_ENGINE_SPARK_OPERATOR}' selected, but runner not yet implemented.")
        # script_runner.run_script_with_spark_operator(...) 
    else:
        print(f"❌ Execution engine '{script_engine_type}' is not supported for script '{script_name_to_exec}'.")

# --- Command Dispatcher ---
COMMAND_HANDLERS = {
    (ACTION_CREATE, RESOURCE_SECRET): _handle_create_secret,
    (ACTION_CREATE, RESOURCE_PARAMETER): _handle_create_parameter,
    (ACTION_CREATE, RESOURCE_CONFIGMAP): _handle_create_configmap,
    (ACTION_CREATE, RESOURCE_SCRIPT): _handle_create_script,

    (ACTION_DELETE, RESOURCE_SECRET): _handle_delete_secret,
    (ACTION_DELETE, RESOURCE_PARAMETER): _handle_delete_parameter,
    (ACTION_DELETE, RESOURCE_CONFIGMAP): _handle_delete_configmap,
    (ACTION_DELETE, RESOURCE_SCRIPT): _handle_delete_script,

    (ACTION_UPDATE, RESOURCE_SECRET): _handle_update_secret, 
    (ACTION_UPDATE, RESOURCE_PARAMETER): _handle_update_parameter,
    (ACTION_UPDATE, RESOURCE_CONFIGMAP): _handle_update_configmap,
    (ACTION_UPDATE, RESOURCE_SCRIPT): _handle_update_script,

    (ACTION_GET, RESOURCE_SCRIPT): _handle_get_script,
    (ACTION_LIST, RESOURCE_SCRIPT): _handle_list_scripts,
    (ACTION_EXECUTE, RESOURCE_SCRIPT): _handle_execute_script,
}

def execute_command(command_string: str, namespace: str = DEFAULT_NAMESPACE): 
    """
    Parses and executes a KubeSol command.
    """
    try:
        parsed_instruction = parse_sql(command_string) 
        print(f"🧾 Parsed: {parsed_instruction}")
    except Exception as e: 
        print(f"❌ Error parsing command: {e}")
        # For more detailed parsing errors during development:
        # import traceback
        # traceback.print_exc()
        return

    action_type = parsed_instruction.get("action") 
    resource_category = parsed_instruction.get("type") 
    resource_identifier = parsed_instruction.get("name") 
    
    handler_lookup_key = (action_type, resource_category) 
    target_handler_func = COMMAND_HANDLERS.get(handler_lookup_key) 

    if not target_handler_func:
        print(f"❌ Command not supported: Action '{action_type}' for resource type '{resource_category}'.")
        return
    
    try:
        if action_type == ACTION_EXECUTE:
            if resource_category == RESOURCE_SCRIPT:
                target_handler_func(
                    script_name_to_exec=resource_identifier,
                    parsed_instruction_details=parsed_instruction, 
                    namespace=namespace
                )
            else:
                print(f"❌ EXECUTE command is only supported for SCRIPT resources, not '{resource_category}'.")
        elif action_type == ACTION_CREATE:
            details_map = parsed_instruction.get("details") 
            fields_map = parsed_instruction.get("fields")   
            if resource_category == RESOURCE_SCRIPT:
                if details_map is None: 
                    print(f"❌ Error: 'details' (WITH clause content) are required for CREATE SCRIPT.")
                    return
                target_handler_func(name=resource_identifier, details=details_map, namespace=namespace)
            else: 
                if fields_map is None: 
                     print(f"❌ Error: Fields (WITH clause) are required for {action_type} {resource_category}.")
                     return
                target_handler_func(name=resource_identifier, fields=fields_map, namespace=namespace)
        elif action_type == ACTION_UPDATE:
            if resource_category == RESOURCE_SCRIPT:
                updates_data = parsed_instruction.get("updates") 
                if updates_data is None: 
                    print(f"❌ Error: 'updates' (SET clause content) are required for UPDATE SCRIPT.")
                    return
                target_handler_func(name=resource_identifier, updates=updates_data, namespace=namespace)
            else: 
                fields_data = parsed_instruction.get("fields") 
                if fields_data is None:
                    print(f"❌ Error: Fields (WITH clause) are required for {action_type} {resource_category}.")
                    return
                target_handler_func(name=resource_identifier, fields=fields_data, namespace=namespace)
        elif action_type == ACTION_GET or action_type == ACTION_DELETE:
            if resource_identifier is None: 
                print(f"❌ Error: Resource name is required for {action_type} {resource_category}.")
                return
            if action_type == ACTION_DELETE and resource_category in [RESOURCE_SECRET, RESOURCE_CONFIGMAP, RESOURCE_PARAMETER]: 
                 target_handler_func(name=resource_identifier, resource_type=resource_category, namespace=namespace)
            else: 
                 target_handler_func(name=resource_identifier, namespace=namespace)
        elif action_type == ACTION_LIST:
            target_handler_func(namespace=namespace)
        else:
            print(f"❌ Internal Error: Unhandled action structure for {action_type} {resource_category}")

    except ValueError as ve: 
        print(f"❌ Validation Error: {ve}")
    except K8sApiException as kube_api_error: 
        k8s_api._print_api_exception_details(kube_api_error, f"Kubernetes API error during '{action_type} {resource_category}' operation for '{resource_identifier or ''}'")
    except Exception as e:
        print(f"❌ Unexpected error executing command for '{resource_identifier if resource_identifier else resource_category}': {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()