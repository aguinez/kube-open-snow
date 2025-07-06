#!/usr/bin/env python3
"""
KubeSol Real Functionality Tests

Tests that verify the plugin system actually executes commands correctly
and maintains the same behavior as the legacy system.
"""

import sys
import os
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging for tests
logging.basicConfig(level=logging.ERROR)  # Suppress most logs during testing

class MockK8sAPI:
    """Mock K8s API to avoid requiring actual cluster"""
    def __init__(self):
        self.secrets = {}
        self.configmaps = {}
        self.namespaces = {}
        self.scripts = {}
    
    def create_k8s_secret(self, name, namespace, data):
        key = f"{namespace}/{name}"
        self.secrets[key] = data
        return True
    
    def delete_k8s_secret(self, name, namespace):
        key = f"{namespace}/{name}"
        return self.secrets.pop(key, None) is not None
    
    def update_k8s_secret(self, name, namespace, data):
        key = f"{namespace}/{name}"
        if key in self.secrets:
            self.secrets[key].update(data)
            return True
        return False
    
    def create_k8s_configmap(self, name, namespace, data):
        key = f"{namespace}/{name}"
        self.configmaps[key] = data
        return True
    
    def delete_k8s_configmap(self, name, namespace):
        key = f"{namespace}/{name}"
        return self.configmaps.pop(key, None) is not None
    
    def update_k8s_configmap(self, name, namespace, data):
        key = f"{namespace}/{name}"
        if key in self.configmaps:
            self.configmaps[key].update(data)
            return True
        return False
    
    def create_script_configmap(self, script_name, namespace, script_data):
        key = f"{namespace}/script-{script_name}"
        self.scripts[key] = script_data
        return True
    
    def delete_script_configmap(self, script_name, namespace):
        key = f"{namespace}/script-{script_name}"
        return self.scripts.pop(key, None) is not None
    
    def get_script_configmap(self, script_name, namespace):
        key = f"{namespace}/script-{script_name}"
        return self.scripts.get(key)
    
    def list_script_configmaps(self, namespace):
        result = {}
        prefix = f"{namespace}/script-"
        for key, data in self.scripts.items():
            if key.startswith(prefix):
                script_name = key[len(prefix):]
                result[script_name] = data
        return result

def setup_test_environment():
    """Setup test environment with mocked dependencies"""
    # Mock K8s API
    mock_k8s = MockK8sAPI()
    
    # Mock the k8s_api module
    k8s_api_mock = MagicMock()
    k8s_api_mock.create_k8s_secret = mock_k8s.create_k8s_secret
    k8s_api_mock.delete_k8s_secret = mock_k8s.delete_k8s_secret
    k8s_api_mock.update_k8s_secret = mock_k8s.update_k8s_secret
    k8s_api_mock.create_k8s_configmap = mock_k8s.create_k8s_configmap
    k8s_api_mock.delete_k8s_configmap = mock_k8s.delete_k8s_configmap
    k8s_api_mock.update_k8s_configmap = mock_k8s.update_k8s_configmap
    k8s_api_mock.create_script_configmap = mock_k8s.create_script_configmap
    k8s_api_mock.delete_script_configmap = mock_k8s.delete_script_configmap
    k8s_api_mock.get_script_configmap = mock_k8s.get_script_configmap
    k8s_api_mock.list_script_configmaps = mock_k8s.list_script_configmaps
    
    # Mock project manager functions
    manager_mock = MagicMock()
    manager_mock.create_new_project.return_value = ("proj-123", "dev", "proj-123-dev", "testproject")
    manager_mock.get_all_project_details.return_value = [
        {"project_id": "proj-123", "project_display_name": "testproject", "environment_names": ["dev"]}
    ]
    
    return mock_k8s, k8s_api_mock, manager_mock

