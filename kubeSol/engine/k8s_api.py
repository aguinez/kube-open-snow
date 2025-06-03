from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubeSol.constants import ( #
    DEFAULT_NAMESPACE,
    SCRIPT_CM_PREFIX, 
    SCRIPT_CM_LABEL_ROLE, 
    SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT,
    # Add new project/env label constants if k8s_api needs to be aware of them directly,
    # though typically manager.py would construct label_selectors.
)
import json
import re
import traceback
import base64 
import os

try:
    config.load_kube_config()
    core_v1_api = client.CoreV1Api() # Used for most namespaced resources and namespaces themselves
except config.ConfigException as e:
    print(f"🚨 Critical Error: Could not load Kubernetes configuration: {e}\n   Please ensure your kubeconfig is correctly set up.")
    core_v1_api = None 
except Exception as e: 
    print(f"🚨 Critical Error: An unexpected error occurred while loading Kubernetes configuration: {e}")
    core_v1_api = None

def get_api_client() -> client.CoreV1Api: 
    """Retrieves the initialized Kubernetes CoreV1Api client."""
    global core_v1_api 
    if core_v1_api is None:
        try:
            print("DEBUG K8S_API: core_v1_api was None, attempting to load kube_config again...")
            config.load_kube_config()
            core_v1_api = client.CoreV1Api()
            print("DEBUG K8S_API: core_v1_api re-loaded successfully.")
        except Exception as e_conf: 
            raise RuntimeError(f"Could not initialize Kubernetes API client in get_api_client: {e_conf}")
    if core_v1_api is None: 
         raise RuntimeError("core_v1_api is None even after re-initialization attempt.")
    return core_v1_api

def _print_api_exception_details(e: ApiException, context_message: str):
    """Prints detailed information from an ApiException."""
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
    """Sanitizes a string to be a valid Kubernetes resource name."""
    original_name = input_name 
    processed_name = input_name.lower() 
    processed_name = re.sub(r'[^a-z0-9-]+', '-', processed_name) 
    processed_name = processed_name.strip('-') 
    max_len_name_part = 50 # Conservative max length for parts of names we construct
    if len(processed_name) > max_len_name_part:
        processed_name = processed_name[:max_len_name_part]
    processed_name = processed_name.strip('-') 
    if not processed_name: 
        raise ValueError(f"Input name '{original_name}' results in an invalid/empty Kubernetes name ('{processed_name}') after sanitization.")
    return processed_name


# --- SECRETS ---
def create_secret(name: str, data: dict, namespace: str = DEFAULT_NAMESPACE):
    """
    Original function to create a Kubernetes Secret with string data.
    'data' is a dictionary where all values are plain strings.
    """
    api = get_api_client()
    metadata = client.V1ObjectMeta(name=name, namespace=namespace)
    secret_body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=metadata,
        string_data=data  # Assumes 'data' is purely for stringData
    )
    try:
        api.create_namespaced_secret(namespace=namespace, body=secret_body)
        print(f"✅ Secret '{name}' (string data only) created successfully in namespace '{namespace}'.")
    except ApiException as e:
        _print_api_exception_details(e, f"Error creating Secret '{name}' in namespace '{namespace}'")

