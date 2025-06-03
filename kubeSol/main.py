# kubeSol/main.py
from kubeSol.engine.kind_manager import select_cluster 
from kubeSol.engine.executor import execute_command # execute_command signature expects context
from kubeSol.constants import DEFAULT_NAMESPACE     # Used by KubeSolContext
from kubeSol.projects.context import KubeSolContext # Import the context manager
from kubeSol.notebook.cli import launch_notebook_server # For LAUNCH NOTEBOOK command

def shell(context: KubeSolContext): # Shell now receives the context object
    """
    Runs the KubeSol interactive shell.
    Uses KubeSolContext to manage current project/environment/namespace.
    """
    print("KubeSol - Write SQL-like commands for Kubernetes.")
    print("Enter commands, spanning multiple lines if needed.")
    print("End your complete command with a semicolon (;) to execute.")
    print("Type 'LAUNCH NOTEBOOK' to start a Jupyter Notebook session.")
    print("Type 'USE PROJECT <proj> ENV <env>' to set your working context.")
    print(f"Initial context: {context}") # Display initial context
    
    command_buffer = [] 

    while True:
        # Get prompt from the context object
        if not command_buffer:
            prompt_string = context.get_prompt()
        else:
            prompt_string = context.get_continuation_prompt()

        try:
            line_input = input(prompt_string)
            stripped_line_input = line_input.strip()
            lower_stripped_line_input = stripped_line_input.lower()

            if lower_stripped_line_input in ["exit", "quit"]:
                if command_buffer:
                    print("⚠️ Exiting. Current unexecuted command in buffer will be lost.")
                print("👋 Goodbye!")
                break 
            
            # Handle LAUNCH NOTEBOOK as a special command before general parsing
            # A more robust CLI would parse "LAUNCH NOTEBOOK" as a regular command
            # and dispatch it via the executor to a handler in projects.cli_handlers or similar.
            if stripped_line_input.upper().startswith("LAUNCH NOTEBOOK"):
                if command_buffer: 
                    print("⚠️ Please clear or complete the current command buffer before launching the notebook.")
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
                print("ℹ️ Jupyter server session ended. Resuming KubeSol CLI.")
                continue 

            command_buffer.append(line_input)
            full_command_text = "\n".join(command_buffer)

            if full_command_text.strip().endswith(";"):
                command_to_execute = full_command_text                 
                if command_to_execute.strip() == ";":
                    command_buffer = [] 
                    continue                 
                
                # Pass the context object to execute_command
                # execute_command will then pass this context to project/env handlers,
                # or use context.current_namespace for resource-specific handlers.
                execute_command(command_to_execute, context=context) 
                command_buffer = []             
            
        except KeyboardInterrupt: 
            if command_buffer: print("\nCommand input cancelled. Buffer cleared."); command_buffer = [] 
            else: print("\n👋 Goodbye!"); break
        except EOFError: print("\n👋 Goodbye!"); break 
        except Exception as e:
            print(f"❌ Unexpected error in shell: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc() 
            command_buffer = [] 

def main():
    """
    Main entry point for KubeSol application.
    Initializes Kubernetes client, selects cluster, initializes KubeSolContext, and starts the shell.
    """
    try:
        from kubeSol.engine.k8s_api import core_v1_api 
        if core_v1_api is None:
            print("🚨 KubeSol cannot start due to Kubernetes configuration issues.")
            print("   Please ensure your kubeconfig is correctly set up and accessible.")
            exit(1) 
    except ImportError:
        print("🚨 KubeSol critical error: Failed to import Kubernetes API module (kubeSol.engine.k8s_api).")
        exit(1)
    except Exception as e:
        print(f"🚨 Critical Error during K8s API client initialization check: {e}")
        exit(1) 

    print("ℹ️ Attempting to select a KinD cluster...")
    selected_cluster_name = select_cluster() 

    # Initialize KubeSolContext here
    # This context will be passed to the shell and then to command handlers.
    kubesol_session_context = KubeSolContext()

    if selected_cluster_name: 
        print(f"🚀 KubeSol connected to cluster: {selected_cluster_name}")
        # The KubeSolContext starts with DEFAULT_NAMESPACE.
        # The user can then use "USE PROJECT ... ENV ..." to change it.
        shell(kubesol_session_context) # Pass context to shell
    else:
        print(" KubeSol exiting as no cluster was selected or available for use.")

if __name__ == "__main__":
    main()