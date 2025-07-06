# kubeSol/plugins/core/__init__.py
"""
KubeSol Core Plugins

Core functionality plugins that provide essential KubeSol features.
"""

from .resource_plugin import ResourcePlugin
from .script_plugin import ScriptPlugin
from .project_plugin import ProjectPlugin

__all__ = ['ResourcePlugin', 'ScriptPlugin', 'ProjectPlugin']