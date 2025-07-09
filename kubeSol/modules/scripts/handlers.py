# kubesol/modules/scripts/handlers.py
"""
Handlers for KubeSol Script execution CLI commands.
These functions bridge the parsed command from the commands.py module
to the core logic in manager.py and handle CLI output.
"""
from tabulate import tabulate

# Importa el manager de scripts de este mismo módulo
from kubesol.modules.scripts import manager
# Importa el contexto global de KubeSol
from kubesol.core.context import KubeSolContext
# Importa constantes si son necesarias para mensajes o defaults (ej. DEFAULT_NAMESPACE)
from kubesol.constants import DEFAULT_NAMESPACE # Asegúrate de que esta constante existe

def handle_execute_script(parsed_args: dict, context: KubeSolContext):
    """
    Handles the EXECUTE SCRIPT <job_name> FROM FILE <path> [WITH IMAGE <image>] [WITH PARAMS FROM FILE <yaml_path>] command.
    """
    job_name_user_input = parsed_args.get("job_name")
    script_path_local = parsed_args.get("script_path_local")
    image = parsed_args.get("image")
    params_yaml_file_path = parsed_args.get("params_yaml_file_path")

    current_namespace = context.current_namespace # Usar el namespace del contexto actual

    print(f"ℹ️ Initiating script execution for '{script_path_local}' in namespace '{current_namespace}'.")
    
    actual_job_name = manager.execute_script_job(
        job_name_user_input=job_name_user_input,
        script_path_local=script_path_local,
        image=image,
        params_yaml_file_path=params_yaml_file_path,
        namespace=current_namespace
    )
    
    if actual_job_name:
        print(f"✅ Script execution completed. Kubernetes Job name: '{actual_job_name}'.")
    else:
        print(f"❌ Script execution failed. See messages above.")

