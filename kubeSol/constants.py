# kubeSol/constants.py
"""
This module defines constants used throughout the KubeSol application.
"""

# Actions
ACTION_CREATE = "CREATE"
ACTION_DELETE = "DELETE"
ACTION_UPDATE = "UPDATE"
ACTION_GET = "GET"
ACTION_LIST = "LIST"
ACTION_EXECUTE = "EXECUTE"

# Resource Types
RESOURCE_SECRET = "SECRET"
RESOURCE_CONFIGMAP = "CONFIGMAP"
RESOURCE_PARAMETER = "PARAMETER" # If you maintain this resource type
RESOURCE_SCRIPT = "SCRIPT"

# Script Specific Constants
SCRIPT_TYPE_PYTHON = "PYTHON"
SCRIPT_TYPE_PYSPARK = "PYSPARK"
SCRIPT_TYPE_SQL_SPARK = "SQL_SPARK" # If used

SCRIPT_ENGINE_K8S_JOB = "K8S_JOB"
SCRIPT_ENGINE_SPARK_OPERATOR = "SPARK_OPERATOR" # If used

# ConfigMap details for scripts
SCRIPT_CM_PREFIX = "kubesol-script-"
SCRIPT_CM_LABEL_ROLE = "kubesol-role"
SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT = "script"
SCRIPT_CM_KEY_CODE = "code"
SCRIPT_CM_KEY_CODE_FROM_FILE = "codeFromFilePath" 
SCRIPT_CM_KEY_TYPE = "scriptType"
SCRIPT_CM_KEY_ENGINE = "engine"
SCRIPT_CM_KEY_PARAMS_SPEC = "paramsSpec"
SCRIPT_CM_KEY_DESCRIPTION = "description"

# Common Field Names (example, if used for PARAMETER type)
FIELD_SCRIPT = "script" 

# Default Values
DEFAULT_NAMESPACE = "default"