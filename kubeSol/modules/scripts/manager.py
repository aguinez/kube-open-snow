# kubesol/modules/scripts/manager.py
"""
Core logic for managing KubeSol script execution as Kubernetes Jobs.
Interacts with the k8s_api module.
"""
import os
import uuid
import time
import yaml # Para parsear archivos YAML
from kubernetes import client # Para V1EnvVar
from kubernetes.client.exceptions import ApiException

# Importa k8s_api desde su ubicación en core
import kubesol.core.k8s_api as k8s_api
from kubesol.constants import DEFAULT_NAMESPACE # Asegúrate de que esta constante existe

# --- Constantes para scripts (podrían ir en kubesol/constants.py) ---
DEFAULT_SCRIPT_JOB_IMAGE = "python:3.11-alpine" # Imagen por defecto
DEFAULT_CPU_REQUEST = "200m" # 200 milicores
DEFAULT_MEMORY_REQUEST = "200Mi" # 200 mebibytes
DEFAULT_JOB_RESTART_POLICY = "Never" # Un Job suele ejecutarse una vez y no reiniciarse por fallos transitorios
JOB_ACTIVE_DEADLINE_SECONDS = 600 # 10 minutos por defecto para el Job
JOB_BACKOFF_LIMIT = 0 # No reintentar por defecto si falla el pod. Fallar el Job.

def _generate_job_name(script_base_name: str) -> str:
    """Genera un nombre de Job único basado en el nombre del script."""
    sanitized_name = k8s_api._sanitize_for_k8s_name(script_base_name)
    return f"kubesol-script-{sanitized_name}-{uuid.uuid4().hex[:8]}"

