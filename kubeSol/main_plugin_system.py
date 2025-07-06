# kubeSol/main_plugin_system.py
"""
KubeSol Main Entry Point with Plugin System

This is the new main entry point that uses the plugin-based architecture.
It initializes the plugin system, loads core plugins, and starts the shell.
"""

import logging
import sys
from pathlib import Path

# Import the new plugin-based components
from kubeSol.core.plugin_system.plugin_manager import PluginManager
from kubeSol.core.executor.base_executor import DynamicExecutor
from kubeSol.core.context import KubeSolContext

# Import core plugins
from kubeSol.plugins.core.resource_plugin import ResourcePlugin
from kubeSol.plugins.core.script_plugin import ScriptPlugin
from kubeSol.plugins.core.project_plugin import ProjectPlugin

# Keep some imports from the old system for now
from kubeSol.engine.kind_manager import select_cluster

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_plugin_system() -> tuple[PluginManager, DynamicExecutor]:
    """
    Initialize the plugin system with core plugins.
    
    Returns:
        Tuple of (PluginManager, DynamicExecutor)
    """
    logger.info("Initializing KubeSol plugin system...")
    
    # Create plugin manager
    plugin_manager = PluginManager()
    
    # Register core plugin classes
    core_plugins = [
        ResourcePlugin,
        ScriptPlugin, 
        ProjectPlugin
    ]
    
    registered_count = 0
    for plugin_class in core_plugins:
        if plugin_manager.register_plugin_class(plugin_class):
            registered_count += 1
        else:
            logger.error(f"Failed to register plugin class: {plugin_class.__name__}")
    
    logger.info(f"Registered {registered_count} core plugin classes")
    
    # Load all registered plugins
    successful, failed = plugin_manager.load_all_plugins()
    logger.info(f"Loaded plugins: {successful} successful, {failed} failed")
    
    if successful == 0:
        logger.error("No plugins loaded successfully")
        return None, None
    
    # Create dynamic executor
    executor = DynamicExecutor(plugin_manager)
    
    logger.info("Plugin system initialized successfully")
    return plugin_manager, executor

def shell(executor: DynamicExecutor, context: KubeSolContext):
    """
    Runs the KubeSol interactive shell with the plugin system.
    
    Args:
        executor: Dynamic executor for handling commands
        context: KubeSol context for session management
    """
    print("🚀 KubeSol - Plugin-Based Architecture")
    print("Write SQL-like commands for Kubernetes.")
    print("Enter commands, spanning multiple lines if needed.")
    print("End your complete command with a semicolon (;) to execute.")
    print("Type 'LAUNCH NOTEBOOK' to start a Jupyter Notebook session.")
    print("Type 'USE PROJECT <proj> ENV <env>' to set your working context.")
    print(f"Initial context: {context}")
    print()
    
    # Show loaded plugins
    try:
        executor_info = executor.get_executor_info()
        if "loaded_plugins" in executor_info:
            loaded_plugins = executor_info["loaded_plugins"]
            print(f"📦 Loaded plugins: {', '.join(loaded_plugins)}")
            print(f"💡 Available commands: {executor_info.get('supported_commands', 0)}")
            print()
    except Exception as e:
        logger.warning(f"Could not get executor info: {e}")
    
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
            
            # Handle exit commands
            if lower_stripped_line_input in ["exit", "quit"]:
                if command_buffer:
                    print("⚠️ Exiting. Current unexecuted command in buffer will be lost.")
                print("👋 Goodbye!")
                break
            
            # Handle special commands
            if stripped_line_input.upper().startswith("LAUNCH NOTEBOOK"):
                if command_buffer:
                    print("⚠️ Please clear or complete the current command buffer before launching the notebook.")
                    print(f"   Current buffer: {repr(command_buffer)}")
                    continue
                
                # Handle notebook launch
                from kubeSol.notebook.cli import launch_notebook_server
                parts = stripped_line_input.split()
                port_to_use = 8888  # Default port
                if len(parts) > 2 and parts[2].upper() == "PORT" and len(parts) > 3:
                    try:
                        port_to_use = int(parts[3])
                    except ValueError:
                        print(f"⚠️ Invalid port number '{parts[3]}'. Using default {port_to_use}.")
                
                launch_notebook_server(port_to_use)
                print("ℹ️ Jupyter server session ended. Resuming KubeSol CLI.")
                continue
            
            # Handle debug commands
            if stripped_line_input.upper().startswith("DEBUG"):
                if len(stripped_line_input.split()) > 1:
                    debug_command = " ".join(stripped_line_input.split()[1:])
                    debug_info = executor.debug_command(debug_command)
                    print("🔍 Debug Information:")
                    for key, value in debug_info.items():
                        print(f"   {key}: {value}")
                else:
                    executor_info = executor.get_executor_info()
                    print("🔍 Executor Information:")
                    for key, value in executor_info.items():
                        print(f"   {key}: {value}")
                continue
            
            # Handle help commands
            if lower_stripped_line_input in ["help", "?"]:
                show_help(executor)
                continue
            
            # Add line to command buffer
            command_buffer.append(line_input)
            full_command_text = "\n".join(command_buffer)
            
            # Check if command is complete (ends with semicolon)
            if full_command_text.strip().endswith(";"):
                command_to_execute = full_command_text
                
                if command_to_execute.strip() == ";":
                    command_buffer = []
                    continue
                
                # Execute the command using the dynamic executor
                try:
                    success = executor.execute_command(command_to_execute, context)
                    if not success:
                        logger.debug(f"Command execution returned False: {command_to_execute}")
                except Exception as e:
                    print(f"❌ Error executing command: {e}")
                    logger.error(f"Error executing command '{command_to_execute}': {e}")
                
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
            print(f"❌ Unexpected error in shell: {type(e).__name__} - {e}")
            logger.error(f"Unexpected error in shell: {e}")
            command_buffer = []

