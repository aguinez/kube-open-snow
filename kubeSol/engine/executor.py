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
    SCRIPT_ENGINE_K8S_JOB, SCRIPT_ENGINE_SPARK_OPERATOR,
    # NUEVAS CONSTANTES DE ACCIÓN Y TIPOS LÓGICOS
    ACTION_CREATE_PROJECT, ACTION_CREATE_ENV, ACTION_LIST_PROJECTS, ACTION_GET_PROJECT,
    ACTION_UPDATE_PROJECT, ACTION_DROP_PROJECT, ACTION_DROP_ENV, ACTION_USE_PROJECT_ENV,
    LOGICAL_TYPE_PROJECT, LOGICAL_TYPE_ENVIRONMENT
)
from kubernetes.client.exceptions import ApiException as K8sApiException
from tabulate import tabulate

# --- NUEVAS IMPORTACIONES ---
from kubeSol.projects import cli_handlers as project_cli_handlers
from kubeSol.projects.context import KubeSolContext 


# --- Handlers Existentes para Recursos (_handle_create_secret, _handle_create_script, etc.) ---
# (Asegúrate de que todas estas funciones estén completas y correctas aquí, como en tu última versión funcional)
# (Por brevedad, no las repito todas, pero deben estar aquí)
def _handle_create_secret(name: str, fields: dict, namespace: str):
    string_data_payload = {}
    b64_data_payload = {} 
    has_file_fields = False 
    for key, value in fields.items():
        if key.startswith("file_"):
            has_file_fields = True
            actual_key_in_secret = key[len("file_"):]
            if not actual_key_in_secret: 
                print(f"⚠️ Invalid key format for file-based secret data: '{key}'. Skipping.")
                continue
            local_file_path = value
            try:
                with open(local_file_path, 'rb') as f_stream: 
                    file_content_bytes = f_stream.read()
                b64_data_payload[actual_key_in_secret] = base64.b64encode(file_content_bytes).decode('utf-8')
            except FileNotFoundError: raise ValueError(f"File not found for secret key '{actual_key_in_secret}': {local_file_path}")
            except Exception as e: raise ValueError(f"Error reading file for secret key '{actual_key_in_secret}': {e}")
        else: string_data_payload[key] = value
    if has_file_fields or (not string_data_payload and b64_data_payload): 
        k8s_api.create_secret_with_mixed_data(name=name, string_data_payload=string_data_payload or None, 
                                          b64_data_payload=b64_data_payload or None, namespace=namespace)
    elif string_data_payload: k8s_api.create_secret(name=name, data=string_data_payload, namespace=namespace)
    else: k8s_api.create_secret_with_mixed_data(name=name, string_data_payload=None, b64_data_payload=None, namespace=namespace)

def _handle_create_parameter(name, fields, namespace):
    content = fields.get(FIELD_SCRIPT)
    if content is None: raise ValueError(f"Field '{FIELD_SCRIPT}' is required for {RESOURCE_PARAMETER}.")
    k8s_api.create_parameter(name=name, script_content=content, namespace=namespace)
def _handle_create_configmap(name, fields, namespace): k8s_api.create_configmap(name=name, data=fields, namespace=namespace)
def _handle_delete_secret(name, resource_type, namespace): k8s_api.delete_secret(name=name, namespace=namespace)
def _handle_delete_parameter(name, resource_type, namespace): k8s_api.delete_secret(name=name, namespace=namespace)
def _handle_delete_configmap(name, resource_type, namespace): k8s_api.delete_configmap(name=name, namespace=namespace)
def _handle_update_secret(name, fields, namespace): k8s_api.update_secret(name=name, data=fields, namespace=namespace)
def _handle_update_parameter(name, fields, namespace): 
    content = fields.get(FIELD_SCRIPT)
    if content is None: raise ValueError(f"Field '{FIELD_SCRIPT}' is required for {RESOURCE_PARAMETER}.")
    k8s_api.update_parameter(name=name, script_content=content, namespace=namespace)
