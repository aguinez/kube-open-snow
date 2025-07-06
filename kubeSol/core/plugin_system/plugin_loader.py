# kubeSol/core/plugin_system/plugin_loader.py
"""
Plugin loading utilities for the KubeSol plugin system.

This module provides functionality for dynamically discovering and loading
plugins from various sources.
"""

import os
import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import List, Type, Dict, Any, Optional
import logging

from .plugin_interface import KubeSolPlugin

logger = logging.getLogger(__name__)

class PluginLoader:
    """
    Handles dynamic loading of plugins from various sources.
    """
    
    def __init__(self):
        self.loaded_modules: Dict[str, Any] = {}
    
    def discover_plugins_in_directory(self, directory: str) -> List[Type[KubeSolPlugin]]:
        """
        Discover all plugins in a given directory.
        
        Args:
            directory: Path to directory to search for plugins
            
        Returns:
            List of plugin classes found
        """
        plugins = []
        directory_path = Path(directory)
        
        if not directory_path.exists() or not directory_path.is_dir():
            logger.warning(f"Plugin directory {directory} does not exist or is not a directory")
            return plugins
        
        for file_path in directory_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
                
            try:
                plugin_classes = self.load_plugin_from_file(str(file_path))
                plugins.extend(plugin_classes)
            except Exception as e:
                logger.error(f"Failed to load plugin from {file_path}: {e}")
        
        return plugins
    
    def load_plugin_from_file(self, file_path: str) -> List[Type[KubeSolPlugin]]:
        """
        Load plugin classes from a Python file.
        
        Args:
            file_path: Path to the Python file containing plugin classes
            
        Returns:
            List of plugin classes found in the file
        """
        plugins = []
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Plugin file {file_path} not found")
        
        module_name = file_path_obj.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module spec from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Store reference to avoid garbage collection
        self.loaded_modules[module_name] = module
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise ImportError(f"Failed to execute module {module_name}: {e}")
        
        # Find all plugin classes in the module
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, KubeSolPlugin) and 
                obj != KubeSolPlugin and
                not inspect.isabstract(obj)):
                plugins.append(obj)
                logger.debug(f"Found plugin class {name} in {file_path}")
        
        return plugins
    
    def load_plugin_from_module(self, module_name: str) -> List[Type[KubeSolPlugin]]:
        """
        Load plugin classes from an importable module.
        
        Args:
            module_name: Name of the module to import (e.g., 'kubeSol.plugins.core.script_plugin')
            
        Returns:
            List of plugin classes found in the module
        """
        plugins = []
        
        try:
            module = importlib.import_module(module_name)
            self.loaded_modules[module_name] = module
        except ImportError as e:
            raise ImportError(f"Failed to import module {module_name}: {e}")
        
        # Find all plugin classes in the module
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, KubeSolPlugin) and 
                obj != KubeSolPlugin and
                not inspect.isabstract(obj)):
                plugins.append(obj)
                logger.debug(f"Found plugin class {name} in module {module_name}")
        
        return plugins
    
    def validate_plugin_class(self, plugin_class: Type[KubeSolPlugin]) -> bool:
        """
        Validate that a plugin class properly implements the required interface.
        
        Args:
            plugin_class: The plugin class to validate
            
        Returns:
            True if the plugin class is valid, False otherwise
        """
        try:
            # Check if all abstract methods are implemented
            if inspect.isabstract(plugin_class):
                logger.error(f"Plugin class {plugin_class.__name__} has unimplemented abstract methods")
                return False
            
            # Try to instantiate the plugin to check for basic errors
            try:
                plugin_instance = plugin_class()
                
                # Check required methods exist and are callable
                required_methods = ['metadata', 'get_grammar_rules', 'get_command_handlers', 'get_constants']
                for method_name in required_methods:
                    if not hasattr(plugin_instance, method_name):
                        logger.error(f"Plugin class {plugin_class.__name__} missing required method {method_name}")
                        return False
                    
                    method = getattr(plugin_instance, method_name)
                    if not callable(method) and method_name != 'metadata':
                        logger.error(f"Plugin class {plugin_class.__name__} method {method_name} is not callable")
                        return False
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to instantiate plugin class {plugin_class.__name__}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error validating plugin class {plugin_class.__name__}: {e}")
            return False
    
    def get_plugin_dependencies(self, plugin_class: Type[KubeSolPlugin]) -> List[str]:
        """
        Get the dependencies for a plugin class.
        
        Args:
            plugin_class: The plugin class to check
            
        Returns:
            List of dependency names
        """
        try:
            plugin_instance = plugin_class()
            return plugin_instance.metadata.dependencies
        except Exception as e:
            logger.error(f"Failed to get dependencies for plugin {plugin_class.__name__}: {e}")
            return []