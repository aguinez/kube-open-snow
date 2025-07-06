# kubeSol/core/plugin_system/plugin_interface.py
"""
Base plugin interfaces for the KubeSol plugin system.

This module defines the abstract base classes that all plugins must implement
to integrate with the KubeSol plugin system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass

@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

class KubeSolPlugin(ABC):
    """
    Base plugin interface for all KubeSol plugins.
    
    All plugins must inherit from this class and implement the required methods.
    This provides the foundation for dynamic grammar composition and command handling.
    """
    
    def __init__(self):
        self._metadata = None
        self._initialized = False
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata including name, version, and description"""
        pass
    
    @abstractmethod
    def get_grammar_rules(self) -> Dict[str, str]:
        """
        Return Lark grammar rules this plugin contributes.
        
        Returns:
            Dict mapping rule names to their grammar definitions
            
        Example:
            {
                "create_secret_command": "CREATE_KW SECRET_KW NAME WITH_KW fields",
                "secret_resource_type": "SECRET_KW"
            }
        """
        pass
    
    @abstractmethod
    def get_command_handlers(self) -> Dict[Tuple[str, str], Callable]:
        """
        Return command handlers this plugin provides.
        
        Returns:
            Dict mapping (action, resource_type) tuples to handler functions
            
        Example:
            {
                ("CREATE", "SECRET"): self._handle_create_secret,
                ("DELETE", "SECRET"): self._handle_delete_secret
            }
        """
        pass
    
    @abstractmethod
    def get_constants(self) -> Dict[str, Any]:
        """
        Return constants this plugin defines.
        
        Returns:
            Dict of constants this plugin contributes to the global namespace
            
        Example:
            {
                "RESOURCE_SECRET": "SECRET",
                "ACTION_CREATE_SECRET": "CREATE_SECRET"
            }
        """
        pass
    
    def initialize(self, context: Any = None) -> bool:
        """
        Initialize the plugin. Called after loading.
        
        Args:
            context: Optional initialization context
            
        Returns:
            True if initialization successful, False otherwise
        """
        self._initialized = True
        return True
    
    def cleanup(self) -> bool:
        """
        Cleanup plugin resources. Called before unloading.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        self._initialized = False
        return True
    
    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized"""
        return self._initialized
    
    def get_transformer_methods(self) -> Dict[str, Callable]:
        """
        Return transformer methods for grammar rules.
        
        Returns:
            Dict mapping rule names to transformer methods
        """
        return {}

class ResourcePlugin(KubeSolPlugin):
    """
    Plugin interface for resource management (SECRET, CONFIGMAP, PARAMETER, etc.)
    
    Resource plugins handle CRUD operations for Kubernetes resources
    that can be managed through KubeSol.
    """
    
    @abstractmethod
    def get_supported_resources(self) -> List[str]:
        """
        Return list of resource types this plugin supports.
        
        Returns:
            List of resource type names (e.g., ["SECRET", "CONFIGMAP"])
        """
        pass
    
    @abstractmethod
    def validate_resource_fields(self, resource_type: str, fields: Dict[str, Any]) -> bool:
        """
        Validate fields for a specific resource type.
        
        Args:
            resource_type: The type of resource being validated
            fields: Dictionary of fields to validate
            
        Returns:
            True if fields are valid, False otherwise
        """
        pass

class ProjectPlugin(KubeSolPlugin):
    """
    Plugin interface for project/environment management.
    
    Project plugins handle the creation, management, and organization
    of projects and their environments within KubeSol.
    """
    
    @abstractmethod
    def get_supported_project_operations(self) -> List[str]:
        """
        Return list of project operations this plugin supports.
        
        Returns:
            List of operation names (e.g., ["CREATE_PROJECT", "CREATE_ENV"])
        """
        pass
    
    @abstractmethod
    def validate_project_name(self, project_name: str) -> bool:
        """
        Validate a project name according to plugin rules.
        
        Args:
            project_name: The project name to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_environment_name(self, env_name: str) -> bool:
        """
        Validate an environment name according to plugin rules.
        
        Args:
            env_name: The environment name to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass

class OrchestrationPlugin(KubeSolPlugin):
    """
    Plugin interface for workflow orchestration integrations.
    
    Orchestration plugins provide integration with external workflow
    systems like Airflow, dbt, Prefect, etc.
    """
    
    @abstractmethod
    def get_supported_orchestrators(self) -> List[str]:
        """
        Return list of orchestration systems this plugin supports.
        
        Returns:
            List of orchestrator names (e.g., ["AIRFLOW", "DBT"])
        """
        pass
    
    @abstractmethod
    def validate_workflow_definition(self, workflow_def: Dict[str, Any]) -> bool:
        """
        Validate a workflow definition for the orchestrator.
        
        Args:
            workflow_def: The workflow definition to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def deploy_workflow(self, workflow_def: Dict[str, Any], target_env: str) -> bool:
        """
        Deploy a workflow to the target environment.
        
        Args:
            workflow_def: The workflow definition to deploy
            target_env: Target environment name
            
        Returns:
            True if deployment successful, False otherwise
        """
        pass

class ScriptPlugin(KubeSolPlugin):
    """
    Plugin interface for script management and execution.
    
    Script plugins handle the creation, management, and execution
    of scripts within the KubeSol environment.
    """
    
    @abstractmethod
    def get_supported_script_types(self) -> List[str]:
        """
        Return list of script types this plugin supports.
        
        Returns:
            List of script type names (e.g., ["PYTHON", "PYSPARK"])
        """
        pass
    
    @abstractmethod
    def get_supported_execution_engines(self) -> List[str]:
        """
        Return list of execution engines this plugin supports.
        
        Returns:
            List of engine names (e.g., ["K8S_JOB", "SPARK_OPERATOR"])
        """
        pass
    
    @abstractmethod
    def validate_script_code(self, script_type: str, code: str) -> bool:
        """
        Validate script code for a specific script type.
        
        Args:
            script_type: The type of script being validated
            code: The script code to validate
            
        Returns:
            True if code is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def prepare_execution_environment(self, script_name: str, script_type: str, engine: str) -> Dict[str, Any]:
        """
        Prepare the execution environment for a script.
        
        Args:
            script_name: Name of the script
            script_type: Type of the script
            engine: Execution engine to use
            
        Returns:
            Dictionary containing environment configuration
        """
        pass