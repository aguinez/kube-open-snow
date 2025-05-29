# kubeSol/main.py
from kubeSol.engine.kind_manager import select_cluster 
from kubeSol.engine.executor import execute_command 
from kubeSol.constants import DEFAULT_NAMESPACE

def shell():
    """
    Runs the KubeSol interactive shell.
    Supports multi-line command input. Commands are executed when the
    accumulated input ends with a semicolon (;).
    """
    print("KubeSol - Write SQL-like commands for Kubernetes.")
    print("Enter commands, spanning multiple lines if needed.")
    print("End your complete command with a semicolon (;) to execute.")
    
    current_namespace = DEFAULT_NAMESPACE 
    command_buffer = [] # Stores lines of the current multi-line command

    while True:
        try:
            # Determine the prompt based on whether we are continuing a command
            if not command_buffer:
                prompt = f"{current_namespace} >> "
            else:
                prompt = f"{current_namespace} ... " # Continuation prompt

            line_input = input(prompt)

            # Handle immediate exit/quit commands
            if line_input.strip().lower() in ["exit", "quit"]:
                if command_buffer:
                    # Simple warning if there's an unexecuted command
                    print("⚠️  Exiting. Current unexecuted command in buffer will be lost.")
                print("👋 Goodbye!")
                break # Exit the main shell loop

            # Append the current line to the buffer
            command_buffer.append(line_input)
            full_command_text = "\n".join(command_buffer)

            # Check if the accumulated command (stripped of outer whitespace) ends with a semicolon
            if full_command_text.strip().endswith(";"):
                command_to_execute = full_command_text # Pass the full text with internal newlines
                
                # Handle case where user just types ";"
                if command_to_execute.strip() == ";":
                    # Silently ignore or print a message like "Empty command."
                    # print("Empty command.") 
                    command_buffer = [] # Reset buffer
                    continue # Go to the next prompt

                # print(f"DEBUG: Executing: {repr(command_to_execute)}") # Uncomment for debugging
                execute_command(command_to_execute, namespace=current_namespace)
                command_buffer = [] # Reset buffer for the next command
            # If not ending with a semicolon, the loop continues to the next input()
            # and more lines will be appended to command_buffer.
            
        except KeyboardInterrupt: # Ctrl+C
            if command_buffer:
                print("\nCommand input cancelled. Buffer cleared.")
                command_buffer = [] # Clear any partial command
            else: # If buffer is empty, Ctrl+C means exit the shell
                print("\n👋 Goodbye!")
                break
        except EOFError: # Ctrl+D
            print("\n👋 Goodbye!")
            break # Exit on EOF
        except Exception as e:
            print(f"❌ Unexpected error in shell: {e}")
            # Clear the buffer on an unexpected error to avoid issues with the next command.
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

    # 2. Select a KinD cluster
    print("ℹ️ Attempting to select a KinD cluster...")
    selected_cluster_name = select_cluster() 

    # 3. Proceed to shell or exit
    if selected_cluster_name: 
        print(f"🚀 KubeSol connected to cluster: {selected_cluster_name}")
        shell() 
    else:
        print(" KubeSol exiting as no cluster was selected or available for use.")

if __name__ == "__main__":
    main()