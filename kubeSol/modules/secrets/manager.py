# kubesol/modules/secrets/manager.py
"""
Core logic for managing KubeSol Secrets.
Interacts with the k8s_api module to manipulate Kubernetes Secrets.
"""
import os
import base64
import json
from kubernetes.client.exceptions import ApiException

# Importa k8s_api desde su ubicación en core
import kubesol.core.k8s_api as k8s_api 

def create_new_secret_from_file(secret_name: str, file_path: str, namespace: str) -> bool:
    """
    Creates a new Kubernetes Secret from the content of a local file.
    The file content will be base64 encoded and stored under a key derived from the filename.
    """
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at '{file_path}'. Cannot create secret '{secret_name}'.")
        return False

    try:
        with open(file_path, 'rb') as f_stream:
            file_content_bytes = f_stream.read()
        
        # Usamos el nombre base del archivo como clave dentro del secreto
        secret_key = os.path.basename(file_path)
        b64_data = {secret_key: base64.b64encode(file_content_bytes).decode('utf-8')}

        print(f"ℹ️ Attempting to create Secret '{secret_name}' from file '{file_path}' (key: '{secret_key}') in namespace '{namespace}'...")
        
        # k8s_api.create_secret_with_mixed_data permite datos base64
        k8s_api.create_secret_with_mixed_data(
            name=secret_name,
            string_data_payload=None, # No hay datos string planos directos
            b64_data_payload=b64_data,
            namespace=namespace
        )
        return True
    except ApiException as e:
        print(f"❌ K8s API error creating secret '{secret_name}': {e.reason} (Status: {e.status})")
        # k8s_api ya tiene manejo de errores detallado, solo un mensaje general aquí.
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating secret '{secret_name}' from file '{file_path}': {type(e).__name__} - {e}")
        return False

def get_secret_details(secret_name: str, namespace: str) -> dict | None:
    """
    Retrieves and displays details of a Kubernetes Secret.
    Decodes base64 content if present.
    """
    print(f"ℹ️ Attempting to get details for Secret '{secret_name}' in namespace '{namespace}'...")
    secret_data = k8s_api.get_secret_data(name=secret_name, namespace=namespace)

    if secret_data is None: # Secret not found or API error already printed by k8s_api
        return None
    if not secret_data:
        print(f"🤷 Secret '{secret_name}' in namespace '{namespace}' found, but contains no data.")
        return {}

    print(f"✅ Secret '{secret_name}' details:")
    output = {}
    for key, value in secret_data.items():
        try:
            # Intentar decodificar como JSON si parece serlo
            parsed_value = json.loads(value)
            output[key] = parsed_value
            print(f"   - {key}: (JSON Content) {str(parsed_value)[:100]}...") # Mostrar un snippet
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Si no es JSON o hay un error de decodificación, mostrar como string normal (o snippet)
            output[key] = value
            display_value = value
            if len(display_value) > 100:
                display_value = display_value[:97] + "..."
            print(f"   - {key}: {display_value}")
        except Exception as e:
            print(f"   - {key}: (Error processing content) {type(e).__name__} - {e}")
            output[key] = "(Error)"
    return output

def delete_secret(secret_name: str, namespace: str) -> bool:
    """
    Deletes a Kubernetes Secret.
    """
    print(f"ℹ️ Attempting to delete Secret '{secret_name}' from namespace '{namespace}'...")
    try:
        k8s_api.delete_secret(name=secret_name, namespace=namespace)
        return True
    except ApiException as e:
        print(f"❌ K8s API error deleting secret '{secret_name}': {e.reason} (Status: {e.status})")
        return False
    except Exception as e:
        print(f"❌ Unexpected error deleting secret '{secret_name}': {type(e).__name__} - {e}")
        return False

def update_secret_from_file(secret_name: str, file_path: str, namespace: str) -> bool:
    # ... (file existence check) ...
    print(f"ℹ️ Updating Secret '{secret_name}' by deleting and recreating it (from file '{file_path}')...")
    # This line is the culprit:
    if not k8s_api.delete_secret(name=secret_name, namespace=namespace): #
        print(f"❌ Failed to delete existing secret '{secret_name}' for update. Aborting.") #
        return False #
    
    # If deletion was successful, it proceeds to recreate.
    return create_new_secret_from_file(secret_name, file_path, namespace) #