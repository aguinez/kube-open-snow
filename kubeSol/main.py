# kubeSol/main.py
from kubeSol.engine.kind_manager import select_cluster 
from kubeSol.engine.executor import execute_command 
from kubeSol.constants import DEFAULT_NAMESPACE

def shell():
    """
    Runs the KubeSol interactive shell.
    """
    print("KubeSol v0.1.1 - Write SQL-like commands for Kubernetes.") # Updated name
    
    current_namespace = DEFAULT_NAMESPACE 
    print(f"ℹ️ Current Namespace: {current_namespace}")

    while True:
        try:
            command_input = input(f"{current_namespace} >> ") 
            if command_input.strip().lower() in ["exit", "quit"]:
                print("👋 Goodbye!") 
                break
            if not command_input.strip():
                continue
            execute_command(command_input, namespace=current_namespace)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!") 
            break
        except Exception as e:
            print(f"❌ Unexpected Error in shell: {e}")

def main():
    """
    Main entry point for KubeSol application.
    Initializes Kubernetes client, selects cluster, and starts the shell.
    """
    try:
        from kubeSol.engine.k8s_api import core_v1_api 
        if core_v1_api is None:
            print("🚨 KubeSol cannot start due to Kubernetes configuration issues.") # Updated name
            exit(1)
    except Exception as e:
        print(f"🚨 Critical Error during K8s API client initialization check: {e}")
        exit(1)

    selected_cluster_name = select_cluster()
    if selected_cluster_name:
        print(f"🚀 KubeSol connected to cluster: {selected_cluster_name}") # Updated name
        shell()
    else:
        print(" KubeSol exiting as no cluster was selected or available.") # Updated name

if __name__ == "__main__":
    main()