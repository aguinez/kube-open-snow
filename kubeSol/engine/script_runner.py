# kubeSol/engine/script_runner.py
import time
import uuid
from kubeSol.engine import k8s_api 
from kubeSol.constants import (
    SCRIPT_TYPE_PYTHON, SCRIPT_TYPE_PYSPARK,
    SCRIPT_CM_KEY_CODE, SCRIPT_CM_KEY_TYPE, SCRIPT_CM_KEY_ENGINE
)

def _prepare_env_vars_from_params(parameters: dict) -> list:
    """Converts a dictionary of parameters into a list of V1EnvVar for Kubernetes."""
    from kubernetes import client 
    env_vars = []
    for key, value in parameters.items():
        env_vars.append(client.V1EnvVar(name=f"PARAM_{key.upper()}", value=str(value)))
    return env_vars

def _prepare_args_from_params(parameters: dict) -> list:
    """Converts a dictionary of parameters into a list of string arguments."""
    args = []
    for key, value in parameters.items():
        args.append(f"--{key}")
        args.append(str(value))
    return args

def _determine_container_config(script_type: str, script_path_in_container: str, cli_script_name: str) -> tuple[str | None, list[str] | None]:
    """
    Determines the Docker image and container command based on the script type.
    """
    image = None
    container_command = None

    if script_type == SCRIPT_TYPE_PYTHON:
        image = "python:3.9-slim"
        container_command = ["python", script_path_in_container]
    elif script_type == SCRIPT_TYPE_PYSPARK:
        image = "your_repo/pyspark-runner:latest"  
        container_command = ["python", script_path_in_container] 
        print(f"⚠️ Warning: For PySpark with K8S_JOB, you need a Docker image ('{image}') with PySpark and dependencies.")
        print(f"     The script '{cli_script_name}' will be executed as a Python script within that image.")
    else:
        print(f"❌ Script type '{script_type}' is not currently supported by the K8S_JOB engine.")
        return None, None
    
    if not image:
        print(f"❌ Could not determine the image for script type '{script_type}'.")
        return None, None
        
    return image, container_command

def _monitor_k8s_job(job_name: str, namespace: str, timeout_seconds: int = 600, check_interval_seconds: int = 10):
    """
    Monitors a Kubernetes Job for completion or failure.
    """
    print(f"⏳ Monitoring Job '{job_name}'... (Ctrl+C to stop log monitoring)")
    try:
        for _ in range(timeout_seconds // check_interval_seconds):
            time.sleep(check_interval_seconds)
            status = k8s_api.get_k8s_job_status(job_name, namespace) 
            if status:
                print(f"   Job Status: Succeeded={status.get('succeeded')}, Failed={status.get('failed')}, Active={status.get('active')}")
                if status.get('succeeded', 0) > 0:
                    print(f"✅ Job '{job_name}' completed successfully.")
                    logs = k8s_api.get_k8s_job_logs(job_name, namespace) 
                    if logs: print(f"\n--- Job Logs ---\n{logs}\n--- End Logs ---")
                    return True 
                if status.get('failed', 0) > 0:
                    print(f"❌ Job '{job_name}' failed.")
                    logs = k8s_api.get_k8s_job_logs(job_name, namespace, tail_lines=50)
                    if logs: print(f"\n--- Job Logs ---\n{logs}\n--- End Logs ---")
                    return False 
            else:
                print(f"   Could not get status for Job '{job_name}'.")
                return False 
        else:  
            print(f"⌛ Job '{job_name}' monitoring exceeded the time limit ({timeout_seconds}s). Check status manually.")
            return False 
            
    except KeyboardInterrupt:
        print(f"\nℹ️ Log monitoring for '{job_name}' interrupted by user.")
        return False 
    except Exception as e:
        print(f"❌ An error occurred during Job monitoring: {e}")
        return False 


def run_script_as_k8s_job(
        cli_script_name: str,
        script_cm_data: dict,
        resolved_parameters: dict,
        namespace: str):
    """Runs a script as a Kubernetes Job."""
    print(f"🚀 Attempting to run script '{cli_script_name}' as a Kubernetes Job...")

    script_code = script_cm_data.get(SCRIPT_CM_KEY_CODE)
    script_type = script_cm_data.get(SCRIPT_CM_KEY_TYPE)

    if not script_code:
        print(f"❌ Code not found for script '{cli_script_name}'.")
        return

    script_mount_dir = "/kubesol_scripts" # Changed mount dir to reflect new name
    script_path_in_container = f"{script_mount_dir}/{SCRIPT_CM_KEY_CODE}"


    image, container_command = _determine_container_config(script_type, script_path_in_container, cli_script_name)
    if not image or not container_command:
        return 

    job_name_suffix = uuid.uuid4().hex[:8]
    k8s_job_name = f"kubesol-exec-{cli_script_name.lower().replace('_', '-')}-{job_name_suffix}"[:63] # Changed job name prefix

    script_args = _prepare_args_from_params(resolved_parameters)
    env_vars = None

    script_configmap_name_on_k8s = k8s_api.get_script_cm_name(cli_script_name) 

    job_created = k8s_api.create_k8s_job( 
        job_name=k8s_job_name,
        namespace=namespace,
        image=image,
        script_configmap_name=script_configmap_name_on_k8s,
        script_file_key_in_cm=SCRIPT_CM_KEY_CODE,
        script_mount_path=script_mount_dir,
        container_command=container_command,
        container_args=script_args,
        env_vars=env_vars
    )

    if job_created:
        _monitor_k8s_job(k8s_job_name, namespace)
    else:
        print(f"❌ Could not create Job '{k8s_job_name}'. Script execution cancelled.")