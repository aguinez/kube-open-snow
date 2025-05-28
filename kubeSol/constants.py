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
RESOURCE_PARAMETER = "PARAMETER"
RESOURCE_SCRIPT = "SCRIPT"

# Script Specific Constants
SCRIPT_TYPE_PYTHON = "PYTHON"
SCRIPT_TYPE_PYSPARK = "PYSPARK"
SCRIPT_TYPE_SQL_SPARK = "SQL_SPARK"

SCRIPT_ENGINE_K8S_JOB = "K8S_JOB"
SCRIPT_ENGINE_SPARK_OPERATOR = "SPARK_OPERATOR"

# ConfigMap details for scripts
SCRIPT_CM_PREFIX = "kubesol-script-" # Changed prefix to reflect new name
SCRIPT_CM_LABEL_ROLE = "kubesol-role" # Changed label to reflect new name
SCRIPT_CM_LABEL_ROLE_VALUE_SCRIPT = "script"
SCRIPT_CM_KEY_CODE = "code"
SCRIPT_CM_KEY_CODE_FROM_FILE = "codeFromFilePath" 
SCRIPT_CM_KEY_TYPE = "scriptType"
SCRIPT_CM_KEY_ENGINE = "engine"
SCRIPT_CM_KEY_PARAMS_SPEC = "paramsSpec"
SCRIPT_CM_KEY_DESCRIPTION = "description"

# Common Field Names
FIELD_SCRIPT = "script" # Field name in PARAMETER resources

# Default Values
DEFAULT_NAMESPACE = "default"