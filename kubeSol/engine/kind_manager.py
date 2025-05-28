# kubeSol/engine/kind_manager.py
import subprocess

def list_kind_clusters():
    """Lists available KinD clusters."""
    try:
        result = subprocess.run(["kind", "get", "clusters"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            if "unknown command" in result.stderr or "executable file not found" in result.stderr:
                print("⚠️  'kind' command not found. Please ensure KinD is installed and in your PATH.")
            else:
                print(f"⚠️ Error listing KinD clusters: {result.stderr.strip()}")
            return []
        return result.stdout.strip().splitlines()
    except FileNotFoundError:
        print("⚠️  'kind' command not found. Please ensure KinD is installed and in your PATH.")
        return []
    except Exception as e: 
        print(f"❌ Unexpected error while listing KinD clusters: {e}")
        return []


def use_kind_cluster(cluster_name: str):
    """Switches the kubectl context to the specified KinD cluster."""
    context_name = f"kind-{cluster_name}" 
    try:
        result = subprocess.run(["kubectl", "config", "use-context", context_name], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            if "no such context" in result.stderr:
                raise RuntimeError(f"Context '{context_name}' not found. Ensure the KinD cluster '{cluster_name}' exists and is configured correctly.")
            else:
                raise RuntimeError(f"Failed to switch to context '{context_name}':\n{result.stderr.strip()}")
        print(f"✅ Switched kubectl context to: {context_name}")
        return True
    except FileNotFoundError:
        print("⚠️ 'kubectl' command not found. Please ensure kubectl is installed and in your PATH.")
        return False
    except Exception as e: 
        print(f"❌ Error switching cluster context: {e}") 
        return False


def select_cluster(): 
    """Allows the user to select a KinD cluster to use."""
    available_clusters = list_kind_clusters() 
    if not available_clusters:
        print("❌ No KinD clusters found or 'kind' command is not available.")
        print("   You can create a new KinD cluster with: kind create cluster")
        return None

    print("🧠 Available KinD clusters:")
    for i, name in enumerate(available_clusters):
        print(f"  {i + 1}. {name}")

    while True:
        try:
            selection_input = input("➡️ Select a cluster by number (or type 'exit' to cancel): ") 
            if selection_input.strip().lower() == 'exit':
                return None
            
            selected_index = int(selection_input) - 1 
            
            if 0 <= selected_index < len(available_clusters):
                cluster_to_use = available_clusters[selected_index] 
                if use_kind_cluster(cluster_to_use):
                    return cluster_to_use 
                else:
                    print("   Please try selecting another cluster or ensure 'kubectl' is configured.")
                    return None 
            else:
                print(f"   Invalid selection. Please enter a number between 1 and {len(available_clusters)}.")
        except ValueError:
            print("   Invalid input. Please enter a number.")