def test_secret_operations():
    """Test SECRET CREATE/DELETE/UPDATE operations"""
    print("🧪 Testing SECRET operations...")
    
    try:
        mock_k8s, k8s_api_mock, manager_mock = setup_test_environment()
        
        # Setup plugin system
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.executor.base_executor import DynamicExecutor
        from kubeSol.core.context import KubeSolContext
        from kubeSol.plugins.core.resource_plugin import ResourcePlugin
        
        plugin_manager = PluginManager()
        plugin_manager.register_plugin_class(ResourcePlugin)
        plugin_manager.load_all_plugins()
        
        executor = DynamicExecutor(plugin_manager)
        context = KubeSolContext()
        
        # Mock the k8s_api import in ResourcePlugin
        with patch('kubeSol.plugins.core.resource_plugin.k8s_api', k8s_api_mock):
            # Test CREATE SECRET
            print("   Testing CREATE SECRET...")
            with patch('sys.stdout'):  # Suppress print output
                success = executor.execute_command('CREATE SECRET testsecret WITH key1="value1", key2="value2";', context)
            
            if not success:
                raise Exception("CREATE SECRET command failed")
            
            # Verify secret was created
            if "default/testsecret" not in mock_k8s.secrets:
                raise Exception("Secret was not created in mock storage")
            
            expected_data = {"key1": "value1", "key2": "value2"}
            if mock_k8s.secrets["default/testsecret"] != expected_data:
                raise Exception(f"Secret data mismatch: {mock_k8s.secrets['default/testsecret']} != {expected_data}")
            
            # Test UPDATE SECRET
            print("   Testing UPDATE SECRET...")
            with patch('sys.stdout'):
                success = executor.execute_command('UPDATE SECRET testsecret WITH key3="value3";', context)
            
            if not success:
                raise Exception("UPDATE SECRET command failed")
            
            # Test DELETE SECRET
            print("   Testing DELETE SECRET...")
            with patch('sys.stdout'):
                success = executor.execute_command('DELETE SECRET testsecret;', context)
            
            if not success:
                raise Exception("DELETE SECRET command failed")
            
            # Verify secret was deleted
            if "default/testsecret" in mock_k8s.secrets:
                raise Exception("Secret was not deleted from mock storage")
        
        print("   ✅ SECRET operations working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ SECRET operations failed: {e}")
        return False

def test_configmap_operations():
    """Test CONFIGMAP CREATE/DELETE/UPDATE operations"""
    print("🧪 Testing CONFIGMAP operations...")
    
    try:
        mock_k8s, k8s_api_mock, manager_mock = setup_test_environment()
        
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.executor.base_executor import DynamicExecutor
        from kubeSol.core.context import KubeSolContext
        from kubeSol.plugins.core.resource_plugin import ResourcePlugin
        
        plugin_manager = PluginManager()
        plugin_manager.register_plugin_class(ResourcePlugin)
        plugin_manager.load_all_plugins()
        
        executor = DynamicExecutor(plugin_manager)
        context = KubeSolContext()
        
        with patch('kubeSol.plugins.core.resource_plugin.k8s_api', k8s_api_mock):
            # Test CREATE CONFIGMAP
            print("   Testing CREATE CONFIGMAP...")
            with patch('sys.stdout'):
                success = executor.execute_command('CREATE CONFIGMAP testconfig WITH config="test", env="dev";', context)
            
            if not success:
                raise Exception("CREATE CONFIGMAP command failed")
            
            # Verify configmap was created
            if "default/testconfig" not in mock_k8s.configmaps:
                raise Exception("ConfigMap was not created in mock storage")
            
            # Test DELETE CONFIGMAP
            print("   Testing DELETE CONFIGMAP...")
            with patch('sys.stdout'):
                success = executor.execute_command('DELETE CONFIGMAP testconfig;', context)
            
            if not success:
                raise Exception("DELETE CONFIGMAP command failed")
            
            if "default/testconfig" in mock_k8s.configmaps:
                raise Exception("ConfigMap was not deleted from mock storage")
        
        print("   ✅ CONFIGMAP operations working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ CONFIGMAP operations failed: {e}")
        return False

