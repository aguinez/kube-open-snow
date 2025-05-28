# kubeSol/engine/k8s_api.py
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubeSol.constants import ( # Updated import
    DEFAULT_NAMESPACE,
    SCRIPT_CM_PREFIX, # This prefix itself was updated in constants.py
    SCRIPT_CM_LABEL_ROLE, # This label was updated in constants.py
    SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT,
)
import json
import re
import traceback

try:
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
except config.ConfigException as e:
    print(f"🚨 Critical Error: Could not load Kubernetes configuration: {e}")
    print("   Please ensure your kubeconfig is correctly set up.")
    core_v1_api = None 
except Exception as e: 
    print(f"🚨 Critical Error: An unexpected error occurred while loading Kubernetes configuration: {e}")
    core_v1_api = None

def get_api_client() -> client.CoreV1Api: 
    """
    Retrieves the initialized Kubernetes CoreV1Api client.
    """
    global core_v1_api 
    if core_v1_api is None:
        try:
            print("DEBUG K8S_API: core_v1_api not found, attempting to load kube_config again...")
            config.load_kube_config()
            core_v1_api = client.CoreV1Api()
            print("DEBUG K8S_API: core_v1_api loaded successfully.")
        except Exception as e_conf: 
            print(f"🔥🔥🔥 CRITICAL ERROR in get_api_client while loading config: {e_conf}") 
            raise RuntimeError(f"Could not initialize Kubernetes API client in get_api_client: {e_conf}")
    
    if core_v1_api is None: 
         raise RuntimeError("core_v1_api is None even after the attempt of re-initialization.")
    return core_v1_api

def _print_api_exception_details(e: ApiException, context_message: str):
    """
    Prints detailed information from an ApiException.
    """
    base_error_message = f"❌ {context_message}: {e.reason} (Status: {e.status})"
    print(base_error_message)
    if e.body:
        try:
            error_body_json = json.loads(e.body)
            print(f"   K8S API Message: {error_body_json.get('message', 'N/A')}")
            if error_body_json.get('details') and error_body_json['details'].get('causes'):
                print("  Causes:")
                for cause in error_body_json['details']['causes']:
                    print(f"    - Field: {cause.get('field', 'N/A')}, Reason: {cause.get('reason', 'N/A')}, Message: {cause.get('message', 'N/A')}")
        except json.JSONDecodeError:
            print(f"  K8S API Error Body (not valid JSON or empty): {e.body[:500]}...") 
    else:
        print("  K8S API Error Body: No additional content from API.")


def _sanitize_for_k8s_name(input_name: str) -> str: 
    """
    Sanitizes a string to be a valid Kubernetes resource name.
    """
    original_name = input_name 
    processed_name = input_name.lower() 
    processed_name = re.sub(r'[^a-z0-9-]+', '-', processed_name) 
    processed_name = processed_name.strip('-') 

    max_len_name_part = 50 
    if len(processed_name) > max_len_name_part:
        processed_name = processed_name[:max_len_name_part]
    
    processed_name = processed_name.strip('-') 

    if not processed_name: 
        raise ValueError(f"Input name '{original_name}' results in an invalid/empty Kubernetes name ('{processed_name}') after sanitization.")
    return processed_name

# --- SECRETS ---
def create_secret(name: str, data: dict, namespace: str = DEFAULT_NAMESPACE): 
    api = get_api_client()
    metadata = client.V1ObjectMeta(name=name, namespace=namespace)
    secret_body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=metadata,
        string_data=data 
    )
    try:
        api.create_namespaced_secret(namespace=namespace, body=secret_body)
        print(f"✅ Secret '{name}' created successfully in namespace '{namespace}'.")
    except ApiException as e:
        _print_api_exception_details(e, f"Error creating Secret '{name}' in namespace '{namespace}'")

def delete_secret(name: str, namespace: str = DEFAULT_NAMESPACE): 
    api = get_api_client()
    try:
        api.delete_namespaced_secret(name=name, namespace=namespace)
        print(f"🗑️ Secret '{name}' deleted successfully from namespace '{namespace}'.")
    except ApiException as e:
        if e.status == 404: 
            print(f"🤷 Secret '{name}' not found in namespace '{namespace}'.")
        else:
            _print_api_exception_details(e, f"Error deleting Secret '{name}' in namespace '{namespace}'")

