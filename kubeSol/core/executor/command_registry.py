# kubeSol/core/executor/command_registry.py
"""
Command Registry for dynamic command handler composition.

This module provides functionality for registering and dispatching
command handlers from multiple plugins.
"""

from typing import Dict, Tuple, Callable, Optional, List
import logging

logger = logging.getLogger(__name__)

class CommandRegistry:
    """
    Registry for managing command handlers from plugins.
    """
    
    def __init__(self):
        self.handlers: Dict[Tuple[str, str], Callable] = {}
        self.plugin_sources: Dict[Tuple[str, str], str] = {}  # (action, resource) -> plugin_name
    
    def register_handlers(self, plugin_name: str, handlers: Dict[Tuple[str, str], Callable]) -> bool:
        """
        Register command handlers from a plugin.
        
        Args:
            plugin_name: Name of the plugin providing the handlers
            handlers: Dictionary mapping (action, resource_type) tuples to handler functions
            
        Returns:
            True if all handlers were registered successfully, False otherwise
        """
        conflicts = []
        
        for handler_key, handler_func in handlers.items():
            if not isinstance(handler_key, tuple) or len(handler_key) != 2:
                logger.error(f"Invalid handler key from plugin {plugin_name}: {handler_key}")
                continue
            
            action, resource_type = handler_key
            
            if handler_key in self.handlers:
                existing_plugin = self.plugin_sources.get(handler_key, "unknown")
                if existing_plugin != plugin_name:
                    conflicts.append(f"Handler ({action}, {resource_type}) conflicts between {existing_plugin} and {plugin_name}")
                    continue
            
            if not callable(handler_func):
                logger.error(f"Handler for {handler_key} from plugin {plugin_name} is not callable")
                continue
            
            self.handlers[handler_key] = handler_func
            self.plugin_sources[handler_key] = plugin_name
        
        if conflicts:
            logger.error(f"Handler conflicts detected: {conflicts}")
            return False
        
        logger.debug(f"Registered {len(handlers)} command handlers from plugin {plugin_name}")
        return True
    
    def unregister_plugin_handlers(self, plugin_name: str):
        """
        Remove all command handlers provided by a specific plugin.
        
        Args:
            plugin_name: Name of the plugin whose handlers should be removed
        """
        handlers_to_remove = [
            handler_key for handler_key, source_plugin in self.plugin_sources.items()
            if source_plugin == plugin_name
        ]
        
        for handler_key in handlers_to_remove:
            del self.handlers[handler_key]
            del self.plugin_sources[handler_key]
        
        logger.debug(f"Unregistered {len(handlers_to_remove)} command handlers from plugin {plugin_name}")
    
    def get_handler(self, action: str, resource_type: str) -> Optional[Callable]:
        """
        Get the command handler for a specific action and resource type.
        
        Args:
            action: The action (e.g., "CREATE", "DELETE", "EXECUTE")
            resource_type: The resource type (e.g., "SECRET", "SCRIPT", "PROJECT_LOGICAL")
            
        Returns:
            Handler function if found, None otherwise
        """
        handler_key = (action, resource_type)
        return self.handlers.get(handler_key)
    
    def list_supported_commands(self) -> List[Tuple[str, str]]:
        """
        Get list of all supported (action, resource_type) combinations.
        
        Returns:
            List of (action, resource_type) tuples
        """
        return list(self.handlers.keys())
    
    def get_handlers_by_plugin(self, plugin_name: str) -> Dict[Tuple[str, str], Callable]:
        """
        Get all handlers provided by a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary of handlers provided by the plugin
        """
        return {
            handler_key: handler_func
            for handler_key, handler_func in self.handlers.items()
            if self.plugin_sources.get(handler_key) == plugin_name
        }
    
    def get_handler_source(self, action: str, resource_type: str) -> Optional[str]:
        """
        Get the plugin that provides a specific handler.
        
        Args:
            action: The action
            resource_type: The resource type
            
        Returns:
            Plugin name if found, None otherwise
        """
        handler_key = (action, resource_type)
        return self.plugin_sources.get(handler_key)
    
    def has_handler(self, action: str, resource_type: str) -> bool:
        """
        Check if a handler exists for the given action and resource type.
        
        Args:
            action: The action
            resource_type: The resource type
            
        Returns:
            True if handler exists, False otherwise
        """
        handler_key = (action, resource_type)
        return handler_key in self.handlers