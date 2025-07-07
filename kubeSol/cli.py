# kubesol/cli.py
import sys
import os
import readline
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from kubesol.dispatch import dispatcher
from kubesol.core.context import KubeSolContext

import kubesol.dispatch.command_registry
import kubesol.modules 

def _check_k8s_api_connection():
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        v1.list_namespace()
        print("✅ Conectado a Kubernetes.")
        return True
    except config.ConfigException:
        print("❌ Error: No se pudo cargar la configuración de Kubernetes.")
        print("   Asegúrate de que tu archivo kubeconfig esté configurado correctamente.")
        return False
    except ApiException as e:
        print(f"❌ Error de conexión a la API de Kubernetes: {e.status} - {e.reason}")
        print("   Asegúrate de que tu contexto de Kubernetes esté apuntando a un clúster en ejecución.")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al conectar a Kubernetes: {type(e).__name__} - {e}")
        return False

def shell():
    if not _check_k8s_api_connection():
        print("Saliendo de KubeSol debido a problemas de conexión con la API de Kubernetes.")
        return

    context = KubeSolContext()
    
    print("\nBienvenido a KubeSol. Escribe 'HELP' para ver los comandos disponibles o 'EXIT' para salir.")
    print("Para establecer el contexto: USE PROJECT <nombre_proyecto> ENV <nombre_entorno>")

    while True:
        try:
            line = input(context.get_prompt())
            line = line.strip()
            
            print(f"DEBUG_CLI: Input recibido: '{line}'") # <--- AÑADIDA LÍNEA DE DEBUG

            if not line:
                continue

            if line.upper() == "EXIT":
                print("¡Adiós!")
                break
            elif line.upper() == "HELP":
                print("\nComandos disponibles (ejemplos):")
                print("  CREATE PROJECT <nombre_proyecto>")
                print("  CREATE ENV <nombre_entorno> FOR PROJECT <nombre_proyecto>")
                print("  LIST PROJECTS")
                print("  GET PROJECT <nombre_proyecto>")
                print("  USE PROJECT <nombre_proyecto> ENV <nombre_entorno>")
                print("  DROP PROJECT <nombre_proyecto>")
                print("  DROP ENVIRONMENT <nombre_entorno> FROM PROJECT <nombre_proyecto>")
                print("  (Más comandos disponibles a medida que se cargan módulos...)")
                continue
            elif line.upper() == "CONTEXT":
                print(context)
                continue

            dispatcher.execute_command(line, context)

        except EOFError:
            print("\n¡Adiós!")
            break
        except KeyboardInterrupt:
            print("\nOperación cancelada.")
        except Exception as e:
            print(f"❌ Error durante la ejecución del comando: {type(e).__name__} - {e}")

def main():
    shell()

if __name__ == "__main__":
    main()