def update_secret(name: str, data: dict, namespace: str = DEFAULT_NAMESPACE): 
    api = get_api_client()
    metadata = client.V1ObjectMeta(name=name, namespace=namespace)
    secret_body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=metadata,
        string_data=data
    )
    try:
        api.replace_namespaced_secret(name=name, namespace=namespace, body=secret_body)
        print(f"🔄 Secret '{name}' updated successfully in namespace '{namespace}'.")
    except ApiException as e:
        if e.status == 404: 
            print(f"❌ Cannot update Secret '{name}': Not found in namespace '{namespace}'. Consider creating it first.")
        else:
            _print_api_exception_details(e, f"Error updating Secret '{name}' in namespace '{namespace}'")

# --- PARAMETERS (implemented as Secrets) ---
def create_parameter(name: str, script_content: str, namespace: str = DEFAULT_NAMESPACE): 
    create_secret(name=name, data={"script": script_content}, namespace=namespace)

def update_parameter(name: str, script_content: str, namespace: str = DEFAULT_NAMESPACE): 
    update_secret(name=name, data={"script": script_content}, namespace=namespace)

# --- CONFIGMAPS ---
def create_configmap(name: str, data: dict, namespace: str = DEFAULT_NAMESPACE): 
    api = get_api_client()
    metadata = client.V1ObjectMeta(name=name, namespace=namespace)
    configmap_body = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=metadata,
        data=data
    )
    try:
        api.create_namespaced_config_map(namespace=namespace, body=configmap_body)
        print(f"✅ ConfigMap '{name}' created successfully in namespace '{namespace}'.")
    except ApiException as e:
        _print_api_exception_details(e, f"Error creating ConfigMap '{name}' in namespace '{namespace}'")

def delete_configmap(name: str, namespace: str = DEFAULT_NAMESPACE): 
    api = get_api_client()
    try:
        api.delete_namespaced_config_map(name=name, namespace=namespace)
        print(f"🗑️ ConfigMap '{name}' deleted successfully from namespace '{namespace}'.")
    except ApiException as e:
        if e.status == 404: 
            print(f"🤷 ConfigMap '{name}' not found in namespace '{namespace}'.")
        else:
            _print_api_exception_details(e, f"Error deleting ConfigMap '{name}' in namespace '{namespace}'")

def update_configmap(name: str, data: dict, namespace: str = DEFAULT_NAMESPACE): 
    api = get_api_client()
    metadata = client.V1ObjectMeta(name=name, namespace=namespace)
    configmap_body = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=metadata,
        data=data
    )
    try:
        api.replace_namespaced_config_map(name=name, namespace=namespace, body=configmap_body)
        print(f"🔄 ConfigMap '{name}' updated successfully in namespace '{namespace}'.")
    except ApiException as e:
        if e.status == 404: 
            print(f"❌ Cannot update ConfigMap '{name}': Not found in namespace '{namespace}'. Consider creating it first.")
        else:
            _print_api_exception_details(e, f"Error updating ConfigMap '{name}' in namespace '{namespace}'")

# --- SCRIPT CONFIGMAPS ---
def get_script_cm_name(script_name: str) -> str: 
    """Generates the Kubernetes ConfigMap name for a given script name."""
    sanitized_script_name = _sanitize_for_k8s_name(script_name)
    return f"{SCRIPT_CM_PREFIX}{sanitized_script_name}" # SCRIPT_CM_PREFIX was updated in constants

def get_script_configmap_data(script_name: str, namespace: str = DEFAULT_NAMESPACE) -> dict | None: 
    """Retrieves the data section of a script's ConfigMap."""
    api = get_api_client()
    cm_name = get_script_cm_name(script_name) 
    try:
        configmap_resource = api.read_namespaced_config_map(name=cm_name, namespace=namespace) 
        data_to_return = configmap_resource.data
        if data_to_return is None: 
            data_to_return = {}
        return data_to_return
    except ApiException as e:
        if e.status == 404: 
            print(f"🤷 Script '{script_name}' (ConfigMap '{cm_name}') not found in namespace '{namespace}'.")
        else:
            _print_api_exception_details(e, f"Error getting script '{script_name}' (ConfigMap '{cm_name}')")
        return None

