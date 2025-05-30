# kubeSol/main.py
from kubeSol.engine.kind_manager import select_cluster 
from kubeSol.engine.executor import execute_command 
from kubeSol.constants import DEFAULT_NAMESPACE
from kubeSol.notebook.cli import launch_notebook_server

def shell():
    """
    Runs the KubeSol interactive shell.
    Supports multi-line command input. Commands are executed when the
    accumulated input ends with a semicolon (;).
    """
    print("KubeSol - Write SQL-like commands for Kubernetes.")
    print("Enter commands, spanning multiple lines if needed.")
    print("End your complete command with a semicolon (;) to execute.")
    
    # This shell will handle commands like CREATE SCRIPT, EXECUTE SCRIPT, etc.
    # The LAUNCH NOTEBOOK command will be handled before entering this loop,
    # or as a special case within it.
    print("KubeSol - Write SQL-like commands for Kubernetes.")
    print("Enter commands, spanning multiple lines if needed.")
    print("End your complete command with a semicolon (;) to execute.")
    print("Type 'LAUNCH NOTEBOOK' to start a Jupyter Notebook session for KubeSol.")
    
    current_namespace = DEFAULT_NAMESPACE 
    command_buffer = [] 

    while True:
        if not command_buffer:
            prompt = f"{current_namespace} >> "
        else:
            prompt = f"{current_namespace} ... " 

        try:
            line_input = input(prompt)
            stripped_line_input = line_input.strip()
            lower_stripped_line_input = stripped_line_input.lower()

            if lower_stripped_line_input in ["exit", "quit"]:
                # ... (existing exit logic) ...
                if command_buffer:
                    buffered_content_str = '\n'.join(command_buffer)
                    preview_text = buffered_content_str
                    max_preview_len = 80 
                    if len(preview_text) > max_preview_len:
                        preview_text = preview_text[:max_preview_len - 3] + "..."                     
                    repr_preview_text = repr(preview_text)
                    prompt_message = f"Current command buffer is not empty: {repr_preview_text}. Exit anyway? (y/n): "
                    confirm_exit = input(prompt_message).strip().lower()
                    if confirm_exit != 'y':
                        print("Resuming current command input.")
                        continue 
                print("👋 Goodbye!")
                break 
            
            # Handle LAUNCH NOTEBOOK as a special command
            # This check is simple; a more robust CLI would use argparse or similar for subcommands
            if stripped_line_input.upper().startswith("LAUNCH NOTEBOOK"):
                if command_buffer: # If there's something else in buffer
                    print("⚠️ Please clear or complete current command buffer before launching notebook.")
                    print(f"   Current buffer: {repr(command_buffer)}")
                    continue

                parts = stripped_line_input.split()
                port_to_use = 8888 # Default port
                if len(parts) > 2 and parts[2].upper() == "PORT" and len(parts) > 3:
                    try:
                        port_to_use = int(parts[3])
                    except ValueError:
                        print(f"⚠️ Invalid port number '{parts[3]}'. Using default {port_to_use}.")
                
                launch_notebook_server(port_to_use)
                # After launch_notebook_server returns (i.e., Jupyter server is stopped),
                # we might want to continue the shell or exit. For now, let's continue.
                print("ℹ️ Jupyter server session ended. Resuming KubeSol CLI.")
                continue # Go back to prompt

            command_buffer.append(line_input)
            full_command_text = "\n".join(command_buffer)

            if full_command_text.strip().endswith(";"):
                command_to_execute = full_command_text                 
                if command_to_execute.strip() == ";":
                    print("Empty command.") 
                    command_buffer = [] 
                    continue                 
                execute_command(command_to_execute, namespace=current_namespace)
                command_buffer = []             
            
        except KeyboardInterrupt: 
            if command_buffer:
                print("\nCommand input cancelled. Buffer cleared.")
                command_buffer = [] 
            else: 
                print("\n👋 Goodbye!")
                break
        except EOFError: 
            print("\n👋 Goodbye!")
            break 
        except Exception as e:
            print(f"❌ Unexpected error in shell: {e}")
            command_buffer = [] 

            # Depending on the severity, you might want to break or continue here.
            # For now, it continues, allowing the user to try another command.

def main():
    """
    Main entry point for KubeSol application.
    Initializes Kubernetes client, selects cluster, and starts the shell.
    """
    # 1. Check Kubernetes API client initialization
    try:
        from kubeSol.engine.k8s_api import core_v1_api 
        if core_v1_api is None:
            print("🚨 KubeSol cannot start due to Kubernetes configuration issues.")
            print("   Please ensure your kubeconfig is correctly set up and accessible.")
            exit(1) 
    except ImportError:
        print("🚨 KubeSol critical error: Failed to import Kubernetes API module (kubeSol.engine.k8s_api).")
        print("   Ensure the file exists and there are no circular dependencies.")
        exit(1)
    except Exception as e:
        print(f"🚨 Critical Error during K8s API client initialization check: {e}")
        exit(1) 

    print("ℹ️ Attempting to select a KinD cluster...")
    selected_cluster_name = select_cluster() 

    if selected_cluster_name: 
        print(f"🚀 KubeSol connected to cluster: {selected_cluster_name}")
        shell() 
    else:
        print(" KubeSol exiting as no cluster was selected or available for use.")

if __name__ == "__main__":
    main()