def create_secret_with_mixed_data(name: str, 
                                  string_data_payload: dict | None, 
                                  b64_data_payload: dict | None, 
                                  namespace: str = DEFAULT_NAMESPACE):
    """
    Creates a Kubernetes Secret, supporting both plain string data and base64 encoded data (e.g., from files).
    """
    api = get_api_client()
    metadata = client.V1ObjectMeta(name=name, namespace=namespace)
    
    secret_body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=metadata,
        string_data=string_data_payload if string_data_payload else None,
        data=b64_data_payload if b64_data_payload else None # For base64 encoded content
    )
    try:
        api.create_namespaced_secret(namespace=namespace, body=secret_body)
        print(f"✅ Secret '{name}' created successfully in namespace '{namespace}'.")
        if string_data_payload:
            print(f"   Includes string data keys: {list(string_data_payload.keys())}")
        if b64_data_payload:
            print(f"   Includes file-based/encoded data keys: {list(b64_data_payload.keys())}")
    except ApiException as e:
        _print_api_exception_details(e, f"Error creating Secret '{name}' with mixed data in namespace '{namespace}'")


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
                  script_file_key_in_cm: str, # e.g., "code"
                  script_mount_path: str,     # e.g., "/kubesol_scripts"
                  container_command: list[str] | None = None, 
                  container_args: list[str] | None = None,    
                  env_vars: list[client.V1EnvVar] | None = None, 
                  restart_policy: str = "Never",
                  secret_volume_mount_configs: list[dict] | None = None # NEW parameter
                  ) -> bool:
    """Creates a Kubernetes Job to execute a script, with support for secret mounts."""
    core_api = get_api_client() 
    batch_v1_api = client.BatchV1Api(core_api.api_client) 

    # --- Define Volumes & Volume Mounts ---
    all_volumes = []
    all_container_volume_mounts = []

    # 1. For the script ConfigMap
    script_volume_name = f"script-vol-{_sanitize_for_k8s_name(script_configmap_name)}"[:63] # Ensure valid name
    # Mount the entire ConfigMap to the script_mount_path directory.
    # The script will be available as a file named after its key (script_file_key_in_cm) within this directory.
    script_volume_obj = client.V1Volume( # Renamed var
        name=script_volume_name,
        config_map=client.V1ConfigMapVolumeSource(
            name=script_configmap_name 
            # To mount only specific keys as files with those key names:
            # items=[client.V1KeyToPath(key=script_file_key_in_cm, path=script_file_key_in_cm)]
            # If script_mount_path is a dir, and script is script_mount_path/script_file_key_in_cm,
            # then mounting the whole CM to script_mount_path is fine.
        )
    )
    all_volumes.append(script_volume_obj)

    script_volume_mount_obj = client.V1VolumeMount( # Renamed var
        name=script_volume_name,
        mount_path=script_mount_path, # e.g., "/kubesol_scripts"
    )
    all_container_volume_mounts.append(script_volume_mount_obj)
    
    # 2. For additional Secret Mounts (NEW logic)
    if secret_volume_mount_configs:
        for i, mount_config in enumerate(secret_volume_mount_configs):
            user_secret_name = mount_config["secret_name"]
            key_from_secret = mount_config["key_in_secret"]
            target_path_in_pod = mount_config["mount_path_in_pod"] # This is the full path to the target file

            # Derive volume name, mount directory, and filename for subPath
            # Example: target_path_in_pod = "/mnt/secrets/gcp/key.json"
            #   volume_mount_dir = "/mnt/secrets/gcp"
            #   filename_in_mount_dir = "key.json"
            volume_mount_dir = os.path.dirname(target_path_in_pod)
            filename_in_mount_dir = os.path.basename(target_path_in_pod)

            # Create a unique volume name for this secret mount
            # Sanitize user_secret_name for use in volume_name
            sanitized_secret_name_part = _sanitize_for_k8s_name(user_secret_name)
            secret_volume_name = f"secret-{sanitized_secret_name_part}-{i}"[:63] # Ensure valid and unique enough

            secret_volume_obj = client.V1Volume( # Renamed var
                name=secret_volume_name,
                secret=client.V1SecretVolumeSource(
                    secret_name=user_secret_name,
                    items=[client.V1KeyToPath(key=key_from_secret, path=filename_in_mount_dir)]
                    # This projects the specific 'key_from_secret' to a file named 'filename_in_mount_dir'
                    # within the directory specified by the volumeMount's mountPath.
                )
            )
            all_volumes.append(secret_volume_obj)

            container_secret_mount = client.V1VolumeMount( # Renamed var
                name=secret_volume_name, # Must match the V1Volume name
                mount_path=volume_mount_dir, # Mount the directory containing the projected file
                read_only=True # Secrets are typically mounted read-only
            )
            all_container_volume_mounts.append(container_secret_mount)

    # Define the Container
    container_spec = client.V1Container(
        name=f"{job_name}-container",
        image=image,
        command=container_command,
        args=container_args,
        env=env_vars if env_vars else [], 
        volume_mounts=all_container_volume_mounts 
    )

    # Define Pod Template Spec
    pod_template_spec = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": job_name, "kubesol-job": "true"}),
        spec=client.V1PodSpec(
            restart_policy=restart_policy,
            containers=[container_spec],
            volumes=all_volumes 
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
        if secret_volume_mount_configs:
            print(f"   Job includes {len(secret_volume_mount_configs)} mounted secret(s).")
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
    
# PROJECT MANAGEMENT FUNCTIONS

def create_k8s_namespace(name: str, labels: dict = None) -> bool:
    """
    Creates a Kubernetes namespace.
    Args:
        name: The name of the namespace to create.
        labels: A dictionary of labels to apply to the namespace.
    Returns:
        True if creation was successful or namespace already exists with same labels, False otherwise.
    """
    api = get_api_client() # CoreV1Api
    namespace_body = client.V1Namespace(
        api_version="v1",
        kind="Namespace",
        metadata=client.V1ObjectMeta(name=name, labels=labels if labels else {})
    )
    try:
        api.create_namespace(body=namespace_body)
        print(f"✅ Namespace '{name}' created successfully with labels: {labels or {}}.")
        return True
    except ApiException as e:
        if e.status == 409: # Conflict - Namespace already exists
            print(f"ℹ️ Namespace '{name}' already exists.")
            # Optionally, check if labels match and update if necessary, or just return True.
            # For simplicity now, if it exists, we consider it a "success" for this operation's intent.
            # To be more robust, you might want to get the existing namespace and compare/patch labels.
            # For now, let's try to patch labels if it already exists, to ensure they are set.
            if labels:
                print(f"   Attempting to ensure labels {labels} are set on existing namespace '{name}'...")
                return update_k8s_namespace_labels(name, labels)
            return True
        _print_api_exception_details(e, f"Error creating namespace '{name}'")
        return False
    except Exception as ex_general:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in create_k8s_namespace for '{name}': {type(ex_general).__name__} - {ex_general}")
        import traceback
        traceback.print_exc()
        return False


def get_k8s_namespace(name: str) -> client.V1Namespace | None:
    """
    Retrieves a specific Kubernetes namespace.
    Args:
        name: The name of the namespace.
    Returns:
        The V1Namespace object if found, otherwise None.
    """
    api = get_api_client()
    try:
        namespace_obj = api.read_namespace(name=name)
        return namespace_obj
    except ApiException as e:
        if e.status == 404: # Not Found
            # This is an expected case if checking for existence, so no error print here.
            # The caller can handle the None return.
            pass
        else:
            _print_api_exception_details(e, f"Error retrieving namespace '{name}'")
        return None
    except Exception as ex_general:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in get_k8s_namespace for '{name}': {type(ex_general).__name__} - {ex_general}")
        import traceback
        traceback.print_exc()
        return None

def list_k8s_namespaces(label_selector: str = None) -> list[client.V1Namespace]:
    """
    Lists Kubernetes namespaces, optionally filtering by label_selector.
    Args:
        label_selector: A label selector string (e.g., "kubesol.io/project=myproj").
    Returns:
        A list of V1Namespace objects.
    """
    api = get_api_client()
    try:
        if label_selector:
            namespace_list = api.list_namespace(label_selector=label_selector)
        else:
            namespace_list = api.list_namespace()
        return namespace_list.items
    except ApiException as e:
        _print_api_exception_details(e, f"Error listing namespaces (selector: '{label_selector}')")
        return []
    except Exception as ex_general:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in list_k8s_namespaces (selector: '{label_selector}'): {type(ex_general).__name__} - {ex_general}")
        import traceback
        traceback.print_exc()
        return []

def delete_k8s_namespace(name: str) -> bool:
    """
    Deletes a Kubernetes namespace.
    Args:
        name: The name of the namespace to delete.
    Returns:
        True if deletion was successful or namespace was already gone, False otherwise.
    """
    api = get_api_client()
    try:
        api.delete_namespace(name=name, body=client.V1DeleteOptions())
        print(f"🗑️ Namespace '{name}' deletion initiated successfully.")
        # Note: Namespace deletion is asynchronous. This call returns quickly.
        # We might want to add a wait loop here if synchronous behavior is needed,
        # but that can be complex due to finalizers. For now, initiating is enough.
        return True
    except ApiException as e:
        if e.status == 404: # Not Found
            print(f"🤷 Namespace '{name}' not found for deletion (perhaps already deleted).")
            return True # Consider it a success if it's already gone
        _print_api_exception_details(e, f"Error deleting namespace '{name}'")
        return False
    except Exception as ex_general:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in delete_k8s_namespace for '{name}': {type(ex_general).__name__} - {ex_general}")
        import traceback
        traceback.print_exc()
        return False


def update_k8s_namespace_labels(namespace_name: str, labels_to_set: dict) -> bool:
    """
    Updates (adds or modifies) labels on a given namespace.
    This uses patch to avoid overwriting other existing labels.
    Args:
        namespace_name: The name of the namespace to update.
        labels_to_set: A dictionary of labels to set/update.
    Returns:
        True if successful, False otherwise.
    """
    api = get_api_client()
    try:
        # To add/update labels without removing existing ones, we patch.
        # The body of the patch should be a V1Namespace object with just the metadata.labels field set.
        patch_body = {
            "metadata": {
                "labels": labels_to_set
            }
        }
        # Using strategic merge patch. For labels, this should add/overwrite.
        api.patch_namespace(name=namespace_name, body=patch_body)
        print(f"✅ Labels {labels_to_set} successfully patched onto namespace '{namespace_name}'.")
        return True
    except ApiException as e:
        if e.status == 404:
            print(f"🤷 Namespace '{namespace_name}' not found for label update.")
        else:
            _print_api_exception_details(e, f"Error updating labels for namespace '{namespace_name}'")
        return False
    except Exception as ex_general:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in update_k8s_namespace_labels for '{namespace_name}': {type(ex_general).__name__} - {ex_general}")
        import traceback
        traceback.print_exc()
        return False
