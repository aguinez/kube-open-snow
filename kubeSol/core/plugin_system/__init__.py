# kubeSol/core/plugin_system/__init__.py
"""
KubeSol Plugin System

Provides the infrastructure for dynamic plugin loading and management.
"""

from .plugin_interface import KubeSolPlugin, ResourcePlugin, ProjectPlugin, OrchestrationPlugin
from .plugin_manager import PluginManager
from .plugin_loader import PluginLoader

__all__ = [
    'KubeSolPlugin',
    'ResourcePlugin', 
    'ProjectPlugin',
    'OrchestrationPlugin',
    'PluginManager',
    'PluginLoader'
]