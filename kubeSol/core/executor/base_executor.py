# kubeSol/core/executor/base_executor.py
"""
Dynamic KubeSol Executor

This module provides a dynamic executor that can dispatch commands
to handlers provided by plugins based on parsed command data.
"""

from typing import Dict, Any, Optional, List
import logging

from .command_registry import CommandRegistry
from kubeSol.core.plugin_system.plugin_manager import PluginManager
from kubeSol.core.parser.base_parser import DynamicKubeSolParser
from kubeSol.core.context import KubeSolContext

logger = logging.getLogger(__name__)

class DynamicExecutor:
    """
    Dynamic executor for KubeSol commands.
    
    Parses commands using the dynamic parser and dispatches them
    to appropriate plugin handlers.
    """
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self.command_registry = CommandRegistry()
        self.parser = DynamicKubeSolParser(plugin_manager)
        self._last_plugin_count = 0
        
        # Initialize with current plugins
        self._rebuild_registries()
    
    def _rebuild_registries(self) -> bool:
        """
        Rebuild command registry with handlers from all loaded plugins.
        
        Returns:
            True if rebuild was successful, False otherwise
        """
        try:
            # Clear existing handlers
            self.command_registry = CommandRegistry()
            
            # Register handlers from all loaded plugins
            for plugin_name in self.plugin_manager.get_loaded_plugins():
                plugin = self.plugin_manager.plugins[plugin_name]
                command_handlers = plugin.get_command_handlers()
                
                if not self.command_registry.register_handlers(plugin_name, command_handlers):
                    logger.error(f"Failed to register command handlers from plugin {plugin_name}")
                    return False
            
            # Rebuild parser as well
            if not self.parser.rebuild_parser():
                logger.error("Failed to rebuild parser")
                return False
            
            self._last_plugin_count = len(self.plugin_manager.get_loaded_plugins())
            logger.info(f"Command registry rebuilt successfully with {self._last_plugin_count} plugins")
            return True
            
        except Exception as e:
            logger.error(f"Error rebuilding command registry: {e}")
            return False
    
    def _ensure_registries_current(self) -> bool:
        """Ensure registries are up-to-date with loaded plugins"""
        current_plugin_count = len(self.plugin_manager.get_loaded_plugins())
        
        if current_plugin_count != self._last_plugin_count:
            return self._rebuild_registries()
        
        return True
    
    def execute_command(self, command_string: str, context: KubeSolContext) -> bool:
        """
        Execute a KubeSol command.
        
        Args:
            command_string: The command string to execute
            context: Current KubeSol context
            
        Returns:
            True if command executed successfully, False otherwise
        """
        if not command_string or not command_string.strip():
            print("❌ Empty command provided.")
            return False
        
        # Ensure registries are current
        if not self._ensure_registries_current():
            print("❌ System error: Command registry initialization failed.")
            return False
        
        try:
            # Parse the command
            parsed_result = self.parser.parse(command_string)
            
            # Check for parse errors
            if "error" in parsed_result:
                error_type = parsed_result.get("type", "unknown")
                error_msg = parsed_result.get("error", "Unknown error")
                
                if error_type == "parse_error":
                    print(f"❌ Syntax error: {error_msg}")
                    self._suggest_similar_commands(command_string)
                elif error_type == "lex_error":
                    print(f"❌ Invalid command format: {error_msg}")
                else:
                    print(f"❌ Command error: {error_msg}")
                
                return False
            
            # Execute the parsed command
            return self._execute_parsed_command(parsed_result, context)
            
        except Exception as e:
            logger.error(f"Unexpected error executing command '{command_string}': {e}")
            print(f"❌ Unexpected error: {e}")
            return False
    
    def _execute_parsed_command(self, parsed_command: Dict[str, Any], context: KubeSolContext) -> bool:
        """
        Execute a parsed command by dispatching to the appropriate handler.
        
        Args:
            parsed_command: The parsed command data
            context: Current KubeSol context
            
        Returns:
            True if command executed successfully, False otherwise
        """
        action = parsed_command.get("action")
        resource_type = parsed_command.get("type")
        
        if not action or not resource_type:
            print(f"❌ Invalid command structure: missing action or type")
            logger.debug(f"Parsed command: {parsed_command}")
            return False
        
        # Find the appropriate handler
        handler = self.command_registry.get_handler(action, resource_type)
        
        if not handler:
            print(f"❌ No handler found for command: {action} {resource_type}")
            self._suggest_available_commands(action, resource_type)
            return False
        
        try:
            # Execute the handler
            logger.debug(f"Executing {action} {resource_type} with handler from {self.command_registry.get_handler_source(action, resource_type)}")
            
            # Call the handler with parsed arguments and context
            handler(parsed_command, context)
            return True
            
        except Exception as e:
            logger.error(f"Error executing handler for {action} {resource_type}: {e}")
            print(f"❌ Error executing command: {e}")
            return False
    
    def _suggest_similar_commands(self, command_string: str):
        """Suggest similar commands when parse fails"""
        # Simple suggestion based on first word
        first_word = command_string.strip().split()[0].upper() if command_string.strip() else ""
        
        similar_commands = []
        for action, resource_type in self.command_registry.list_supported_commands():
            if action.startswith(first_word) or first_word in action:
                similar_commands.append(f"{action} {resource_type}")
        
        if similar_commands:
            print("💡 Did you mean one of these?")
            for cmd in similar_commands[:5]:  # Show up to 5 suggestions
                print(f"   {cmd}")
    
    def _suggest_available_commands(self, action: str, resource_type: str):
        """Suggest available commands when no handler is found"""
        # Suggest commands with same action
        same_action = [
            (a, rt) for a, rt in self.command_registry.list_supported_commands()
            if a == action
        ]
        
        # Suggest commands with same resource type
        same_resource = [
            (a, rt) for a, rt in self.command_registry.list_supported_commands()
            if rt == resource_type
        ]
        
        if same_action:
            print(f"💡 Available {action} commands:")
            for a, rt in same_action:
                print(f"   {a} {rt}")
        
        if same_resource:
            print(f"💡 Available commands for {resource_type}:")
            for a, rt in same_resource:
                print(f"   {a} {rt}")
        
        if not same_action and not same_resource:
            print("💡 Available commands:")
            for a, rt in self.command_registry.list_supported_commands()[:10]:  # Show first 10
                print(f"   {a} {rt}")
    
    def get_supported_commands(self) -> List[str]:
        """
        Get list of all supported commands.
        
        Returns:
            List of supported command strings
        """
        if not self._ensure_registries_current():
            return []
        
        commands = []
        for action, resource_type in self.command_registry.list_supported_commands():
            commands.append(f"{action} {resource_type}")
        
        return sorted(commands)
    
    def validate_command(self, command_string: str) -> Dict[str, Any]:
        """
        Validate a command without executing it.
        
        Args:
            command_string: The command string to validate
            
        Returns:
            Dictionary with validation results
        """
        if not self._ensure_registries_current():
            return {"valid": False, "error": "System not ready"}
        
        # Parse the command
        parsed_result = self.parser.parse(command_string)
        
        if "error" in parsed_result:
            return {
                "valid": False,
                "error": parsed_result.get("error"),
                "error_type": parsed_result.get("type")
            }
        
        # Check if handler exists
        action = parsed_result.get("action")
        resource_type = parsed_result.get("type")
        
        if not action or not resource_type:
            return {
                "valid": False,
                "error": "Invalid command structure",
                "parsed": parsed_result
            }
        
        handler = self.command_registry.get_handler(action, resource_type)
        
        if not handler:
            return {
                "valid": False,
                "error": f"No handler for {action} {resource_type}",
                "action": action,
                "resource_type": resource_type
            }
        
        return {
            "valid": True,
            "action": action,
            "resource_type": resource_type,
            "handler_plugin": self.command_registry.get_handler_source(action, resource_type),
            "parsed": parsed_result
        }
    
    def get_executor_info(self) -> Dict[str, Any]:
        """
        Get information about the current executor state.
        
        Returns:
            Dictionary with executor information
        """
        if not self._ensure_registries_current():
            return {"error": "Registries not available"}
        
        return {
            "loaded_plugins": self.plugin_manager.get_loaded_plugins(),
            "supported_commands": len(self.command_registry.list_supported_commands()),
            "parser_info": self.parser.get_grammar_info(),
            "handlers_by_plugin": {
                plugin_name: len(self.command_registry.get_handlers_by_plugin(plugin_name))
                for plugin_name in self.plugin_manager.get_loaded_plugins()
            }
        }
    
    def debug_command(self, command_string: str) -> Dict[str, Any]:
        """
        Debug a command by showing detailed parsing and execution information.
        
        Args:
            command_string: The command string to debug
            
        Returns:
            Dictionary with debug information
        """
        debug_info = {
            "command": command_string,
            "registries_current": self._ensure_registries_current()
        }
        
        if not debug_info["registries_current"]:
            debug_info["error"] = "Registries not current"
            return debug_info
        
        # Parse the command
        parsed_result = self.parser.parse(command_string)
        debug_info["parsed_result"] = parsed_result
        
        if "error" not in parsed_result:
            action = parsed_result.get("action")
            resource_type = parsed_result.get("type")
            
            debug_info["action"] = action
            debug_info["resource_type"] = resource_type
            
            if action and resource_type:
                handler = self.command_registry.get_handler(action, resource_type)
                debug_info["handler_found"] = handler is not None
                
                if handler:
                    debug_info["handler_plugin"] = self.command_registry.get_handler_source(action, resource_type)
                    debug_info["handler_function"] = str(handler)
        
        return debug_info