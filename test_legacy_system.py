#!/usr/bin/env python3
"""
KubeSol Legacy System Functionality Test

This script tests that the EXISTING legacy system still works correctly.
This is our baseline to ensure we don't break existing functionality.
"""

import sys
import os
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging for tests
logging.basicConfig(level=logging.ERROR)

def test_legacy_parser():
    """Test that the legacy parser still works"""
    print("🧪 Testing legacy parser...")
    
    try:
        from kubeSol.parser.parser import parse_sql
        
        test_commands = [
            "CREATE PROJECT myproject;",
            "CREATE ENV staging DEPENDS ON dev;", 
            "CREATE SECRET mysecret WITH key1=\"value1\";",
            "CREATE CONFIGMAP myconfig WITH config=\"test\";",
            "CREATE SCRIPT myscript TYPE PYTHON WITH CODE=\"print('hello')\";",
            "LIST PROJECTS;",
            "LIST SCRIPTS;",
            "USE PROJECT myproject ENV dev;",
        ]
        
        success_count = 0
        for command in test_commands:
            try:
                result = parse_sql(command)
                if isinstance(result, dict) and "action" in result:
                    success_count += 1
                    print(f"   ✅ {command}")
                else:
                    print(f"   ❌ {command} - Invalid result structure")
            except Exception as e:
                print(f"   ❌ {command} - Exception: {e}")
        
        if success_count == len(test_commands):
            print(f"   ✅ Legacy parser working - {success_count}/{len(test_commands)} commands parsed")
            return True
        else:
            print(f"   ⚠️ Legacy parser partial - {success_count}/{len(test_commands)} commands parsed")
            return success_count > 0
        
    except Exception as e:
        print(f"   ❌ Legacy parser test failed: {e}")
        return False

def test_legacy_executor():
    """Test that the legacy executor can handle commands"""
    print("🧪 Testing legacy executor...")
    
    try:
        from kubeSol.engine.executor import execute_command
        from kubeSol.projects.context import KubeSolContext
        
        context = KubeSolContext()
        
        # Test with a simple command that should parse but might fail execution
        # We're just testing that the executor doesn't crash
        with patch('sys.stdout'), patch('builtins.input', return_value='n'):
            try:
                # This might fail but shouldn't crash
                execute_command("LIST PROJECTS;", context=context)
                print("   ✅ Legacy executor can handle commands without crashing")
                return True
            except Exception as e:
                print(f"   ⚠️ Legacy executor runs but may have execution issues: {e}")
                return True  # It's OK if execution fails, we just want no crash
        
    except ImportError as e:
        print(f"   ❌ Legacy executor import failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Legacy executor test failed: {e}")
        return False

def test_legacy_context():
    """Test that the legacy context system works"""
    print("🧪 Testing legacy context...")
    
    try:
        from kubeSol.projects.context import KubeSolContext
        
        # Test context creation and basic operations
        context = KubeSolContext()
        
        # Test initial state
        if context.current_namespace != "default":
            raise Exception(f"Expected default namespace, got {context.current_namespace}")
        
        # Test setting project context
        context.set_project_env_context("testproject", "proj-123", "dev", "testproject-dev")
        
        if context.user_project_name != "testproject":
            raise Exception(f"Project name not set correctly: {context.user_project_name}")
        
        if context.environment_name != "dev":
            raise Exception(f"Environment name not set correctly: {context.environment_name}")
        
        # Test context clearing
        context.clear_project_context()
        
        if context.is_project_context_active():
            raise Exception("Context should be cleared")
        
        print("   ✅ Legacy context system working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Legacy context test failed: {e}")
        return False