def create_script_configmap(script_name: str, script_details: dict, namespace: str = DEFAULT_NAMESPACE):
    """Creates a ConfigMap to store a script's details."""
    print(f"[DEBUG K8S_API] >>> Entering create_script_configmap for script: '{script_name}'")
    
    try:
        api = get_api_client() 
        cm_name = get_script_cm_name(script_name)
        
        print(f"[DEBUG K8S_API] Attempting to create ConfigMap: '{cm_name}' in namespace '{namespace}'. Data keys for CM: {list(script_details.keys())}")

        # Note: SCRIPT_CM_LABEL_ROLE was updated in constants.py
        metadata = client.V1ObjectMeta(
            name=cm_name,
            namespace=namespace,
            labels={
                SCRIPT_CM_LABEL_ROLE: SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT,
                "kubesol-script-name": _sanitize_for_k8s_name(script_name) # Changed label key
            }
        )
        string_data = {k: str(v) for k, v in script_details.items() if v is not None}

        configmap_body = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=metadata,
            data=string_data
        )
        
        api.create_namespaced_config_map(namespace=namespace, body=configmap_body)
        print(f"✅ Script '{script_name}' (as ConfigMap '{cm_name}') created in namespace '{namespace}'.")

    except ApiException as e:
        if e.status == 409: 
            print(f"❌ Error creating script '{script_name}': ConfigMap '{cm_name}' already exists. Use UPDATE or delete it first.")
        else:
            _print_api_exception_details(e, f"API Error creating script '{script_name}' (ConfigMap '{cm_name}')")
    except Exception as general_exception: 
        cm_name_for_error_msg = locals().get('cm_name', 'UNKNOWN (not determined before error)')
        print(f"🔥🔥🔥 UNEXPECTED ERROR in create_script_configmap for script '{script_name}' (attempting CM '{cm_name_for_error_msg}'): {type(general_exception).__name__} - {general_exception}")
        print("--- Unexpected Error Traceback ---")
        traceback.print_exc() 
        print("--- End of Traceback ---")
    print(f"[DEBUG K8S_API] <<< Exiting create_script_configmap for script: '{script_name}'")


def list_script_configmaps_data(namespace: str = DEFAULT_NAMESPACE) -> list[dict]: 
    """Lists all script ConfigMaps in a namespace and returns their data sections."""
    api = get_api_client()
    scripts_data_list = [] 
    # Note: SCRIPT_CM_LABEL_ROLE was updated in constants.py
    label_selector = f"{SCRIPT_CM_LABEL_ROLE}={SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT}"
    try:
        configmaps_response = api.list_namespaced_config_map(namespace=namespace, label_selector=label_selector) 
        for cm_item in configmaps_response.items: 
            if cm_item.data: 
                script_info = cm_item.data.copy() 
                script_info['_script_name_from_cm'] = cm_item.metadata.name.replace(SCRIPT_CM_PREFIX, "", 1) 
                script_info['_cm_name'] = cm_item.metadata.name 
                scripts_data_list.append(script_info)
            else: 
                 print(f"⚠️ ConfigMap '{cm_item.metadata.name}' with script label has no 'data' section. Skipping.")
        return scripts_data_list
    except ApiException as e:
        _print_api_exception_details(e, f"Error listing scripts in namespace '{namespace}'")
        return []

def delete_script_configmap(script_name: str, namespace: str = DEFAULT_NAMESPACE): 
    """Deletes a script's ConfigMap."""
    api = get_api_client()
    cm_name = get_script_cm_name(script_name)
    try:
        api.delete_namespaced_config_map(name=cm_name, namespace=namespace)
        print(f"🗑️ Script '{script_name}' (ConfigMap '{cm_name}') deleted from namespace '{namespace}'.")
    except ApiException as e:
        if e.status == 404: 
            print(f"🤷 Script '{script_name}' (ConfigMap '{cm_name}') not found for deletion in namespace '{namespace}'.")
        else:
            _print_api_exception_details(e, f"Error deleting script '{script_name}' (ConfigMap '{cm_name}')")

def update_script_configmap(script_name: str, updates: dict, namespace: str = DEFAULT_NAMESPACE) -> bool:
    """
    Updates a script's ConfigMap with new data.
    """
    api = get_api_client()
    cm_name = get_script_cm_name(script_name) 

    try:
        current_cm = api.read_namespaced_config_map(name=cm_name, namespace=namespace)
        
        if current_cm.data is None: 
            current_cm.data = {}

        for key, value in updates.items():
            if value is not None: 
                current_cm.data[key] = str(value)
            elif key in current_cm.data: 
                del current_cm.data[key]
        
        api.replace_namespaced_config_map(name=cm_name, namespace=namespace, body=current_cm)
        print(f"🔄 Script '{script_name}' (ConfigMap '{cm_name}') updated in namespace '{namespace}'.")
        return True

    except ApiException as e:
        if e.status == 404: 
            print(f"🤷 Script '{script_name}' (ConfigMap '{cm_name}') not found for update in namespace '{namespace}'.")
        else:
            _print_api_exception_details(e, f"Error updating script '{script_name}' (ConfigMap '{cm_name}')")
        return False

