# kubeSol/core/plugin_system/plugin_manager.py
"""
Plugin management system for KubeSol.

This module provides the central PluginManager class that handles plugin
discovery, loading, lifecycle management, and provides unified access
to plugin-provided functionality.
"""

import logging
from typing import Dict, List, Any, Optional, Callable, Tuple, Type, Set
from collections import defaultdict

from .plugin_interface import KubeSolPlugin, PluginMetadata
from .plugin_loader import PluginLoader

logger = logging.getLogger(__name__)

class PluginDependencyError(Exception):
    """Raised when plugin dependencies cannot be resolved."""
    pass

class PluginManager:
    """
    Central manager for the KubeSol plugin system.
    
    Handles plugin discovery, loading, dependency resolution, and provides
    unified access to plugin functionality.
    """
    
    def __init__(self):
        self.plugins: Dict[str, KubeSolPlugin] = {}
        self.plugin_classes: Dict[str, Type[KubeSolPlugin]] = {}
        self.loader = PluginLoader()
        
        # Cached aggregated data from all plugins
        self.grammar_rules: Dict[str, str] = {}
        self.command_handlers: Dict[Tuple[str, str], Callable] = {}
        self.constants: Dict[str, Any] = {}
        self.transformer_methods: Dict[str, Callable] = {}
        
        # Plugin metadata
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # Cache validity
        self._cache_valid = False
    
    def discover_plugins(self, plugin_directories: List[str]) -> int:
        """
        Discover plugins in specified directories.
        
        Args:
            plugin_directories: List of directory paths to search for plugins
            
        Returns:
            Number of plugin classes discovered
        """
        discovered_count = 0
        
        for directory in plugin_directories:
            try:
                plugin_classes = self.loader.discover_plugins_in_directory(directory)
                for plugin_class in plugin_classes:
                    if self.loader.validate_plugin_class(plugin_class):
                        plugin_name = plugin_class.__name__
                        self.plugin_classes[plugin_name] = plugin_class
                        discovered_count += 1
                        logger.info(f"Discovered plugin: {plugin_name}")
                    else:
                        logger.warning(f"Invalid plugin class: {plugin_class.__name__}")
            except Exception as e:
                logger.error(f"Error discovering plugins in {directory}: {e}")
        
        return discovered_count
    
    def load_plugin_from_module(self, module_name: str) -> int:
        """
        Load plugins from a specific module.
        
        Args:
            module_name: Module name to load plugins from
            
        Returns:
            Number of plugins loaded
        """
        loaded_count = 0
        
        try:
            plugin_classes = self.loader.load_plugin_from_module(module_name)
            for plugin_class in plugin_classes:
                if self.loader.validate_plugin_class(plugin_class):
                    plugin_name = plugin_class.__name__
                    self.plugin_classes[plugin_name] = plugin_class
                    loaded_count += 1
                    logger.info(f"Loaded plugin class: {plugin_name}")
                else:
                    logger.warning(f"Invalid plugin class: {plugin_class.__name__}")
        except Exception as e:
            logger.error(f"Error loading plugins from module {module_name}: {e}")
        
        return loaded_count
    
    def register_plugin_class(self, plugin_class: Type[KubeSolPlugin]) -> bool:
        """
        Register a plugin class directly.
        
        Args:
            plugin_class: The plugin class to register
            
        Returns:
            True if successfully registered, False otherwise
        """
        if not self.loader.validate_plugin_class(plugin_class):
            logger.error(f"Invalid plugin class: {plugin_class.__name__}")
            return False
        
        plugin_name = plugin_class.__name__
        self.plugin_classes[plugin_name] = plugin_class
        logger.info(f"Registered plugin class: {plugin_name}")
        return True
    
    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load and initialize a single plugin by name.
        
        Args:
            plugin_name: Name of the plugin class to load
            
        Returns:
            True if successfully loaded, False otherwise
        """
        if plugin_name in self.plugins:
            logger.warning(f"Plugin {plugin_name} is already loaded")
            return True
        
        if plugin_name not in self.plugin_classes:
            logger.error(f"Plugin class {plugin_name} not found")
            return False
        
        try:
            plugin_class = self.plugin_classes[plugin_name]
            plugin_instance = plugin_class()
            
            # Store metadata and check dependencies
            self.plugin_metadata[plugin_name] = plugin_instance.metadata
            dependencies = plugin_instance.metadata.dependencies
            
            # Check if dependencies are loaded
            for dep in dependencies:
                if dep not in self.plugins:
                    logger.error(f"Plugin {plugin_name} requires dependency {dep} which is not loaded")
                    return False
            
            # Initialize the plugin
            if not plugin_instance.initialize():
                logger.error(f"Failed to initialize plugin {plugin_name}")
                return False
            
            # Store the plugin instance
            self.plugins[plugin_name] = plugin_instance
            
            # Update dependency graph
            self.dependency_graph[plugin_name].update(dependencies)
            
            # Invalidate cache
            self._cache_valid = False
            
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin and clean up its resources.
        
        Args:
            plugin_name: Name of the plugin to unload
            
        Returns:
            True if successfully unloaded, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} is not loaded")
            return True
        
        try:
            # Check if other plugins depend on this one
            dependents = [name for name, deps in self.dependency_graph.items() 
                         if plugin_name in deps and name in self.plugins]
            
            if dependents:
                logger.error(f"Cannot unload plugin {plugin_name}: required by {dependents}")
                return False
            
            # Cleanup the plugin
            plugin = self.plugins[plugin_name]
            if not plugin.cleanup():
                logger.warning(f"Plugin {plugin_name} cleanup returned False")
            
            # Remove from loaded plugins
            del self.plugins[plugin_name]
            del self.plugin_metadata[plugin_name]
            if plugin_name in self.dependency_graph:
                del self.dependency_graph[plugin_name]
            
            # Invalidate cache
            self._cache_valid = False
            
            logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self) -> Tuple[int, int]:
        """
        Load all discovered plugin classes.
        
        Returns:
            Tuple of (successful_loads, failed_loads)
        """
        # Resolve dependencies and determine load order
        load_order = self._resolve_load_order()
        
        successful = 0
        failed = 0
        
        for plugin_name in load_order:
            if self.load_plugin(plugin_name):
                successful += 1
            else:
                failed += 1
        
        return successful, failed
    
    def _resolve_load_order(self) -> List[str]:
        """
        Resolve plugin dependencies and return load order.
        
        Returns:
            List of plugin names in dependency order
            
        Raises:
            PluginDependencyError: If circular dependencies are detected
        """
        # Build dependency graph from plugin classes
        temp_deps: Dict[str, Set[str]] = defaultdict(set)
        
        for plugin_name, plugin_class in self.plugin_classes.items():
            dependencies = self.loader.get_plugin_dependencies(plugin_class)
            temp_deps[plugin_name].update(dependencies)
        
        # Topological sort
        visited = set()
        temp_visited = set()
        load_order = []
        
        def visit(plugin_name: str):
            if plugin_name in temp_visited:
                raise PluginDependencyError(f"Circular dependency detected involving {plugin_name}")
            
            if plugin_name in visited:
                return
            
            temp_visited.add(plugin_name)
            
            for dep in temp_deps[plugin_name]:
                if dep not in self.plugin_classes:
                    raise PluginDependencyError(f"Plugin {plugin_name} depends on {dep} which is not available")
                visit(dep)
            
            temp_visited.remove(plugin_name)
            visited.add(plugin_name)
            load_order.append(plugin_name)
        
        for plugin_name in self.plugin_classes:
            if plugin_name not in visited:
                visit(plugin_name)
        
        return load_order
    
    def _rebuild_cache(self):
        """Rebuild the aggregated cache from all loaded plugins."""
        if self._cache_valid:
            return
        
        # Clear existing cache
        self.grammar_rules.clear()
        self.command_handlers.clear()
        self.constants.clear()
        self.transformer_methods.clear()
        
        # Aggregate from all loaded plugins
        for plugin_name, plugin in self.plugins.items():
            try:
                # Merge grammar rules
                plugin_grammar = plugin.get_grammar_rules()
                for rule_name, rule_def in plugin_grammar.items():
                    if rule_name in self.grammar_rules:
                        logger.warning(f"Grammar rule {rule_name} from plugin {plugin_name} conflicts with existing rule")
                    self.grammar_rules[rule_name] = rule_def
                
                # Merge command handlers
                plugin_handlers = plugin.get_command_handlers()
                for handler_key, handler_func in plugin_handlers.items():
                    if handler_key in self.command_handlers:
                        logger.warning(f"Command handler {handler_key} from plugin {plugin_name} conflicts with existing handler")
                    self.command_handlers[handler_key] = handler_func
                
                # Merge constants
                plugin_constants = plugin.get_constants()
                for const_name, const_value in plugin_constants.items():
                    if const_name in self.constants:
                        logger.warning(f"Constant {const_name} from plugin {plugin_name} conflicts with existing constant")
                    self.constants[const_name] = const_value
                
                # Merge transformer methods
                plugin_transformers = plugin.get_transformer_methods()
                for transformer_name, transformer_func in plugin_transformers.items():
                    if transformer_name in self.transformer_methods:
                        logger.warning(f"Transformer {transformer_name} from plugin {plugin_name} conflicts with existing transformer")
                    self.transformer_methods[transformer_name] = transformer_func
                
            except Exception as e:
                logger.error(f"Error aggregating data from plugin {plugin_name}: {e}")
        
        self._cache_valid = True
    
    def get_combined_grammar(self) -> str:
        """
        Get the combined grammar from all loaded plugins.
        
        Returns:
            Combined Lark grammar string
        """
        self._rebuild_cache()
        
        if not self.grammar_rules:
            return ""
        
        # Build the complete grammar
        grammar_parts = [
            "?start: command [\";\"]\n",
            "command: " + " | ".join(self.grammar_rules.keys()) + "\n"
        ]
        
        # Add all rule definitions
        for rule_name, rule_def in self.grammar_rules.items():
            grammar_parts.append(f"{rule_name}: {rule_def}")
        
        # Add common terminals and imports
        grammar_parts.extend([
            "NAME: /[a-zA-Z0-9]([a-zA-Z0-9_.-]*[a-zA-Z0-9_])?|[a-zA-Z0-9]/",
            "%import common.ESCAPED_STRING",
            "%import common.WS",
            "%ignore WS"
        ])
        
        return "\n".join(grammar_parts)
    
    def get_command_handler(self, action: str, resource_type: str) -> Optional[Callable]:
        """
        Get the command handler for a specific action and resource type.
        
        Args:
            action: The action (e.g., "CREATE", "DELETE")
            resource_type: The resource type (e.g., "SECRET", "PROJECT")
            
        Returns:
            Handler function if found, None otherwise
        """
        self._rebuild_cache()
        return self.command_handlers.get((action, resource_type))
    
    def get_all_constants(self) -> Dict[str, Any]:
        """
        Get all constants from loaded plugins.
        
        Returns:
            Dictionary of all constants
        """
        self._rebuild_cache()
        return self.constants.copy()
    
    def get_transformer_methods(self) -> Dict[str, Callable]:
        """
        Get all transformer methods from loaded plugins.
        
        Returns:
            Dictionary of transformer methods
        """
        self._rebuild_cache()
        return self.transformer_methods.copy()
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names."""
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get metadata for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin metadata if found, None otherwise
        """
        return self.plugin_metadata.get(plugin_name)
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is loaded."""
        return plugin_name in self.plugins