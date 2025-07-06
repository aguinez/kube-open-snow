# kubeSol/core/parser/base_parser.py
"""
Dynamic KubeSol Parser

This module provides a dynamic parser that can compose grammar rules
from multiple plugins and parse commands using the unified grammar.
"""

from typing import Dict, Any, Optional, Callable, List
import logging
from lark import Lark, Transformer, Tree, Token
from lark.exceptions import LarkError, ParseError, LexError

from .grammar_registry import GrammarRegistry
from kubeSol.core.plugin_system.plugin_manager import PluginManager

logger = logging.getLogger(__name__)

class DynamicTransformer(Transformer):
    """
    Dynamic transformer that delegates transformation to plugin-provided methods.
    """
    
    def __init__(self, plugin_manager: PluginManager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self._transformer_methods: Dict[str, Callable] = {}
        self._rebuild_transformers()
    
    def _rebuild_transformers(self):
        """Rebuild transformer methods from loaded plugins"""
        self._transformer_methods = self.plugin_manager.get_transformer_methods()
        
        # Dynamically add transformer methods to this instance
        for method_name, method_func in self._transformer_methods.items():
            # Check if it's a lambda (terminal transformer) or method (rule transformer)
            if hasattr(method_func, '__name__') and method_func.__name__ == '<lambda>':
                # For lambda functions (terminal transformers), don't pass self
                bound_method = lambda *args, func=method_func, **kwargs: func(*args, **kwargs)
            else:
                # For methods (rule transformers), pass self and children
                bound_method = lambda *args, func=method_func, **kwargs: func(self, *args, **kwargs)
            setattr(self, method_name, bound_method)
    
    def __default__(self, data, children, meta):
        """Default handler for rules without specific transformers"""
        # Try to find a transformer method for this rule
        rule_name = data
        
        if rule_name in self._transformer_methods:
            transformer_func = self._transformer_methods[rule_name]
            try:
                # Check if it's a lambda (terminal transformer) or method (rule transformer)
                if hasattr(transformer_func, '__name__') and transformer_func.__name__ == '<lambda>':
                    return transformer_func(*children)
                else:
                    return transformer_func(self, *children)
            except Exception as e:
                logger.error(f"Error in transformer {rule_name}: {e}")
                return {"error": f"Transform error in {rule_name}", "children": children}
        
        # Default behavior - return as-is or simplify
        if len(children) == 1:
            return children[0]
        return children
    
    # Base transformer methods that all plugins might use
    def NAME(self, token: Token) -> str:
        """Transform NAME tokens to strings"""
        return str(token.value)
    
    def ESCAPED_STRING(self, token: Token) -> str:
        """Transform ESCAPED_STRING tokens to unescaped strings"""
        import ast
        try:
            return ast.literal_eval(token.value)
        except (ValueError, SyntaxError):
            logger.warning(f"Failed to parse escaped string: {token.value}")
            return token.value[1:-1]  # Remove quotes as fallback

class DynamicKubeSolParser:
    """
    Dynamic parser for KubeSol that can compose grammar from plugins.
    """
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self.grammar_registry = GrammarRegistry()
        self.parser: Optional[Lark] = None
        self.transformer = DynamicTransformer(plugin_manager)
        self._last_plugin_count = 0
        
        # Register for plugin manager events (if available)
        # For now, we'll rebuild when needed
    
    def rebuild_parser(self) -> bool:
        """
        Rebuild the parser with current plugin grammar rules.
        
        Returns:
            True if parser was rebuilt successfully, False otherwise
        """
        try:
            # Clear existing rules
            self.grammar_registry = GrammarRegistry()
            
            # Register grammar rules from all loaded plugins
            for plugin_name in self.plugin_manager.get_loaded_plugins():
                plugin = self.plugin_manager.plugins[plugin_name]
                grammar_rules = plugin.get_grammar_rules()
                
                if not self.grammar_registry.register_grammar_rules(plugin_name, grammar_rules):
                    logger.error(f"Failed to register grammar rules from plugin {plugin_name}")
                    return False
            
            # Validate the composed grammar
            if not self.grammar_registry.validate_grammar():
                logger.error("Composed grammar validation failed")
                return False
            
            # Generate the complete grammar
            complete_grammar = self.grammar_registry.get_combined_grammar()
            
            # Rebuild transformer
            self.transformer._rebuild_transformers()
            
            # Create the new parser
            try:
                self.parser = Lark(
                    complete_grammar,
                    parser="lalr",
                    transformer=self.transformer,
                    maybe_placeholders=True
                )
                
                self._last_plugin_count = len(self.plugin_manager.get_loaded_plugins())
                logger.info(f"Parser rebuilt successfully with {self._last_plugin_count} plugins")
                return True
                
            except LarkError as e:
                logger.error(f"Failed to create Lark parser: {e}")
                logger.debug(f"Grammar that failed:\n{complete_grammar}")
                return False
            
        except Exception as e:
            logger.error(f"Error rebuilding parser: {e}")
            return False
    
    def _ensure_parser_current(self) -> bool:
        """Ensure parser is up-to-date with loaded plugins"""
        current_plugin_count = len(self.plugin_manager.get_loaded_plugins())
        
        if (self.parser is None or 
            current_plugin_count != self._last_plugin_count):
            return self.rebuild_parser()
        
        return True
    
    def parse(self, command: str) -> Dict[str, Any]:
        """
        Parse a KubeSol command string.
        
        Args:
            command: The command string to parse
            
        Returns:
            Parsed command dictionary or error information
        """
        if not command or not command.strip():
            return {"error": "Empty command", "type": "parse_error"}
        
        # Ensure parser is current
        if not self._ensure_parser_current():
            return {"error": "Parser initialization failed", "type": "parser_error"}
        
        if self.parser is None:
            return {"error": "No parser available", "type": "parser_error"}
        
        try:
            # Parse the command
            result = self.parser.parse(command)
            
            # If result is already a dict (from transformer), return it
            if isinstance(result, dict):
                return result
            
            # Otherwise, it might be a Tree object
            if isinstance(result, Tree):
                logger.warning(f"Parser returned Tree object instead of transformed result: {result}")
                return {"error": "Parse result not transformed", "type": "transform_error", "raw_result": str(result)}
            
            # Fallback for other types
            return {"error": "Unexpected parse result type", "type": "parse_error", "result": str(result)}
            
        except ParseError as e:
            logger.debug(f"Parse error for command '{command}': {e}")
            return {
                "error": f"Parse error: {e}", 
                "type": "parse_error", 
                "command": command,
                "line": getattr(e, 'line', None),
                "column": getattr(e, 'column', None)
            }
        
        except LexError as e:
            logger.debug(f"Lex error for command '{command}': {e}")
            return {
                "error": f"Lexical error: {e}",
                "type": "lex_error",
                "command": command
            }
        
        except Exception as e:
            logger.error(f"Unexpected error parsing command '{command}': {e}")
            return {
                "error": f"Unexpected parse error: {e}",
                "type": "unexpected_error",
                "command": command
            }
    
    def get_grammar_info(self) -> Dict[str, Any]:
        """
        Get information about the current grammar composition.
        
        Returns:
            Dictionary with grammar information
        """
        if not self._ensure_parser_current():
            return {"error": "Parser not available"}
        
        return {
            "total_rules": len(self.grammar_registry.list_rules()),
            "loaded_plugins": self.plugin_manager.get_loaded_plugins(),
            "rules_by_plugin": {
                plugin_name: [
                    rule_name for rule_name, source in self.grammar_registry.plugin_sources.items()
                    if source == plugin_name
                ]
                for plugin_name in self.plugin_manager.get_loaded_plugins()
            }
        }
    
    def validate_command_syntax(self, command: str) -> bool:
        """
        Validate command syntax without full parsing.
        
        Args:
            command: Command to validate
            
        Returns:
            True if syntax is valid, False otherwise
        """
        result = self.parse(command)
        return "error" not in result
    
    def get_supported_commands(self) -> List[str]:
        """
        Get list of supported command patterns.
        
        Returns:
            List of command patterns that can be parsed
        """
        if not self._ensure_parser_current():
            return []
        
        # Extract command rules from grammar
        command_rules = [
            rule_name for rule_name in self.grammar_registry.list_rules()
            if rule_name.endswith('_command')
        ]
        
        return command_rules
    
    def debug_grammar(self) -> str:
        """
        Get the complete grammar for debugging purposes.
        
        Returns:
            Complete grammar string
        """
        if not self._ensure_parser_current():
            return "Parser not available"
        
        return self.grammar_registry.get_combined_grammar()