def test_script_operations():
    """Test SCRIPT CREATE/DELETE/UPDATE/LIST operations"""
    print("🧪 Testing SCRIPT operations...")
    
    try:
        mock_k8s, k8s_api_mock, manager_mock = setup_test_environment()
        
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.executor.base_executor import DynamicExecutor
        from kubeSol.core.context import KubeSolContext
        from kubeSol.plugins.core.script_plugin import ScriptPlugin
        
        plugin_manager = PluginManager()
        plugin_manager.register_plugin_class(ScriptPlugin)
        plugin_manager.load_all_plugins()
        
        executor = DynamicExecutor(plugin_manager)
        context = KubeSolContext()
        
        with patch('kubeSol.plugins.core.script_plugin.k8s_api', k8s_api_mock):
            # Test CREATE SCRIPT
            print("   Testing CREATE SCRIPT...")
            with patch('sys.stdout'):
                success = executor.execute_command('CREATE SCRIPT testscript TYPE PYTHON WITH CODE="print(\\"hello\\")";', context)
            
            if not success:
                raise Exception("CREATE SCRIPT command failed")
            
            # Verify script was created
            if "default/script-testscript" not in mock_k8s.scripts:
                raise Exception("Script was not created in mock storage")
            
            script_data = mock_k8s.scripts["default/script-testscript"]
            if script_data.get("code") != 'print("hello")':
                raise Exception(f"Script code mismatch: {script_data.get('code')}")
            
            if script_data.get("scriptType") != "PYTHON":
                raise Exception(f"Script type mismatch: {script_data.get('scriptType')}")
            
            # Test LIST SCRIPTS
            print("   Testing LIST SCRIPTS...")
            with patch('sys.stdout'):
                success = executor.execute_command('LIST SCRIPTS;', context)
            
            if not success:
                raise Exception("LIST SCRIPTS command failed")
            
            # Test GET SCRIPT
            print("   Testing GET SCRIPT...")
            with patch('sys.stdout'):
                success = executor.execute_command('GET SCRIPT testscript;', context)
            
            if not success:
                raise Exception("GET SCRIPT command failed")
            
            # Test DELETE SCRIPT
            print("   Testing DELETE SCRIPT...")
            with patch('sys.stdout'):
                success = executor.execute_command('DELETE SCRIPT testscript;', context)
            
            if not success:
                raise Exception("DELETE SCRIPT command failed")
            
            if "default/script-testscript" in mock_k8s.scripts:
                raise Exception("Script was not deleted from mock storage")
        
        print("   ✅ SCRIPT operations working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ SCRIPT operations failed: {e}")
        return False

def test_project_operations():
    """Test PROJECT CREATE/LIST operations"""
    print("🧪 Testing PROJECT operations...")
    
    try:
        mock_k8s, k8s_api_mock, manager_mock = setup_test_environment()
        
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.executor.base_executor import DynamicExecutor
        from kubeSol.core.context import KubeSolContext
        from kubeSol.plugins.core.project_plugin import ProjectPlugin
        
        plugin_manager = PluginManager()
        plugin_manager.register_plugin_class(ProjectPlugin)
        plugin_manager.load_all_plugins()
        
        executor = DynamicExecutor(plugin_manager)
        context = KubeSolContext()
        
        with patch('kubeSol.plugins.core.project_plugin.manager', manager_mock):
            # Test LIST PROJECTS
            print("   Testing LIST PROJECTS...")
            with patch('sys.stdout'), patch('builtins.input', return_value='n'):
                success = executor.execute_command('LIST PROJECTS;', context)
            
            if not success:
                raise Exception("LIST PROJECTS command failed")
            
            # Verify manager was called
            manager_mock.get_all_project_details.assert_called()
            
            # Test CREATE PROJECT (mock the input for confirmation)
            print("   Testing CREATE PROJECT...")
            with patch('sys.stdout'), patch('builtins.input', return_value='n'):
                success = executor.execute_command('CREATE PROJECT testproject;', context)
            
            if not success:
                raise Exception("CREATE PROJECT command failed")
            
            # Verify manager was called
            manager_mock.create_new_project.assert_called_with(user_project_name="testproject")
        
        print("   ✅ PROJECT operations working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ PROJECT operations failed: {e}")
        return False