def show_help(executor: DynamicExecutor):
    """Show help information"""
    print("📚 KubeSol Help")
    print("=" * 50)
    print()
    
    try:
        supported_commands = executor.get_supported_commands()
        if supported_commands:
            print("Available Commands:")
            for cmd in sorted(supported_commands):
                print(f"   {cmd}")
        else:
            print("No commands available (plugin system issue)")
    except Exception as e:
        print(f"Could not retrieve command list: {e}")
    
    print()
    print("Special Commands:")
    print("   help, ?          - Show this help")
    print("   debug [command]  - Debug command parsing")
    print("   exit, quit       - Exit KubeSol")
    print("   LAUNCH NOTEBOOK  - Start Jupyter Notebook")
    print()
    print("Examples:")
    print("   CREATE PROJECT myproject;")
    print("   CREATE ENV staging DEPENDS ON dev;")
    print("   CREATE SECRET mysecret WITH key1=\"value1\";")
    print("   LIST PROJECTS;")
    print("   USE PROJECT myproject ENV dev;")

def main():
    """
    Main entry point for KubeSol with plugin system.
    """
    try:
        # Check Kubernetes connectivity using existing functionality
        from kubeSol.engine.k8s_api import core_v1_api
        if core_v1_api is None:
            print("🚨 KubeSol cannot start due to Kubernetes configuration issues.")
            print("   Please ensure your kubeconfig is correctly set up and accessible.")
            sys.exit(1)
    except ImportError:
        print("🚨 KubeSol critical error: Failed to import Kubernetes API module.")
        sys.exit(1)
    except Exception as e:
        print(f"🚨 Critical Error during K8s API client initialization check: {e}")
        sys.exit(1)
    
    # Select cluster using existing functionality
    print("ℹ️ Attempting to select a KinD cluster...")
    selected_cluster_name = select_cluster()
    
    if not selected_cluster_name:
        print("❌ KubeSol exiting as no cluster was selected or available for use.")
        sys.exit(1)
    
    print(f"🚀 KubeSol connected to cluster: {selected_cluster_name}")
    
    # Initialize plugin system
    plugin_manager, executor = initialize_plugin_system()
    
    if not plugin_manager or not executor:
        print("🚨 Failed to initialize plugin system. Exiting.")
        sys.exit(1)
    
    # Initialize context
    kubesol_session_context = KubeSolContext(default_namespace="default")
    
    # Start the shell
    try:
        shell(executor, kubesol_session_context)
    except Exception as e:
        logger.error(f"Fatal error in shell: {e}")
        print(f"🚨 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()