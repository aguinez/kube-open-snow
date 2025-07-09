# kubesol/modules/secrets/handlers.py
"""
Handlers for KubeSol Secret CLI commands.
These functions bridge the parsed command from the commands.py module
to the core logic in manager.py and handle CLI output.
"""
from tabulate import tabulate

# Importa el manager de secretos de este mismo módulo
from kubesol.modules.secrets import manager
# Importa el contexto global de KubeSol
from kubesol.core.context import KubeSolContext
# Importa constantes si son necesarias para mensajes o defaults (ej. DEFAULT_NAMESPACE)
from kubesol.constants import DEFAULT_NAMESPACE # Asegúrate de que esta constante existe

def handle_create_secret_from_file(parsed_args: dict, context: KubeSolContext):
    """
    Handles the CREATE SECRET <name> FROM FILE <path> command.
    """
    secret_name = parsed_args.get("secret_name")
    file_path = parsed_args.get("file_path")
    
    current_namespace = context.current_namespace # Usar el namespace del contexto actual

    print(f"ℹ️ Attempting to create secret '{secret_name}' from file '{file_path}' in namespace '{current_namespace}'.")
    
    success = manager.create_new_secret_from_file(secret_name, file_path, current_namespace)
    
    if success:
        print(f"✅ Secret '{secret_name}' created successfully.")
    else:
        print(f"❌ Failed to create secret '{secret_name}'. See messages above.")

def handle_get_secret(parsed_args: dict, context: KubeSolContext):
    """
    Handles the GET SECRET <name> command.
    """
    secret_name = parsed_args.get("secret_name")
    current_namespace = context.current_namespace

    print(f"ℹ️ Retrieving secret '{secret_name}' from namespace '{current_namespace}'.")
    
    # El manager ya imprime los detalles, solo necesitamos su resultado para saber si lo encontró.
    secret_details = manager.get_secret_details(secret_name, current_namespace)
    
    if secret_details is None:
        print(f"❌ Secret '{secret_name}' not found or an error occurred.")
    elif not secret_details: # Encontrado pero sin datos
        pass # manager ya imprimió que no tenía datos
    else:
        pass # manager ya imprimió los detalles

def handle_delete_secret(parsed_args: dict, context: KubeSolContext):
    """
    Handles the DELETE SECRET <name> command.
    """
    secret_name = parsed_args.get("secret_name")
    current_namespace = context.current_namespace

    print(f"ℹ️ Deleting secret '{secret_name}' from namespace '{current_namespace}'.")
    
    # Añadir confirmación antes de borrar (opcional, pero buena práctica para operaciones destructivas)
    confirm = input(f"CONFIRM DELETION of Secret '{secret_name}' in namespace '{current_namespace}' by typing its name: ").strip()
    if confirm != secret_name:
        print("Deletion cancelled.")
        return

    success = manager.delete_secret(secret_name, current_namespace)
    
    if success:
        print(f"✅ Secret '{secret_name}' deleted successfully.")
    else:
        print(f"❌ Failed to delete secret '{secret_name}'. See messages above.")

def handle_update_secret_from_file(parsed_args: dict, context: KubeSolContext):
    """
    Handles the UPDATE SECRET <name> FROM FILE <path> command.
    """
    secret_name = parsed_args.get("secret_name")
    file_path = parsed_args.get("file_path")
    current_namespace = context.current_namespace

    print(f"ℹ️ Attempting to update secret '{secret_name}' from file '{file_path}' in namespace '{current_namespace}'.")
    
    # La implementación del manager es un borrado + recreado.
    success = manager.update_secret_from_file(secret_name, file_path, current_namespace)

    if success:
        print(f"✅ Secret '{secret_name}' updated successfully (recreated).")
    else:
        print(f"❌ Failed to update secret '{secret_name}'. See messages above.")