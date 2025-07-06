# kubeSol/core/parser/grammar_registry.py
"""
Grammar Registry for dynamic grammar composition.

This module provides functionality for composing Lark grammar rules
from multiple plugins into a unified grammar.
"""

from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)

class GrammarRegistry:
    """
    Registry for managing and composing grammar rules from plugins.
    """
    
    def __init__(self):
        self.grammar_rules: Dict[str, str] = {}
        self.plugin_sources: Dict[str, str] = {}  # rule_name -> plugin_name
        self.reserved_rules: Set[str] = {
            "start", "command", "NAME", "ESCAPED_STRING", "WS"
        }
    
    def register_grammar_rules(self, plugin_name: str, rules: Dict[str, str]) -> bool:
        """
        Register grammar rules from a plugin.
        
        Args:
            plugin_name: Name of the plugin providing the rules
            rules: Dictionary of rule names to rule definitions
            
        Returns:
            True if all rules were registered successfully, False otherwise
        """
        conflicts = []
        
        for rule_name, rule_def in rules.items():
            if rule_name in self.reserved_rules:
                logger.warning(f"Plugin {plugin_name} attempted to override reserved rule {rule_name}")
                continue
            
            if rule_name in self.grammar_rules:
                existing_plugin = self.plugin_sources.get(rule_name, "unknown")
                if existing_plugin != plugin_name:
                    conflicts.append(f"Rule '{rule_name}' conflicts between {existing_plugin} and {plugin_name}")
                    continue
            
            self.grammar_rules[rule_name] = rule_def
            self.plugin_sources[rule_name] = plugin_name
        
        if conflicts:
            logger.error(f"Grammar conflicts detected: {conflicts}")
            return False
        
        logger.debug(f"Registered {len(rules)} grammar rules from plugin {plugin_name}")
        return True
    
    def unregister_plugin_rules(self, plugin_name: str):
        """
        Remove all grammar rules provided by a specific plugin.
        
        Args:
            plugin_name: Name of the plugin whose rules should be removed
        """
        rules_to_remove = [
            rule_name for rule_name, source_plugin in self.plugin_sources.items()
            if source_plugin == plugin_name
        ]
        
        for rule_name in rules_to_remove:
            del self.grammar_rules[rule_name]
            del self.plugin_sources[rule_name]
        
        logger.debug(f"Unregistered {len(rules_to_remove)} grammar rules from plugin {plugin_name}")
    
    def get_combined_grammar(self) -> str:
        """
        Generate the complete Lark grammar from all registered rules.
        
        Returns:
            Complete grammar string ready for Lark parser
        """
        if not self.grammar_rules:
            logger.warning("No grammar rules registered")
            return self._get_base_grammar()
        
        # Start building the grammar
        grammar_parts = []
        
        # Add the start rule
        grammar_parts.append("?start: command [\";\"]\n")
        
        # Collect all command rules (rules that end with '_command')
        command_rules = [
            rule_name for rule_name in self.grammar_rules.keys()
            if rule_name.endswith('_command')
        ]
        
        if command_rules:
            # Create the main command rule
            command_def = " | ".join(command_rules)
            grammar_parts.append(f"command: {command_def}\n")
        else:
            # Fallback if no command rules found
            grammar_parts.append("command: NAME\n")
        
        # Add all registered rules
        for rule_name, rule_def in self.grammar_rules.items():
            if rule_name != "command":  # Don't duplicate the command rule
                grammar_parts.append(f"{rule_name}: {rule_def}")
        
        # Add base terminals and imports
        grammar_parts.extend(self._get_base_terminals())
        
        combined_grammar = "\n".join(grammar_parts)
        
        logger.debug(f"Generated grammar with {len(self.grammar_rules)} rules")
        return combined_grammar
    
    def _get_base_grammar(self) -> str:
        """Get minimal base grammar when no plugins are loaded"""
        return """
        ?start: command [";"]
        command: NAME
        NAME: /[a-zA-Z0-9]([a-zA-Z0-9_.-]*[a-zA-Z0-9_])?|[a-zA-Z0-9]/
        %import common.ESCAPED_STRING
        %import common.WS
        %ignore WS
        """
    
    def _get_base_terminals(self) -> List[str]:
        """Get base terminal definitions and imports"""
        return [
            "NAME: /[a-zA-Z0-9]([a-zA-Z0-9_.-]*[a-zA-Z0-9_])?|[a-zA-Z0-9]/",
            "%import common.ESCAPED_STRING",
            "%import common.WS",
            "%ignore WS"
        ]
    
    def get_rule_source(self, rule_name: str) -> str:
        """Get the plugin that provided a specific rule"""
        return self.plugin_sources.get(rule_name, "unknown")
    
    def list_rules(self) -> List[str]:
        """Get list of all registered rule names"""
        return list(self.grammar_rules.keys())
    
    def validate_grammar(self) -> bool:
        """
        Validate the composed grammar for basic correctness.
        
        Returns:
            True if grammar appears valid, False otherwise
        """
        try:
            grammar_text = self.get_combined_grammar()
            
            # Basic validation - check for required elements
            if "start:" not in grammar_text:
                logger.error("Grammar missing start rule")
                return False
            
            if "command:" not in grammar_text:
                logger.error("Grammar missing command rule")
                return False
            
            # Check for balanced quotes and parentheses (basic check)
            if grammar_text.count('"') % 2 != 0:
                logger.error("Grammar has unbalanced quotes")
                return False
            
            logger.debug("Grammar validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Grammar validation failed: {e}")
            return False