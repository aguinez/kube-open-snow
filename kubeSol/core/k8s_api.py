# kubesol/core/k8s_api.py (Contenido original de kubeSol/engine/k8s_api.py, con import de constants actualizado)
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubesol.constants import ( # Actualizado a 'kubesol.constants'
    DEFAULT_NAMESPACE,
    SCRIPT_CM_PREFIX, 
    SCRIPT_CM_LABEL_ROLE, 
    SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT,
)
import json
import re
import traceback
import base64 
import os

try:
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
except config.ConfigException as e:
    print(f"🚨 Critical Error: Could not load Kubernetes configuration: {e}\n   Please ensure your kubeconfig is correctly set up.")
    core_v1_api = None 
except Exception as e: 
    print(f"🚨 Critical Error: An unexpected error occurred while loading Kubernetes configuration: {e}")
    core_v1_api = None

def get_api_client() -> client.CoreV1Api:
    global core_v1_api
    if core_v1_api is None:
        try:
            config.load_kube_config()
            core_v1_api = client.CoreV1Api()
        except Exception as e_conf:
            raise RuntimeError(f"Could not initialize Kubernetes API client in get_api_client: {e_conf}")
    if core_v1_api is None:
         raise RuntimeError("core_v1_api is None even after re-initialization attempt.")
    return core_v1_api

def _print_api_exception_details(e: ApiException, context_message: str):
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
    original_name = input_name 
    processed_name = input_name.lower() 
    processed_name = re.sub(r'[^a-z0-9-]+', '-', processed_name) 
    processed_name = processed_name.strip('-') 
    if not processed_name: 
        raise ValueError(f"Input name '{original_name}' results in an invalid K8s name ('{processed_name}') after sanitization.")
    return processed_name[:63]