def _handle_update_configmap(name, fields, namespace): k8s_api.update_configmap(name=name, data=fields, namespace=namespace)
def _handle_create_script(name: str, details: dict, namespace: str):
    final_script_details_for_cm = details.copy() 
    code_inline = final_script_details_for_cm.get(SCRIPT_CM_KEY_CODE)
    code_from_file_path = final_script_details_for_cm.pop(SCRIPT_CM_KEY_CODE_FROM_FILE, None)
    if code_inline and code_from_file_path: raise ValueError(f"Cannot specify '{SCRIPT_CM_KEY_CODE}' and '{SCRIPT_CM_KEY_CODE_FROM_FILE}' for script '{name}'.")
    if code_from_file_path:
        try:
            abs_file_path = os.path.abspath(code_from_file_path)
            with open(abs_file_path, 'r', encoding='utf-8') as f: actual_script_code = f.read()
            final_script_details_for_cm[SCRIPT_CM_KEY_CODE] = actual_script_code
        except Exception as e: raise ValueError(f"Error reading script file '{code_from_file_path}': {e}")
    elif not code_inline: raise ValueError(f"Either '{SCRIPT_CM_KEY_CODE}' or '{SCRIPT_CM_KEY_CODE_FROM_FILE}' must be specified for script '{name}'.")
    if final_script_details_for_cm.get(SCRIPT_CM_KEY_CODE) is None: raise ValueError(f"Script code missing for '{name}'.")
    if not final_script_details_for_cm.get(SCRIPT_CM_KEY_TYPE): raise ValueError(f"'{SCRIPT_CM_KEY_TYPE}' is required for script '{name}'.")
    if not final_script_details_for_cm.get(SCRIPT_CM_KEY_ENGINE):
        final_script_details_for_cm[SCRIPT_CM_KEY_ENGINE] = SCRIPT_ENGINE_K8S_JOB
    k8s_api.create_script_configmap(script_name=name, script_details=final_script_details_for_cm, namespace=namespace)

def _handle_get_script(name: str, namespace: str):
    data = k8s_api.get_script_configmap_data(script_name=name, namespace=namespace)
    if not data: return
    cm_name = data.get('_cm_name', k8s_api.get_script_cm_name(name))
    print(f"📄 Script Details for '{name}' (from ConfigMap: '{cm_name}')")
    meta, code_val = [], None # Renamed code to code_val to avoid conflict
    for k,v in sorted(data.items()):
        if k == SCRIPT_CM_KEY_CODE: code_val = v
        elif k.startswith('_'): continue
        else: meta.append([k, str(v)[:70] + ('...' if len(str(v)) > 70 else '')])
    if meta: print(tabulate(meta, headers=["Attribute", "Value"], tablefmt="grid"))
    if code_val is not None: print(f"\n🖥️ Code ({SCRIPT_CM_KEY_CODE}):\n--- BEGIN CODE ---\n{code_val}\n--- END CODE ---")

def _handle_list_scripts(namespace: str):
    scripts = k8s_api.list_script_configmaps_data(namespace=namespace)
    if not scripts: print(f"ℹ️ No scripts found in '{namespace}'."); return
    print(f"📜 Scripts in namespace '{namespace}':")
    headers = ["Name", "Type", "Engine", "Description", "ConfigMap Name"]
    data = [[s.get('_script_name_from_cm','N/A'), s.get(SCRIPT_CM_KEY_TYPE,'N/A'), s.get(SCRIPT_CM_KEY_ENGINE,'N/A'), 
             (s.get(SCRIPT_CM_KEY_DESCRIPTION,'')[:47] + '...' if len(s.get(SCRIPT_CM_KEY_DESCRIPTION,'')) > 50 else s.get(SCRIPT_CM_KEY_DESCRIPTION,'')), 
             s.get('_cm_name','N/A')] for s in scripts]
    if data: print(tabulate(data, headers=headers, tablefmt="grid"))