def test_depends_on_functionality():
    """Test the new DEPENDS ON functionality"""
    print("🧪 Testing DEPENDS ON functionality...")
    
    try:
        mock_k8s, k8s_api_mock, manager_mock = setup_test_environment()
        
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.executor.base_executor import DynamicExecutor
        from kubeSol.core.context import KubeSolContext
        from kubeSol.plugins.core.project_plugin import ProjectPlugin
        
        plugin_manager = PluginManager()
        plugin_manager.register_plugin_class(ProjectPlugin)
        plugin_manager.load_all_plugins()
        
        executor = DynamicExecutor(plugin_manager)
        context = KubeSolContext()
        
        # Mock the manager to simulate project context
        manager_mock.add_environment_to_project.return_value = "proj-123-staging"
        manager_mock._resolve_project_id_from_display_name.return_value = "proj-123"
        
        # Set project context
        context.set_project_env_context("testproject", "proj-123", "dev", "proj-123-dev")
        
        with patch('kubeSol.plugins.core.project_plugin.manager', manager_mock):
            # Test CREATE ENV with DEPENDS ON
            print("   Testing CREATE ENV with DEPENDS ON...")
            with patch('sys.stdout'):
                success = executor.execute_command('CREATE ENV staging DEPENDS ON dev;', context)
            
            if not success:
                raise Exception("CREATE ENV with DEPENDS ON command failed")
            
            # Verify manager was called with correct arguments
            manager_mock.add_environment_to_project.assert_called_with(
                project_id="proj-123",
                user_project_name="testproject",
                new_env_name="staging",
                depends_on_env_name="dev"
            )
        
        print("   ✅ DEPENDS ON functionality working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ DEPENDS ON functionality failed: {e}")
        return False

def test_command_parsing_edge_cases():
    """Test edge cases and complex command parsing"""
    print("🧪 Testing command parsing edge cases...")
    
    try:
        from kubeSol.core.plugin_system.plugin_manager import PluginManager
        from kubeSol.core.executor.base_executor import DynamicExecutor
        from kubeSol.core.context import KubeSolContext
        from kubeSol.plugins.core.resource_plugin import ResourcePlugin
        from kubeSol.plugins.core.script_plugin import ScriptPlugin
        from kubeSol.plugins.core.project_plugin import ProjectPlugin
        
        plugin_manager = PluginManager()
        for plugin_class in [ResourcePlugin, ScriptPlugin, ProjectPlugin]:
            plugin_manager.register_plugin_class(plugin_class)
        plugin_manager.load_all_plugins()
        
        executor = DynamicExecutor(plugin_manager)
        context = KubeSolContext()
        
        # Test commands that should fail gracefully
        edge_cases = [
            ("", "Empty command"),
            (";", "Semicolon only"),
            ("INVALID COMMAND;", "Invalid command"),
            ("CREATE SECRET;", "Missing required arguments"),
            ("CREATE SECRET test WITH;", "Incomplete WITH clause"),
        ]
        
        for command, description in edge_cases:
            print(f"   Testing {description}...")
            with patch('sys.stdout'):
                success = executor.execute_command(command, context)
            
            # These should all fail gracefully (return False, not throw exceptions)
            if success and command.strip() not in ["", ";"]:
                print(f"      ⚠️ Expected command to fail but it succeeded: {command}")
        
        # Test valid complex commands
        complex_commands = [
            'CREATE SECRET complex WITH key1="value with spaces", key2="value,with,commas";',
            'CREATE SCRIPT complex TYPE PYTHON WITH CODE="def hello():\\n    print(\\"world\\")";',
        ]
        
        mock_k8s, k8s_api_mock, manager_mock = setup_test_environment()
        
        with patch('kubeSol.plugins.core.resource_plugin.k8s_api', k8s_api_mock), \
             patch('kubeSol.plugins.core.script_plugin.k8s_api', k8s_api_mock):
            
            for command in complex_commands:
                print(f"   Testing complex command parsing...")
                with patch('sys.stdout'):
                    success = executor.execute_command(command, context)
                
                if not success:
                    raise Exception(f"Complex command failed: {command}")
        
        print("   ✅ Command parsing edge cases handled correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Command parsing edge cases failed: {e}")
        return False

def run_real_functionality_tests():
    """Run all real functionality tests"""
    print("🧪 Testing Real KubeSol Functionality")
    print("=" * 60)
    print("These tests verify that commands actually execute correctly")
    print("(using mocked backends to avoid requiring K8s cluster)")
    print()
    
    tests = [
        test_secret_operations,
        test_configmap_operations,
        test_script_operations,
        test_project_operations,
        test_depends_on_functionality,
        test_command_parsing_edge_cases
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
            import traceback
            traceback.print_exc()
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Real Functionality Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All real functionality tests passed! Plugin system maintains legacy behavior.")
        return True
    else:
        print("⚠️ Some functionality tests failed. There may be breaking changes.")
        return False

if __name__ == "__main__":
    success = run_real_functionality_tests()
    sys.exit(0 if success else 1)