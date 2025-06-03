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

# --- New Project/Environment Action Types ---
ACTION_CREATE_PROJECT = "CREATE_PROJECT"
ACTION_CREATE_ENV = "CREATE_ENV"
ACTION_LIST_PROJECTS = "LIST_PROJECTS"
ACTION_GET_PROJECT = "GET_PROJECT"       # Gets details of a project (its environments)
ACTION_UPDATE_PROJECT = "UPDATE_PROJECT"   # Updates project display name
ACTION_DROP_PROJECT = "DROP_PROJECT"       # Deletes a whole project (all its envs/namespaces)
ACTION_DROP_ENV = "DROP_ENV"         # Deletes a specific environment from a project
ACTION_USE_PROJECT_ENV = "USE_PROJECT_ENV" # Sets the current context

LOGICAL_TYPE_PROJECT = "PROJECT_LOGICAL" # To signify operations on the project abstraction
LOGICAL_TYPE_ENVIRONMENT = "ENVIRONMENT_LOGICAL" # To signify operations on the environment abstraction
# The actual Kubernetes resource being manipulated is Namespace, but these help route commands.


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

# --- Project and Environment Management Constants ---
# Labels to be applied to namespaces managed by KubeSol as projects/environments
PROJECT_ID_LABEL_KEY = "kubesol.io/project-id"       # Stores the unique, immutable ID of the KubeSol project
PROJECT_NAME_LABEL_KEY = "kubesol.io/project-name"    # Stores the user-defined, mutable display name of the project
ENVIRONMENT_LABEL_KEY = "kubesol.io/environment"    # Stores the environment name (e.g., dev, staging, prod)

# Default environment name created with a new project
DEFAULT_PROJECT_ENVIRONMENT = "dev"