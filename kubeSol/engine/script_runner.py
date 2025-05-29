# kubeSol/engine/script_runner.py
import time
import uuid
from kubeSol.engine import k8s_api 
from kubeSol.constants import (
    SCRIPT_TYPE_PYTHON, SCRIPT_TYPE_PYSPARK,
    SCRIPT_CM_KEY_CODE, SCRIPT_CM_KEY_TYPE, SCRIPT_CM_KEY_ENGINE, SCRIPT_CM_KEY_CODE
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
        #image = "python:3.9-slim"
        image="cloudsaur/arrow-to-gcs:latest"
        container_command = ["python", script_path_in_container]
    elif script_type == SCRIPT_TYPE_PYSPARK:
        image = "cloudsaur/arrow-to-gcs:latest"  
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
        for i in range(timeout_seconds // check_interval_seconds):
            time.sleep(check_interval_seconds)
            status = k8s_api.get_k8s_job_status(job_name, namespace) 
            
            if status:
                active_count = status.get('active') or 0 # Default None to 0
                succeeded_count = status.get('succeeded') or 0 # Default None to 0
                failed_count = status.get('failed') or 0   # Default None to 0

                print(f"   Job Status: Active={active_count}, Succeeded={succeeded_count}, Failed={failed_count} (Attempt {i+1})")

                if succeeded_count > 0: # Check against the potentially 0 value
                    print(f"✅ Job '{job_name}' completed successfully.")
                    logs = k8s_api.get_k8s_job_logs(job_name, namespace) 
                    if logs: print(f"\n--- Job Logs ---\n{logs}\n--- End Job Logs ---")
                    return True 
                
                if failed_count > 0: # Check against the potentially 0 value
                    print(f"❌ Job '{job_name}' failed.")
                    logs = k8s_api.get_k8s_job_logs(job_name, namespace, tail_lines=50) # Get more lines for failed jobs
                    if logs: print(f"\n--- Job Logs (Failure) ---\n{logs}\n--- End Job Logs ---")
                    return False 
            else:
                print(f"   Could not retrieve status for Job '{job_name}'. Will retry...")
            
        else:  # Loop finished without returning (timeout)
            print(f"⌛ Job '{job_name}' monitoring exceeded the time limit ({timeout_seconds}s). Check status manually.")
            # Attempt to get logs one last time on timeout if the job might have finished or failed silently
            logs = k8s_api.get_k8s_job_logs(job_name, namespace, tail_lines=100)
            if logs: print(f"\n--- Job Logs (Timeout) ---\n{logs}\n--- End Job Logs ---")
            return False 
            
    except KeyboardInterrupt:
        print(f"\nℹ️ Log monitoring for '{job_name}' interrupted by user.")
        return False # Consider what state to return here
    except Exception as e:
        print(f"❌ An error occurred during Job monitoring for '{job_name}': {e}")
        import traceback
        traceback.print_exc()
        return False # Indicate monitoring failed


def run_script_as_k8s_job(
        cli_script_name: str,
        script_cm_data: dict,
        resolved_parameters: dict,
        namespace: str,
        secret_mounts: list | None = None): # NEW secret_mounts parameter
    """Runs a script as a Kubernetes Job, potentially with secret mounts."""
    print(f"🚀 Attempting to run script '{cli_script_name}' as a Kubernetes Job in namespace '{namespace}'...")
    # ... (existing logic to get script_code, script_type, determine image, container_command, job_name) ...
    # ... (script_args, env_vars setup) ...

    script_code = script_cm_data.get(SCRIPT_CM_KEY_CODE)
    script_type = script_cm_data.get(SCRIPT_CM_KEY_TYPE)

    if not script_code:
        print(f"❌ Code not found for script '{cli_script_name}'.")
        return

    # Determine image and command for the container (this helper might need script_type from script_cm_data)
    # This path assumes script_cm_data has been fetched and validated.
    script_mount_dir = "/kubesol_scripts" 
    script_path_in_container = f"{script_mount_dir}/{SCRIPT_CM_KEY_CODE}"
    
    image, container_command_list = _determine_container_config(script_type, script_path_in_container, cli_script_name) # Renamed var
    if not image or not container_command_list:
        print(f"❌ Could not determine container configuration for script '{cli_script_name}'. Execution aborted.")
        return

    job_name_suffix = uuid.uuid4().hex[:8]
    k8s_job_name = f"kubesol-exec-{cli_script_name.lower().replace('_', '-')}-{job_name_suffix}"[:63]

    script_cmd_args = _prepare_args_from_params(resolved_parameters) # Renamed var
    # For now, env_vars from parameters are not implemented, pass None or an empty list.
    # If you want to pass resolved_parameters as env vars too, call _prepare_env_vars_from_params
    job_env_vars = None # Or: _prepare_env_vars_from_params(resolved_parameters)

    script_cm_name_on_k8s = k8s_api.get_script_cm_name(cli_script_name)


    job_created = k8s_api.create_k8s_job(
        job_name=k8s_job_name,
        namespace=namespace,
        image=image,
        script_configmap_name=script_cm_name_on_k8s,
        script_file_key_in_cm=SCRIPT_CM_KEY_CODE, 
        script_mount_path=script_mount_dir,      
        container_command=container_command_list,      
        container_args=script_cmd_args,
        env_vars=job_env_vars, # Pass the env_vars for the job
        # NEW: Pass the secret mount configurations
        secret_volume_mount_configs=secret_mounts
    )

    if job_created:
        _monitor_k8s_job(k8s_job_name, namespace) # Assumes _monitor_k8s_job exists
    else:
        print(f"❌ Job '{k8s_job_name}' could not be created. Script execution failed.")