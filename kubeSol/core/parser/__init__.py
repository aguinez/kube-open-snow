# kubeSol/core/parser/__init__.py
"""
KubeSol Core Parser Module

Dynamic parsing infrastructure for plugin-based grammar composition.
"""

from .base_parser import DynamicKubeSolParser
from .grammar_registry import GrammarRegistry

__all__ = ['DynamicKubeSolParser', 'GrammarRegistry']