def _handle_delete_script(name: str, namespace: str): k8s_api.delete_script_configmap(script_name=name, namespace=namespace)
def _handle_update_script(name: str, updates_dict: dict, namespace: str): 
    if not updates_dict: print(f"⚠️ No fields to update for script '{name}'."); return
    k8s_api.update_script_configmap(script_name=name, updates=updates_dict, namespace=namespace)

def _resolve_parameters_from_configmap(cm_name, prefix, ns):
    # Awaiting full implementation of k8s_api.get_configmap_data or using direct client call
    print(f"DEBUG: _resolve_parameters_from_configmap called for {cm_name} (not fully implemented in example).")
    return {} # Placeholder

def _handle_execute_script(script_name_to_exec: str, parsed_instruction_details: dict, namespace: str):
    custom_args = parsed_instruction_details.get("custom_args")
    args_from_cm = parsed_instruction_details.get("args_from_configmap")
    secret_mounts = parsed_instruction_details.get("secret_mounts", [])
    cm_data = k8s_api.get_script_configmap_data(script_name_to_exec, namespace)
    if not cm_data: print(f"❌ Script '{script_name_to_exec}' not found."); return
    params = {}
    if args_from_cm and "cm_name" in args_from_cm: 
        params.update(_resolve_parameters_from_configmap(args_from_cm["cm_name"], args_from_cm.get("key_prefix",""), namespace))
    if custom_args: params.update(custom_args)
    engine = cm_data.get(SCRIPT_CM_KEY_ENGINE, SCRIPT_ENGINE_K8S_JOB)
    print(f"ℹ️ Script '{script_name_to_exec}' using engine: '{engine}'.")
    if params: print(f"   With resolved parameters: {list(params.keys())}")
    if secret_mounts: print(f"   With {len(secret_mounts)} secret mount(s) requested.")
    if engine == SCRIPT_ENGINE_K8S_JOB:
        script_runner.run_script_as_k8s_job(script_name_to_exec, cm_data, params, namespace, secret_mounts)
    elif engine == SCRIPT_ENGINE_SPARK_OPERATOR: 
        print(f"ℹ️ Engine '{SCRIPT_ENGINE_SPARK_OPERATOR}' selected, but runner not yet implemented.")
    else:
        print(f"❌ Execution engine '{engine}' is not supported for script '{script_name_to_exec}'.")

# --- Diccionario COMMAND_HANDLERS Actualizado ---
COMMAND_HANDLERS = {
    # Comandos de recursos existentes
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

    # NUEVOS Handlers para Comandos de Proyecto y Entorno
    (ACTION_CREATE_PROJECT, LOGICAL_TYPE_PROJECT): project_cli_handlers.handle_create_project,
    (ACTION_CREATE_ENV, LOGICAL_TYPE_ENVIRONMENT): project_cli_handlers.handle_create_environment,
    (ACTION_LIST_PROJECTS, LOGICAL_TYPE_PROJECT): project_cli_handlers.handle_list_projects,
    (ACTION_GET_PROJECT, LOGICAL_TYPE_PROJECT): project_cli_handlers.handle_get_project,
    (ACTION_UPDATE_PROJECT, LOGICAL_TYPE_PROJECT): project_cli_handlers.handle_update_project,
    (ACTION_DROP_PROJECT, LOGICAL_TYPE_PROJECT): project_cli_handlers.handle_drop_project,
    (ACTION_DROP_ENV, LOGICAL_TYPE_ENVIRONMENT): project_cli_handlers.handle_drop_environment,
    (ACTION_USE_PROJECT_ENV, LOGICAL_TYPE_PROJECT): project_cli_handlers.handle_use_project_environment,
}

