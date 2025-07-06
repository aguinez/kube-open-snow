# kubeSol/core/executor/__init__.py
"""
KubeSol Core Executor Module

Dynamic command execution infrastructure for plugin-based command handling.
"""

from .base_executor import DynamicExecutor
from .command_registry import CommandRegistry

__all__ = ['DynamicExecutor', 'CommandRegistry']