def _read_yaml_config_as_env_vars(yaml_file_path: str) -> list[client.V1EnvVar]:
    """
    Reads a YAML file and converts its top-level key-value pairs into Kubernetes V1EnvVar objects.
    Fails if duplicate keys are found.
    """
    if not os.path.exists(yaml_file_path):
        raise FileNotFoundError(f"YAML config file not found at: '{yaml_file_path}'")

    with open(yaml_file_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    if not isinstance(config_data, dict):
        raise ValueError(f"YAML config file '{yaml_file_path}' must contain a top-level dictionary.")

    env_vars = []
    seen_keys = set()
    for key, value in config_data.items():
        if not isinstance(key, str):
            raise ValueError(f"YAML config key '{key}' is not a string. All top-level keys must be strings.")
        
        if key in seen_keys:
            raise ValueError(f"Duplicate key '{key}' found in YAML config file '{yaml_file_path}'. Aborting.")
        seen_keys.add(key)

        # Convertir todos los valores a string para ENV VARS de K8s
        env_vars.append(client.V1EnvVar(name=key, value=str(value)))
    
    return env_vars

def execute_script_job(
    job_name_user_input: str | None,
    script_path_local: str,
    image: str | None,
    params_yaml_file_path: str | None,
    namespace: str,
    cpu_request: str | None = None,
    memory_request: str | None = None
) -> str | None:
    """
    Executes a local script as a Kubernetes Job.
    Returns the name of the created Job or None on failure.
    """
    if not os.path.exists(script_path_local):
        print(f"❌ Error: Script file not found at '{script_path_local}'.")
        return None

    script_base_name = os.path.basename(script_path_local)
    actual_job_name = job_name_user_input if job_name_user_input else _generate_job_name(script_base_name)
    image_to_use = image if image else DEFAULT_SCRIPT_JOB_IMAGE
    cpu_req = cpu_request if cpu_request else DEFAULT_CPU_REQUEST
    mem_req = memory_request if memory_request else DEFAULT_MEMORY_REQUEST

    print(f"ℹ️ Preparing to execute script '{script_base_name}' as Job '{actual_job_name}' in namespace '{namespace}'...")
    print(f"   Image: {image_to_use}, CPU Request: {cpu_req}, Memory Request: {mem_req}")

    # 1. Leer el contenido del script
    with open(script_path_local, 'r', encoding='utf-8') as f:
        script_content = f.read()

    # 2. Crear un ConfigMap para el script (ya que el script puede ser grande)
    script_cm_name = f"{actual_job_name}-script-cm"
    all_env_vars = []
    
    # Add Python unbuffered output environment variable
    all_env_vars.append(client.V1EnvVar(name="PYTHONUNBUFFERED", value="1"))
    
    # Manejar parámetros desde YAML como variables de entorno
    if params_yaml_file_path:
        try:
            yaml_env_vars = _read_yaml_config_as_env_vars(params_yaml_file_path)
            all_env_vars.extend(yaml_env_vars)
            print(f"   Loaded {len(yaml_env_vars)} parameters from '{params_yaml_file_path}' as environment variables.")
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ Error loading parameters from YAML: {e}. Aborting script execution.")
            return None

    # El script mismo se montará como un ConfigMap.
    script_cm_data = {"script.py": script_content} # Asumimos .py por ahora, o se puede parametrizar

    # Crear el ConfigMap del script
    if not k8s_api.create_configmap(name=script_cm_name, data=script_cm_data, namespace=namespace):
        print(f"❌ Failed to create ConfigMap '{script_cm_name}' for script content. Aborting.")
        return None

    # --- Definir el Job de Kubernetes ---
    # Montar el ConfigMap del script como un volumen
    script_mount_path = "/usr/src/app" # Ruta estándar para scripts
    script_filename_in_pod = "script.py" # Nombre del script una vez montado

    volumes = [
        client.V1Volume(
            name="script-volume",
            config_map=client.V1ConfigMapVolumeSource(name=script_cm_name)
        )
    ]
    volume_mounts = [
        client.V1VolumeMount(
            name="script-volume",
            mount_path=script_mount_path
        )
    ]

    # Comando de entrada para el contenedor (ej. python /usr/src/app/script.py)
    container_command = ["python", f"{script_mount_path}/{script_filename_in_pod}"]
    container_args = None  # No args needed since we're putting everything in command

    # Configurar los límites de recursos
    resources = client.V1ResourceRequirements(
        requests={"cpu": cpu_req, "memory": mem_req},
        limits={"cpu": cpu_req, "memory": mem_req}
    )

    # Crear el Job
    success = k8s_api.create_k8s_job(
        job_name=actual_job_name,
        namespace=namespace,
        image=image_to_use,
        script_configmap_name=script_cm_name, # Se usa para el volumen
        script_file_key_in_cm=script_filename_in_pod, # La clave dentro del CM que contiene el script
        script_mount_path=script_mount_path, # Donde se monta el CM
        container_command=container_command,
        container_args=container_args if container_args else [],
        env_vars=all_env_vars,
        pod_restart_policy=DEFAULT_JOB_RESTART_POLICY,
        job_backoff_limit=JOB_BACKOFF_LIMIT,
        job_active_deadline_seconds=JOB_ACTIVE_DEADLINE_SECONDS
    )

    if not success:
        print(f"❌ Failed to create Kubernetes Job '{actual_job_name}'. Aborting.")
        # Limpiar el ConfigMap del script si el Job no se pudo crear
        k8s_api.delete_configmap(name=script_cm_name, namespace=namespace)
        return None

    # --- Monitorear y obtener logs en tiempo real ---
    print(f"ℹ️ Job '{actual_job_name}' created. Monitoring its status...")
    
    print(f"ℹ️ Streaming logs for Job '{actual_job_name}' in real-time...")
    print(f"--- Logs for Job '{actual_job_name}' ---")
    
    job_completed = False
    max_attempts = JOB_ACTIVE_DEADLINE_SECONDS // 2  # Check every 2 seconds instead of 5
    attempts = 0
    logs_retrieved = False
    
    while not job_completed and attempts < max_attempts:
        job_status = k8s_api.get_k8s_job_status(actual_job_name, namespace)
        
        # Always try to get logs, regardless of job status
        if not logs_retrieved:
            logs = k8s_api.get_k8s_job_logs(actual_job_name, namespace)
            if logs:
                print(logs)
                logs_retrieved = True
        
        if job_status:
            if job_status.get("succeeded") or job_status.get("failed"):
                job_completed = True
                # Try one more time to get logs if job just completed
                if not logs_retrieved:
                    logs = k8s_api.get_k8s_job_logs(actual_job_name, namespace)
                    if logs:
                        print(logs)
                        logs_retrieved = True
            elif job_status.get("active"):
                if not logs_retrieved:
                    print(f"   Job '{actual_job_name}' still active ({job_status.get('active')} pod(s))...")
            else:
                print(f"   Job '{actual_job_name}' status: {job_status.get('conditions', 'N/A')}. Waiting...")
        else:
            print(f"   Could not get status for Job '{actual_job_name}'. Waiting...")

        if not job_completed:
            time.sleep(2)  # Reduced sleep time for faster log retrieval
            attempts += 1
    
    # Final log retrieval attempts with more patience
    if not logs_retrieved:
        for _ in range(3):  # Try 3 more times
            logs = k8s_api.get_k8s_job_logs(actual_job_name, namespace)
            if logs:
                print(logs)
                logs_retrieved = True
                break
            time.sleep(1)  # Wait 1 second between attempts
    
    if not logs_retrieved:
        print("No logs available or failed to retrieve logs.")
    
    if not job_completed:
        print(f"⚠️ Job '{actual_job_name}' did not complete within {JOB_ACTIVE_DEADLINE_SECONDS} seconds or max attempts reached.")
        
    print(f"--- End of Logs for Job '{actual_job_name}' ---")

    # 6. Limpieza automática de recursos
    print(f"ℹ️ Cleaning up Job '{actual_job_name}' and associated ConfigMap '{script_cm_name}'...")
    k8s_api.delete_k8s_job(actual_job_name, namespace)
    k8s_api.delete_configmap(script_cm_name, namespace)
    print(f"✅ Cleanup for Job '{actual_job_name}' completed.")

    return actual_job_name