# execute_command ahora acepta KubeSolContext
def execute_command(command_string: str, context: KubeSolContext): # <--- MODIFICADO para aceptar context
    """
    Parsea y ejecuta un comando de KubeSol usando el contexto proporcionado.
    """
    try:
        parsed_instruction = parse_sql(command_string) 
        print(f"🧾 Parsed: {parsed_instruction}") # Dejar para depuración por ahora
    except Exception as e: 
        print(f"❌ Error parsing command.")
        print(f"   Type: {type(e)}, Details: {e}")
        import traceback
        traceback.print_exc()
        return

    action_type = parsed_instruction.get("action") 
    command_object_type = parsed_instruction.get("type") # Será LOGICAL_TYPE_* o RESOURCE_*
    
    handler_lookup_key = (action_type, command_object_type) 
    target_handler_func = COMMAND_HANDLERS.get(handler_lookup_key) 

    if not target_handler_func:
        print(f"❌ Command not supported: Action '{action_type}' for type '{command_object_type}'.")
        return
    
    # Determinar el namespace actual para operaciones de recursos
    current_k8s_namespace = context.current_namespace

    try:
        # Diferenciar cómo se llaman los handlers
        if command_object_type in [LOGICAL_TYPE_PROJECT, LOGICAL_TYPE_ENVIRONMENT] or \
           action_type == ACTION_USE_PROJECT_ENV: # USE_PROJECT_ENV actualiza el contexto
            # Los handlers de proyecto/entorno esperan (parsed_args_dict, context_obj)
            target_handler_func(parsed_args=parsed_instruction, context=context)
        else:
            # Los handlers de recursos existentes esperan argumentos específicos
            resource_identifier = parsed_instruction.get("name")
            if action_type == ACTION_EXECUTE:
                target_handler_func(
                    script_name_to_exec=resource_identifier,
                    parsed_instruction_details=parsed_instruction, 
                    namespace=current_k8s_namespace
                )
            elif action_type == ACTION_CREATE:
                details_map = parsed_instruction.get("details") 
                fields_map = parsed_instruction.get("fields")   
                if command_object_type == RESOURCE_SCRIPT:
                    if details_map is None: raise ValueError("'details' required for CREATE SCRIPT.")
                    target_handler_func(name=resource_identifier, details=details_map, namespace=current_k8s_namespace)
                else: 
                    if fields_map is None: raise ValueError(f"Fields required for CREATE {command_object_type}.")
                    target_handler_func(name=resource_identifier, fields=fields_map, namespace=current_k8s_namespace)
            elif action_type == ACTION_UPDATE:
                if command_object_type == RESOURCE_SCRIPT:
                    updates_data = parsed_instruction.get("updates") 
                    if updates_data is None: raise ValueError("'updates' required for UPDATE SCRIPT.")
                    target_handler_func(name=resource_identifier, updates=updates_data, namespace=current_k8s_namespace)
                else: 
                    fields_data = parsed_instruction.get("fields") 
                    if fields_data is None: raise ValueError(f"Fields required for UPDATE {command_object_type}.")
                    target_handler_func(name=resource_identifier, fields=fields_data, namespace=current_k8s_namespace)
            elif action_type == ACTION_GET or action_type == ACTION_DELETE:
                if resource_identifier is None: raise ValueError(f"Resource name required for {action_type} {command_object_type}.")
                if action_type == ACTION_DELETE and command_object_type in [RESOURCE_SECRET, RESOURCE_CONFIGMAP, RESOURCE_PARAMETER]: 
                     target_handler_func(name=resource_identifier, resource_type=command_object_type, namespace=current_k8s_namespace)
                else: 
                     target_handler_func(name=resource_identifier, namespace=current_k8s_namespace)
            elif action_type == ACTION_LIST:
                # LIST_PROJECTS es manejado por project_cli_handlers
                # LIST_SCRIPTS (y otras listas de recursos) solo necesitan namespace
                target_handler_func(namespace=current_k8s_namespace)
            else:
                print(f"❌ Internal Error: Dispatch failed for {action_type} {command_object_type}")

    except ValueError as ve: 
        print(f"❌ Validation Error: {ve}")
    except K8sApiException as kube_api_error: 
        k8s_api._print_api_exception_details(kube_api_error, f"K8s API error during '{action_type} {command_object_type}' operation for '{parsed_instruction.get('name', '')}'")
    except Exception as e:
        print(f"❌ Unexpected error executing command '{action_type} {command_object_type}': {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()