# --- SECRETS ---
def get_secret_data(name: str, namespace: str = DEFAULT_NAMESPACE) -> dict | None:
    """
    Retrieves the data from a Kubernetes Secret.
    The data values are base64 decoded.
    """
    api = get_api_client()
    try:
        secret = api.read_namespaced_secret(name=name, namespace=namespace)
        if secret.data:
            decoded_data = {
                key: base64.b64decode(value).decode('utf-8')
                for key, value in secret.data.items()
            }
            return decoded_data
        return {}
    except ApiException as e:
        if e.status == 404:
            print(f"🤷 Secret '{name}' not found in namespace '{namespace}'.")
        else:
            _print_api_exception_details(e, f"Error getting Secret '{name}' in namespace '{namespace}'")
        return None
    except Exception as e:
        print(f"❌ Unexpected error getting Secret '{name}': {type(e).__name__} - {e}")
        traceback.print_exc()
        return None

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
        string_data=data
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
        data=b64_data_payload if b64_data_payload else None
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
    return f"{SCRIPT_CM_PREFIX}{sanitized_script_name}"

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

        metadata = client.V1ObjectMeta(
            name=cm_name,
            namespace=namespace,
            labels={
                SCRIPT_CM_LABEL_ROLE: SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT,
                "kubesol-script-name": _sanitize_for_k8s_name(script_name)
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
    except Exception as ex_general:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in list_script_configmaps_data (namespace: '{namespace}'): {type(ex_general).__name__} - {ex_general}")
        import traceback
        traceback.print_exc()
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
                  pod_restart_policy: str = "Never", 
                  secret_volume_mount_configs: list[dict] | None = None,
                  job_backoff_limit: int = 0,
                  job_active_deadline_seconds: int | None = 300
                  ) -> bool:
    """
    Creates a Kubernetes Job with PodFailurePolicy and controlled retries.
    """
    core_api = get_api_client() 
    batch_v1_api = client.BatchV1Api(core_api.api_client) 

    all_volumes = []
    all_container_volume_mounts = []

    # 1. Volumen para el ConfigMap del script
    script_volume_name = f"script-vol-{_sanitize_for_k8s_name(script_configmap_name)}"[:63]
    script_volume_obj = client.V1Volume(
        name=script_volume_name,
        config_map=client.V1ConfigMapVolumeSource(name=script_configmap_name)
    )
    all_volumes.append(script_volume_obj)
    script_volume_mount_obj = client.V1VolumeMount(name=script_volume_name, mount_path=script_mount_path)
    all_container_volume_mounts.append(script_volume_mount_obj)

    # 2. Volúmenes para Secretos adicionales
    if secret_volume_mount_configs:
        for i, mount_config in enumerate(secret_volume_mount_configs):
            user_secret_name = mount_config["secret_name"]
            key_from_secret = mount_config["key_in_secret"]
            target_path_in_pod = mount_config["mount_path_in_pod"]
            volume_mount_dir = os.path.dirname(target_path_in_pod)
            filename_in_mount_dir = os.path.basename(target_path_in_pod)
            sanitized_secret_name_part = _sanitize_for_k8s_name(user_secret_name)
            secret_volume_name = f"secret-{sanitized_secret_name_part}-{i}"[:63]

            secret_volume_obj = client.V1Volume(
                name=secret_volume_name,
                secret=client.V1SecretVolumeSource(
                    secret_name=user_secret_name,
                    items=[client.V1KeyToPath(key=key_from_secret, path=filename_in_mount_dir)]))
            all_volumes.append(secret_volume_obj)
            container_secret_mount = client.V1VolumeMount(name=secret_volume_name, mount_path=volume_mount_dir, read_only=True)
            all_container_volume_mounts.append(container_secret_mount)

    main_container_name = f"{job_name}-container"

    container_spec = client.V1Container(
        name=main_container_name, 
        image=image,
        args=container_args,
        env=env_vars if env_vars else [], 
        volume_mounts=all_container_volume_mounts 
    )

    pod_template_spec = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": job_name, "kubesol-job": "true"}),
        spec=client.V1PodSpec(
            restart_policy=pod_restart_policy, 
            containers=[container_spec],
            volumes=all_volumes 
        )
    )

    on_exit_codes_rule = client.V1PodFailurePolicyRule(
        action="FailJob", 
        on_exit_codes=client.V1PodFailurePolicyOnExitCodesRequirement(
            container_name=main_container_name,
            operator="In",      
            values=[
                1, 126, 127, 137
            ]
        )
    )

    pod_failure_policy_config = client.V1PodFailurePolicy(rules=[on_exit_codes_rule])

    job_spec = client.V1JobSpec(
        template=pod_template_spec,
        backoff_limit=job_backoff_limit, 
        active_deadline_seconds=job_active_deadline_seconds,
        pod_failure_policy=pod_failure_policy_config
    )

    job_object = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_name, namespace=namespace),
        spec=job_spec
    )

    try:
        print(f"DEBUG K8S_API: Creating Job '{job_name}' with effective settings:")
        print(f"  spec.backoffLimit: {job_object.spec.backoff_limit}")
        print(f"  spec.activeDeadlineSeconds: {job_object.spec.active_deadline_seconds}")
        print(f"  spec.template.spec.restartPolicy: {job_object.spec.template.spec.restart_policy}")
        if job_object.spec.pod_failure_policy and job_object.spec.pod_failure_policy.rules:
            print(f"  spec.podFailurePolicy.rules[0].action: {job_object.spec.pod_failure_policy.rules[0].action}")
            if job_object.spec.pod_failure_policy.rules[0].on_exit_codes:
                print(f"  spec.podFailurePolicy.rules[0].onExitCodes.containerName: {job_object.spec.pod_failure_policy.rules[0].on_exit_codes.container_name}")
        else:
            print(f"  spec.podFailurePolicy: Not set or no rules.")

        current_batch_v1_api = client.BatchV1Api(get_api_client().api_client)
        current_batch_v1_api.create_namespaced_job(body=job_object, namespace=namespace)

        print(f"✅ Job '{job_name}' created in namespace '{namespace}'.")
        return True
    except ApiException as e:
        _print_api_exception_details(e, f"Error creating Job '{job_name}'")
        return False
    except Exception as general_error: 
        print(f"🔥🔥🔥 UNEXPECTED ERROR in create_k8s_job for '{job_name}': {type(general_error).__name__} - {general_error}")
        traceback.print_exc()
        return False


def get_k8s_job_status(job_name: str, namespace: str = DEFAULT_NAMESPACE) -> dict | None:
    """
    Retrieves the status of a Kubernetes Job.
    """
    api_client_instance = get_api_client() 
    batch_v1_api = client.BatchV1Api(api_client_instance.api_client) 

    try:
        job_status_obj = batch_v1_api.read_namespaced_job_status(name=job_name, namespace=namespace)

        if not job_status_obj or not job_status_obj.status:
            print(f"DEBUG K8S_API: Job '{job_name}' found but has no status block or status is None.")
            return None 

        status = job_status_obj.status 

        status_dict = {
            "active": status.active,
            "succeeded": status.succeeded,
            "failed": status.failed,
            "startTime": status.start_time.isoformat() if status.start_time else None,
            "completionTime": status.completion_time.isoformat() if status.completion_time else None,
            "conditions": []
        }
        if status.conditions:
            status_dict["conditions"] = [
                {"type": c.type, "status": c.status, 
                 "lastTransitionTime": c.last_transition_time.isoformat() if c.last_transition_time else None,
                 "message": c.message} 
                for c in status.conditions
            ]
        return status_dict

    except ApiException as e:
        if e.status == 404: 
            print(f"🤷 Job '{job_name}' not found in namespace '{namespace}' when trying to get status.")
        else:
            _print_api_exception_details(e, f"Error getting status of Job '{job_name}'")
        return None
    except Exception as general_error:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in get_k8s_job_status for '{job_name}': {type(general_error).__name__} - {general_error}")
        import traceback
        traceback.print_exc()
        return None

