# kubeSol/plugins/core/resource_plugin.py
"""
Resource Plugin for KubeSol

Handles CRUD operations for Kubernetes resources like SECRET, CONFIGMAP, and PARAMETER.
This plugin extracts the core resource management functionality from the monolithic codebase.
"""

from typing import Dict, List, Any, Callable, Tuple
import logging

from kubeSol.core.plugin_system.plugin_interface import ResourcePlugin as BaseResourcePlugin, PluginMetadata
from kubeSol.core.context import KubeSolContext

logger = logging.getLogger(__name__)

class ResourcePlugin(BaseResourcePlugin):
    """
    Plugin for managing Kubernetes resources (SECRET, CONFIGMAP, PARAMETER).
    
    This plugin provides the grammar rules, command handlers, and validation
    for basic resource operations.
    """
    
    def __init__(self):
        super().__init__()
        self._supported_resources = ["SECRET", "CONFIGMAP", "PARAMETER"]
    
    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata"""
        return PluginMetadata(
            name="ResourcePlugin",
            version="1.0.0",
            description="Core resource management plugin for SECRET, CONFIGMAP, and PARAMETER operations",
            author="KubeSol Team",
            dependencies=[]
        )
    
    def get_grammar_rules(self) -> Dict[str, str]:
        """Return grammar rules for resource operations"""
        return {
            # Resource type definitions
            "resource_type_value_rule": "SECRET_KW | CONFIGMAP_KW | PARAMETER_KW",
            
            # Main resource commands
            "create_resource_command": "CREATE_KW resource_type_value_rule NAME WITH_KW fields",
            "delete_resource_command": "DELETE_KW resource_type_value_rule NAME",
            "update_resource_command": "UPDATE_KW resource_type_value_rule NAME WITH_KW fields",
            
            # Field definitions
            "fields": "field (\",\" field)*",
            "field": "NAME \"=\" ESCAPED_STRING",
            
            # Keywords
            "CREATE_KW": "\"CREATE\"i",
            "DELETE_KW": "\"DELETE\"i", 
            "UPDATE_KW": "\"UPDATE\"i",
            "WITH_KW": "\"WITH\"i",
            "SECRET_KW": "\"SECRET\"i",
            "CONFIGMAP_KW": "\"CONFIGMAP\"i",
            "PARAMETER_KW": "\"PARAMETER\"i"
        }
    
    def get_command_handlers(self) -> Dict[Tuple[str, str], Callable]:
        """Return command handlers for resource operations"""
        return {
            ("CREATE", "SECRET"): self._handle_create_secret,
            ("DELETE", "SECRET"): self._handle_delete_secret,
            ("UPDATE", "SECRET"): self._handle_update_secret,
            ("CREATE", "CONFIGMAP"): self._handle_create_configmap,
            ("DELETE", "CONFIGMAP"): self._handle_delete_configmap,
            ("UPDATE", "CONFIGMAP"): self._handle_update_configmap,
            ("CREATE", "PARAMETER"): self._handle_create_parameter,
            ("DELETE", "PARAMETER"): self._handle_delete_parameter,
            ("UPDATE", "PARAMETER"): self._handle_update_parameter
        }
    
    def get_constants(self) -> Dict[str, Any]:
        """Return constants defined by this plugin"""
        return {
            # Actions
            "ACTION_CREATE": "CREATE",
            "ACTION_DELETE": "DELETE",
            "ACTION_UPDATE": "UPDATE",
            
            # Resource Types
            "RESOURCE_SECRET": "SECRET",
            "RESOURCE_CONFIGMAP": "CONFIGMAP",
            "RESOURCE_PARAMETER": "PARAMETER"
        }
    
    def get_transformer_methods(self) -> Dict[str, Callable]:
        """Return transformer methods for grammar rules"""
        return {
            "create_resource": self._transform_create_resource,
            "delete_resource": self._transform_delete_resource,
            "update_resource": self._transform_update_resource,
            "field": self._transform_field,
            "fields": self._transform_fields,
            "resource_type_value_rule": self._transform_resource_type,
            "SECRET_KW": lambda token: "SECRET",
            "CONFIGMAP_KW": lambda token: "CONFIGMAP", 
            "PARAMETER_KW": lambda token: "PARAMETER",
            "CREATE_KW": lambda token: token.value.upper(),
            "DELETE_KW": lambda token: token.value.upper(),
            "UPDATE_KW": lambda token: token.value.upper(),
            "WITH_KW": lambda token: token.value.upper()
        }
    
    def get_supported_resources(self) -> List[str]:
        """Return list of supported resource types"""
        return self._supported_resources.copy()
    
    def validate_resource_fields(self, resource_type: str, fields: Dict[str, Any]) -> bool:
        """Validate fields for a specific resource type"""
        if resource_type not in self._supported_resources:
            logger.error(f"Unsupported resource type: {resource_type}")
            return False
        
        if not fields:
            logger.error(f"No fields provided for {resource_type}")
            return False
        
        # Resource-specific validation
        if resource_type == "SECRET":
            return self._validate_secret_fields(fields)
        elif resource_type == "CONFIGMAP":
            return self._validate_configmap_fields(fields)
        elif resource_type == "PARAMETER":
            return self._validate_parameter_fields(fields)
        
        return True
    
    def _validate_secret_fields(self, fields: Dict[str, Any]) -> bool:
        """Validate SECRET-specific fields"""
        # Check for required fields or patterns
        # Secrets should have at least one data field
        return len(fields) > 0
    
    def _validate_configmap_fields(self, fields: Dict[str, Any]) -> bool:
        """Validate CONFIGMAP-specific fields"""
        # ConfigMaps should have at least one data field
        return len(fields) > 0
    
    def _validate_parameter_fields(self, fields: Dict[str, Any]) -> bool:
        """Validate PARAMETER-specific fields"""
        # Parameters are implemented as secrets, so similar validation
        return len(fields) > 0
    
    # Transformer methods - these must match @v_args(inline=True) signatures from legacy system
    def _transform_create_resource(self, create_kw_val, resource_type_val, name_str, with_kw_val, fields_dict):
        """Transform CREATE resource commands"""
        return {
            "action": "CREATE",
            "type": resource_type_val,
            "name": name_str.lower(),
            "fields": fields_dict
        }
    
    def _transform_delete_resource(self, delete_kw_val, resource_type_val, name_str):
        """Transform DELETE resource commands"""
        return {
            "action": "DELETE",
            "type": resource_type_val,
            "name": name_str.lower()
        }
    
    def _transform_update_resource(self, update_kw_val, resource_type_val, name_str, with_kw_val, fields_dict):
        """Transform UPDATE resource commands"""
        return {
            "action": "UPDATE",
            "type": resource_type_val,
            "name": name_str.lower(),
            "fields": fields_dict
        }
    
    def _transform_field(self, key_name_str, value_str):
        """Transform field definitions"""
        return (key_name_str, value_str)
    
    def _transform_fields(self, field_list):
        """Transform fields list into dictionary"""
        return dict(field_list)
    
    def _transform_resource_type(self, *items):
        """Transform resource type values"""
        return items[0] if items else None
    
    # Command handlers - these will use the existing k8s_api functionality
    def _handle_create_secret(self, parsed_args: dict, context: KubeSolContext):
        """Handle CREATE SECRET commands"""
        from kubeSol.engine import k8s_api
        
        name = parsed_args.get("name")
        fields = parsed_args.get("fields", {})
        namespace = context.current_namespace
        
        if not self.validate_resource_fields("SECRET", fields):
            return
        
        print(f"Creating Secret '{name}' in namespace '{namespace}'...")
        
        try:
            success = k8s_api.create_k8s_secret(
                name=name,
                namespace=namespace,
                data=fields
            )
            
            if success:
                print(f"✅ Secret '{name}' created successfully.")
            else:
                print(f"❌ Failed to create Secret '{name}'.")
                
        except Exception as e:
            print(f"❌ Error creating Secret '{name}': {e}")
            logger.error(f"Error creating Secret '{name}': {e}")
    
    def _handle_delete_secret(self, parsed_args: dict, context: KubeSolContext):
        """Handle DELETE SECRET commands"""
        from kubeSol.engine import k8s_api
        
        name = parsed_args.get("name")
        namespace = context.current_namespace
        
        print(f"Deleting Secret '{name}' from namespace '{namespace}'...")
        
        try:
            success = k8s_api.delete_k8s_secret(name=name, namespace=namespace)
            
            if success:
                print(f"✅ Secret '{name}' deleted successfully.")
            else:
                print(f"❌ Failed to delete Secret '{name}'.")
                
        except Exception as e:
            print(f"❌ Error deleting Secret '{name}': {e}")
            logger.error(f"Error deleting Secret '{name}': {e}")
    
    def _handle_update_secret(self, parsed_args: dict, context: KubeSolContext):
        """Handle UPDATE SECRET commands"""
        from kubeSol.engine import k8s_api
        
        name = parsed_args.get("name")
        fields = parsed_args.get("fields", {})
        namespace = context.current_namespace
        
        if not self.validate_resource_fields("SECRET", fields):
            return
        
        print(f"Updating Secret '{name}' in namespace '{namespace}'...")
        
        try:
            success = k8s_api.update_k8s_secret(
                name=name,
                namespace=namespace,
                data=fields
            )
            
            if success:
                print(f"✅ Secret '{name}' updated successfully.")
            else:
                print(f"❌ Failed to update Secret '{name}'.")
                
        except Exception as e:
            print(f"❌ Error updating Secret '{name}': {e}")
            logger.error(f"Error updating Secret '{name}': {e}")
    
    def _handle_create_configmap(self, parsed_args: dict, context: KubeSolContext):
        """Handle CREATE CONFIGMAP commands"""
        from kubeSol.engine import k8s_api
        
        name = parsed_args.get("name")
        fields = parsed_args.get("fields", {})
        namespace = context.current_namespace
        
        if not self.validate_resource_fields("CONFIGMAP", fields):
            return
        
        print(f"Creating ConfigMap '{name}' in namespace '{namespace}'...")
        
        try:
            success = k8s_api.create_k8s_configmap(
                name=name,
                namespace=namespace,
                data=fields
            )
            
            if success:
                print(f"✅ ConfigMap '{name}' created successfully.")
            else:
                print(f"❌ Failed to create ConfigMap '{name}'.")
                
        except Exception as e:
            print(f"❌ Error creating ConfigMap '{name}': {e}")
            logger.error(f"Error creating ConfigMap '{name}': {e}")
    
    def _handle_delete_configmap(self, parsed_args: dict, context: KubeSolContext):
        """Handle DELETE CONFIGMAP commands"""
        from kubeSol.engine import k8s_api
        
        name = parsed_args.get("name")
        namespace = context.current_namespace
        
        print(f"Deleting ConfigMap '{name}' from namespace '{namespace}'...")
        
        try:
            success = k8s_api.delete_k8s_configmap(name=name, namespace=namespace)
            
            if success:
                print(f"✅ ConfigMap '{name}' deleted successfully.")
            else:
                print(f"❌ Failed to delete ConfigMap '{name}'.")
                
        except Exception as e:
            print(f"❌ Error deleting ConfigMap '{name}': {e}")
            logger.error(f"Error deleting ConfigMap '{name}': {e}")
    
    def _handle_update_configmap(self, parsed_args: dict, context: KubeSolContext):
        """Handle UPDATE CONFIGMAP commands"""
        from kubeSol.engine import k8s_api
        
        name = parsed_args.get("name")
        fields = parsed_args.get("fields", {})
        namespace = context.current_namespace
        
        if not self.validate_resource_fields("CONFIGMAP", fields):
            return
        
        print(f"Updating ConfigMap '{name}' in namespace '{namespace}'...")
        
        try:
            success = k8s_api.update_k8s_configmap(
                name=name,
                namespace=namespace,
                data=fields
            )
            
            if success:
                print(f"✅ ConfigMap '{name}' updated successfully.")
            else:
                print(f"❌ Failed to update ConfigMap '{name}'.")
                
        except Exception as e:
            print(f"❌ Error updating ConfigMap '{name}': {e}")
            logger.error(f"Error updating ConfigMap '{name}': {e}")
    
    def _handle_create_parameter(self, parsed_args: dict, context: KubeSolContext):
        """Handle CREATE PARAMETER commands (implemented as secrets)"""
        # Parameters are implemented as secrets in the current system
        self._handle_create_secret(parsed_args, context)
    
    def _handle_delete_parameter(self, parsed_args: dict, context: KubeSolContext):
        """Handle DELETE PARAMETER commands (implemented as secrets)"""
        # Parameters are implemented as secrets in the current system
        self._handle_delete_secret(parsed_args, context)
    
    def _handle_update_parameter(self, parsed_args: dict, context: KubeSolContext):
        """Handle UPDATE PARAMETER commands (implemented as secrets)"""
        # Parameters are implemented as secrets in the current system
        self._handle_update_secret(parsed_args, context)