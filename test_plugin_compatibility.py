#!/usr/bin/env python3
"""
KubeSol Plugin System Compatibility Tests

This script tests that the new plugin-based system maintains backward
compatibility with existing KubeSol commands and functionality.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging for tests
logging.basicConfig(level=logging.WARNING)

def test_plugin_system_initialization():
    """Test that the plugin system initializes correctly"""
    print("🧪 Testing plugin system initialization...")
    
    try:
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.plugins.core.resource_plugin import ResourcePlugin
        from kubeSol.plugins.core.script_plugin import ScriptPlugin
        from kubeSol.plugins.core.project_plugin import ProjectPlugin
        
        # Create plugin manager
        plugin_manager = PluginManager()
        
        # Register core plugins
        core_plugins = [ResourcePlugin, ScriptPlugin, ProjectPlugin]
        
        for plugin_class in core_plugins:
            if not plugin_manager.register_plugin_class(plugin_class):
                raise Exception(f"Failed to register {plugin_class.__name__}")
        
        # Load all plugins
        successful, failed = plugin_manager.load_all_plugins()
        
        if successful != len(core_plugins):
            raise Exception(f"Expected {len(core_plugins)} plugins, got {successful}")
        
        if failed != 0:
            raise Exception(f"Expected 0 failed plugins, got {failed}")
        
        print("   ✅ Plugin system initialization successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Plugin system initialization failed: {e}")
        return False

def test_parser_compatibility():
    """Test that the new parser can handle legacy commands"""
    print("🧪 Testing parser compatibility with legacy commands...")
    
    try:
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.parser.base_parser import DynamicKubeSolParser
        from kubeSol.plugins.core.resource_plugin import ResourcePlugin
        from kubeSol.plugins.core.script_plugin import ScriptPlugin
        from kubeSol.plugins.core.project_plugin import ProjectPlugin
        
        # Initialize plugin system
        plugin_manager = PluginManager()
        for plugin_class in [ResourcePlugin, ScriptPlugin, ProjectPlugin]:
            plugin_manager.register_plugin_class(plugin_class)
        plugin_manager.load_all_plugins()
        
        # Create parser
        parser = DynamicKubeSolParser(plugin_manager)
        
        # Test legacy commands
        test_commands = [
            "CREATE PROJECT myproject;",
            "CREATE ENV staging DEPENDS ON dev;",
            "CREATE SECRET mysecret WITH key1=\"value1\";",
            "CREATE CONFIGMAP myconfig WITH config=\"test\";",
            "CREATE SCRIPT myscript TYPE PYTHON WITH CODE=\"print('hello')\";",
            "LIST PROJECTS;",
            "LIST SCRIPTS;",
            "GET PROJECT myproject;",
            "USE PROJECT myproject ENV dev;",
            "EXECUTE SCRIPT myscript;"
        ]
        
        success_count = 0
        for command in test_commands:
            try:
                result = parser.parse(command)
                if "error" not in result:
                    success_count += 1
                    print(f"   ✅ {command}")
                else:
                    print(f"   ❌ {command} - {result.get('error')}")
            except Exception as e:
                print(f"   ❌ {command} - Exception: {e}")
        
        if success_count == len(test_commands):
            print(f"   ✅ All {len(test_commands)} legacy commands parsed successfully")
            return True
        else:
            print(f"   ❌ Only {success_count}/{len(test_commands)} commands parsed successfully")
            return False
        
    except Exception as e:
        print(f"   ❌ Parser compatibility test failed: {e}")
        return False

def test_command_handler_availability():
    """Test that all expected command handlers are available"""
    print("🧪 Testing command handler availability...")
    
    try:
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.executor.base_executor import DynamicExecutor
        from kubeSol.plugins.core.resource_plugin import ResourcePlugin
        from kubeSol.plugins.core.script_plugin import ScriptPlugin
        from kubeSol.plugins.core.project_plugin import ProjectPlugin
        
        # Initialize plugin system
        plugin_manager = PluginManager()
        for plugin_class in [ResourcePlugin, ScriptPlugin, ProjectPlugin]:
            plugin_manager.register_plugin_class(plugin_class)
        plugin_manager.load_all_plugins()
        
        # Create executor
        executor = DynamicExecutor(plugin_manager)
        
        # Expected command handlers from legacy system
        expected_handlers = [
            ("CREATE", "SECRET"),
            ("DELETE", "SECRET"),
            ("UPDATE", "SECRET"),
            ("CREATE", "CONFIGMAP"),
            ("DELETE", "CONFIGMAP"),
            ("UPDATE", "CONFIGMAP"),
            ("CREATE", "PARAMETER"),
            ("DELETE", "PARAMETER"),
            ("UPDATE", "PARAMETER"),
            ("CREATE", "SCRIPT"),
            ("DELETE", "SCRIPT"),
            ("UPDATE", "SCRIPT"),
            ("EXECUTE", "SCRIPT"),
            ("LIST", "SCRIPT"),
            ("GET", "SCRIPT"),
            ("CREATE_PROJECT", "PROJECT_LOGICAL"),
            ("CREATE_ENV", "ENVIRONMENT_LOGICAL"),
            ("LIST_PROJECTS", "PROJECT_LOGICAL"),
            ("GET_PROJECT", "PROJECT_LOGICAL"),
            ("UPDATE_PROJECT", "PROJECT_LOGICAL"),
            ("DROP_PROJECT", "PROJECT_LOGICAL"),
            ("DROP_ENV", "ENVIRONMENT_LOGICAL"),
            ("USE_PROJECT_ENV", "PROJECT_LOGICAL")
        ]
        
        missing_handlers = []
        for action, resource_type in expected_handlers:
            handler = executor.command_registry.get_handler(action, resource_type)
            if not handler:
                missing_handlers.append((action, resource_type))
        
        if not missing_handlers:
            print(f"   ✅ All {len(expected_handlers)} expected handlers are available")
            return True
        else:
            print(f"   ❌ Missing handlers: {missing_handlers}")
            return False
        
    except Exception as e:
        print(f"   ❌ Command handler availability test failed: {e}")
        return False

def test_context_compatibility():
    """Test that the context system works correctly"""
    print("🧪 Testing context compatibility...")
    
    try:
        from kubeSol.core.context import KubeSolContext
        
        # Create context
        context = KubeSolContext(default_namespace="default")
        
        # Test initial state
        if context.current_namespace != "default":
            raise Exception(f"Expected default namespace 'default', got '{context.current_namespace}'")
        
        if context.is_project_context_active():
            raise Exception("Project context should not be active initially")
        
        # Test setting project context
        context.set_project_env_context("testproject", "proj-123", "dev", "testproject-dev")
        
        if not context.is_project_context_active():
            raise Exception("Project context should be active after setting")
        
        if context.user_project_name != "testproject":
            raise Exception(f"Expected project name 'testproject', got '{context.user_project_name}'")
        
        if context.environment_name != "dev":
            raise Exception(f"Expected environment 'dev', got '{context.environment_name}'")
        
        if context.current_namespace != "testproject-dev":
            raise Exception(f"Expected namespace 'testproject-dev', got '{context.current_namespace}'")
        
        # Test clearing context
        context.clear_project_context()
        
        if context.is_project_context_active():
            raise Exception("Project context should not be active after clearing")
        
        if context.current_namespace != "default":
            raise Exception(f"Expected default namespace after clearing, got '{context.current_namespace}'")
        
        print("   ✅ Context system working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Context compatibility test failed: {e}")
        return False

def test_grammar_composition():
    """Test that grammar rules are properly composed from plugins"""
    print("🧪 Testing grammar composition...")
    
    try:
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.parser.base_parser import DynamicKubeSolParser
        from kubeSol.plugins.core.resource_plugin import ResourcePlugin
        from kubeSol.plugins.core.script_plugin import ScriptPlugin
        from kubeSol.plugins.core.project_plugin import ProjectPlugin
        
        # Initialize plugin system
        plugin_manager = PluginManager()
        for plugin_class in [ResourcePlugin, ScriptPlugin, ProjectPlugin]:
            plugin_manager.register_plugin_class(plugin_class)
        plugin_manager.load_all_plugins()
        
        # Create parser
        parser = DynamicKubeSolParser(plugin_manager)
        
        # Get grammar info
        grammar_info = parser.get_grammar_info()
        
        if "total_rules" not in grammar_info:
            raise Exception("Grammar info missing total_rules")
        
        if grammar_info["total_rules"] < 10:  # Expect at least 10 rules
            raise Exception(f"Expected at least 10 grammar rules, got {grammar_info['total_rules']}")
        
        if "loaded_plugins" not in grammar_info:
            raise Exception("Grammar info missing loaded_plugins")
        
        expected_plugins = ["ResourcePlugin", "ScriptPlugin", "ProjectPlugin"]
        loaded_plugins = grammar_info["loaded_plugins"]
        
        for plugin in expected_plugins:
            if plugin not in loaded_plugins:
                raise Exception(f"Expected plugin {plugin} not found in loaded plugins")
        
        # Test that command rules exist
        supported_commands = parser.get_supported_commands()
        
        expected_command_patterns = [
            "create_resource_command",
            "create_script_command", 
            "create_project_command",
            "create_env_command"
        ]
        
        for pattern in expected_command_patterns:
            if pattern not in supported_commands:
                raise Exception(f"Expected command pattern {pattern} not found")
        
        print(f"   ✅ Grammar composed successfully with {grammar_info['total_rules']} rules")
        return True
        
    except Exception as e:
        print(f"   ❌ Grammar composition test failed: {e}")
        return False

def run_all_tests():
    """Run all compatibility tests"""
    print("🧪 Running KubeSol Plugin System Compatibility Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_plugin_system_initialization,
        test_parser_compatibility,
        test_command_handler_availability,
        test_context_compatibility,
        test_grammar_composition
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test {test_func.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Plugin system is backward compatible.")
        return True
    else:
        print("⚠️ Some tests failed. Plugin system may not be fully backward compatible.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)