# --- KUBERNETES JOBS ---
def create_k8s_job(job_name: str, namespace: str, image: str,
                  script_configmap_name: str, 
                  script_file_key_in_cm: str, 
                  script_mount_path: str,     
                  container_command: list[str] | None = None, 
                  container_args: list[str] | None = None,    
                  env_vars: list[client.V1EnvVar] | None = None, 
                  restart_policy: str = "Never"
                  ) -> bool:
    """
    Creates a Kubernetes Job to execute a script.
    """
    core_api = get_api_client() 
    batch_v1_api = client.BatchV1Api(core_api.api_client) 

    volume_name = "script-volume" 
    configmap_volume = client.V1Volume(
        name=volume_name,
        config_map=client.V1ConfigMapVolumeSource(
            name=script_configmap_name 
        )
    )

    volume_mount = client.V1VolumeMount(
        name=volume_name, 
        mount_path=script_mount_path, 
    )
    
    container_spec = client.V1Container( # Renamed
        name=f"{job_name}-container", 
        image=image,
        command=container_command, 
        args=container_args,
        env=env_vars,
        volume_mounts=[volume_mount] 
    )

    pod_template_spec = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": job_name, "kubesol-job": "true"}), # Changed label
        spec=client.V1PodSpec(
            restart_policy=restart_policy, 
            containers=[container_spec],        
            volumes=[configmap_volume]     
        )
    )

    job_spec = client.V1JobSpec(
        template=pod_template_spec, 
        backoff_limit=4             
    )

    job_object = client.V1Job( 
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_name, namespace=namespace),
        spec=job_spec
    )

    try:
        batch_v1_api.create_namespaced_job(body=job_object, namespace=namespace)
        print(f"✅ Job '{job_name}' created in namespace '{namespace}'.")
        return True
    except ApiException as e:
        _print_api_exception_details(e, f"Error creating Job '{job_name}'")
        return False


def get_k8s_job_status(job_name: str, namespace: str = DEFAULT_NAMESPACE) -> dict | None:
    """Retrieves the status of a Kubernetes Job."""
    core_api = get_api_client()
    batch_v1_api = client.BatchV1Api(core_api.api_client)
    try:
        job_status_obj = batch_v1_api.read_namespaced_job_status(name=job_name, namespace=namespace) 
        status = job_status_obj.status 
        return {
            "active": status.active,
            "succeeded": status.succeeded,
            "failed": status.failed,
            "startTime": status.start_time.isoformat() if status.start_time else None,
            "completionTime": status.completion_time.isoformat() if status.completion_time else None,
            "conditions": [{"type": c.type, "status": c.status, 
                            "lastTransitionTime":c.last_transition_time.isoformat()} 
                           for c in status.conditions] if status.conditions else []
        }
    except ApiException as e:
        if e.status == 404: 
            print(f"🤷 Job '{job_name}' not found in namespace '{namespace}'.")
        else:
            _print_api_exception_details(e, f"Error getting status of Job '{job_name}'")
        return None

def get_k8s_job_logs(job_name: str, namespace: str = DEFAULT_NAMESPACE, tail_lines: int = 20) -> str | None:
    """Retrieves logs from the first pod of a Kubernetes Job."""
    core_api = get_api_client() 
    try:
        pod_list = core_api.list_namespaced_pod( 
            namespace=namespace,
            label_selector=f"job-name={job_name}" 
        )
        if not pod_list.items:
            print(f"🤷 No pods found for Job '{job_name}'.")
            return None

        pod_to_log_from = pod_list.items[0] 
        pod_name = pod_to_log_from.metadata.name 
        
        if not pod_to_log_from.spec.containers:
            print(f"🤷 Pod '{pod_name}' has no defined containers.")
            return None
        container_name_in_pod = pod_to_log_from.spec.containers[0].name 

        print(f"🪵 Fetching logs for pod '{pod_name}', container '{container_name_in_pod}' of Job '{job_name}'...")
        log_string = core_api.read_namespaced_pod_log( 
            name=pod_name,
            namespace=namespace,
            container=container_name_in_pod,
            tail_lines=tail_lines,
            timestamps=True 
        )
        return log_string
    except ApiException as e:
        _print_api_exception_details(e, f"Error getting logs for Job '{job_name}'")
        return None