def get_k8s_job_logs(job_name: str, namespace: str = DEFAULT_NAMESPACE, tail_lines: int = 100) -> str | None:
    """Retrieves logs from the pod(s) of a Kubernetes Job."""
    core_api = get_api_client()
    try:
        pod_list = core_api.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"job-name={job_name}"
        )
        if not pod_list.items:
            print(f"🤷 No pods found for Job '{job_name}' to retrieve logs.")
            return None

        pod_to_log_from = pod_list.items[-1]
        pod_name = pod_to_log_from.metadata.name

        if not pod_to_log_from.spec.containers:
            print(f"🤷 Pod '{pod_name}' for job '{job_name}' has no defined containers.")
            return None

        container_name_in_pod = pod_to_log_from.spec.containers[0].name
        if pod_to_log_from.status.phase == "Pending" or \
           any(cs.state and cs.state.waiting and cs.state.waiting.reason == "ContainerCreating" 
               for cs in pod_to_log_from.status.container_statuses or []):
            print(f"ℹ️ Container '{container_name_in_pod}' in pod '{pod_name}' is still creating or pending. Logs might not be available yet.")

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
    except Exception as general_error:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in get_k8s_job_logs for '{job_name}': {type(general_error).__name__} - {general_error}")
        import traceback
        traceback.print_exc()
        return None


# PROJECT MANAGEMENT FUNCTIONS

def create_k8s_namespace(name: str, labels: dict = None, annotations: dict = None) -> bool:
    """
    Creates a Kubernetes namespace.
    """
    api = get_api_client()
    namespace_body = client.V1Namespace(
        api_version="v1",
        kind="Namespace",
        metadata=client.V1ObjectMeta(name=name, labels=labels if labels else {}, annotations=annotations if annotations else {})
    )
    try:
        api.create_namespace(body=namespace_body)
        print(f"✅ Namespace '{name}' created successfully with labels: {labels or {}} and annotations: {annotations or {}}.")
        return True
    except ApiException as e:
        if e.status == 409:
            print(f"ℹ️ Namespace '{name}' already exists.")
            print(f"   Attempting to ensure labels {labels} and annotations {annotations} are set on existing namespace '{name}'...")
            return patch_k8s_namespace_metadata(name, labels=labels, annotations=annotations)

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
    """
    api = get_api_client()
    try:
        namespace_obj = api.read_namespace(name=name)
        return namespace_obj
    except ApiException as e:
        if e.status == 404:
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
    """
    api = get_api_client()
    try:
        api.delete_namespace(name=name, body=client.V1DeleteOptions())
        print(f"🗑️ Namespace '{name}' deletion initiated successfully.")
        return True
    except ApiException as e:
        if e.status == 404:
            print(f"🤷 Namespace '{name}' not found for deletion (perhaps already deleted).")
            return True
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
    """
    return patch_k8s_namespace_metadata(namespace_name, labels=labels_to_set)

def patch_k8s_namespace_metadata(namespace_name: str, labels: dict = None, annotations: dict = None) -> bool:
    """
    Patches labels and/or annotations on a given namespace.
    """
    api = get_api_client()
    try:
        patch_body = {"metadata": {}}
        if labels is not None:
            patch_body["metadata"]["labels"] = labels
        if annotations is not None:
            patch_body["metadata"]["annotations"] = annotations

        if not patch_body["metadata"]:
            print(f"ℹ️ No labels or annotations provided to patch for namespace '{namespace_name}'.")
            return True

        api.patch_namespace(name=namespace_name, body=patch_body)
        print(f"✅ Metadata (labels: {labels}, annotations: {annotations}) successfully patched onto namespace '{namespace_name}'.")
        return True
    except ApiException as e:
        if e.status == 404:
            print(f"🤷 Namespace '{namespace_name}' not found for metadata update.")
        else:
            _print_api_exception_details(e, f"Error patching metadata for namespace '{namespace_name}'")
        return False
    except Exception as ex_general:
        print(f"🔥🔥🔥 UNEXPECTED ERROR in patch_k8s_namespace_metadata for '{namespace_name}': {type(ex_general).__name__} - {ex_general}")
        import traceback
        traceback.print_exc()
        return False