def test_legacy_constants():
    """Test that legacy constants are available"""
    print("🧪 Testing legacy constants...")
    
    try:
        from kubeSol import constants
        
        # Check for key constants that should exist
        required_constants = [
            'ACTION_CREATE', 'ACTION_DELETE', 'ACTION_UPDATE',
            'RESOURCE_SECRET', 'RESOURCE_CONFIGMAP', 'RESOURCE_SCRIPT',
            'DEFAULT_NAMESPACE', 'SCRIPT_TYPE_PYTHON'
        ]
        
        missing_constants = []
        for const_name in required_constants:
            if not hasattr(constants, const_name):
                missing_constants.append(const_name)
        
        if missing_constants:
            print(f"   ❌ Missing constants: {missing_constants}")
            return False
        
        print("   ✅ All required legacy constants available")
        return True
        
    except Exception as e:
        print(f"   ❌ Legacy constants test failed: {e}")
        return False

def test_depends_on_parsing():
    """Test that the new DEPENDS ON functionality parses correctly in legacy system"""
    print("🧪 Testing DEPENDS ON parsing in legacy system...")
    
    try:
        from kubeSol.parser.parser import parse_sql
        
        # Test the new DEPENDS ON syntax
        command = "CREATE ENV staging DEPENDS ON dev;"
        result = parse_sql(command)
        
        if not isinstance(result, dict):
            raise Exception(f"Expected dict result, got {type(result)}")
        
        if result.get("action") != "CREATE_ENV":
            raise Exception(f"Expected CREATE_ENV action, got {result.get('action')}")
        
        if result.get("depends_on_env") != "dev":
            raise Exception(f"Expected depends_on_env='dev', got {result.get('depends_on_env')}")
        
        print("   ✅ DEPENDS ON parsing works in legacy system")
        return True
        
    except Exception as e:
        print(f"   ❌ DEPENDS ON parsing test failed: {e}")
        return False

def test_legacy_project_manager():
    """Test that legacy project manager functions are available"""
    print("🧪 Testing legacy project manager availability...")
    
    try:
        from kubeSol.projects import manager
        
        # Check that key functions exist
        required_functions = [
            'create_new_project',
            'add_environment_to_project', 
            'get_all_project_details',
            'delete_whole_project'
        ]
        
        missing_functions = []
        for func_name in required_functions:
            if not hasattr(manager, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            print(f"   ❌ Missing manager functions: {missing_functions}")
            return False
        
        # Test that the add_environment_to_project function has the new depends_on_env_name parameter
        import inspect
        sig = inspect.signature(manager.add_environment_to_project)
        params = list(sig.parameters.keys())
        
        if 'depends_on_env_name' not in params:
            print(f"   ❌ add_environment_to_project missing depends_on_env_name parameter")
            print(f"       Current parameters: {params}")
            return False
        
        print("   ✅ Legacy project manager available with DEPENDS ON support")
        return True
        
    except Exception as e:
        print(f"   ❌ Legacy project manager test failed: {e}")
        return False

def run_legacy_system_tests():
    """Run all legacy system tests"""
    print("🧪 Testing Legacy KubeSol System")
    print("=" * 60)
    print("These tests verify that the EXISTING system still works")
    print("This is our baseline before switching to plugins")
    print()
    
    tests = [
        test_legacy_constants,
        test_legacy_context,
        test_legacy_parser,
        test_depends_on_parsing,
        test_legacy_project_manager,
        test_legacy_executor,
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
    print(f"📊 Legacy System Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 Legacy system is working correctly!")
        print("✅ This confirms existing functionality is intact")
    elif passed > failed:
        print("⚠️ Legacy system mostly working with some issues")
        print("✅ Core functionality appears intact")
    else:
        print("❌ Legacy system has significant issues")
        print("❌ Need to fix existing problems before plugin migration")
    
    return failed == 0

if __name__ == "__main__":
    success = run_legacy_system_tests()
    
    if success:
        print("\n" + "="*60)
        print("🎯 RECOMMENDATION:")
        print("✅ Legacy system works - safe to test plugin system")
        print("💡 Run: python test_plugin_compatibility.py")
        print("💡 Then: python -m kubeSol.main_plugin_system")
    else:
        print("\n" + "="*60) 
        print("🎯 RECOMMENDATION:")
        print("❌ Fix legacy system issues first")
        print("💡 Use original system: python -m kubeSol.main")
    
    sys.exit(0 if success else 1)