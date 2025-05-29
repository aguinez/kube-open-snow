# kubecli/parser/parser.py
from lark import Lark
from kubeSol.parser.transformer import KubeTransformer # Transformer class should also be in English

# The grammar defines the SQL-like language for KubeCLI
sql_grammar = r"""
    ?start: command [";"] // A command can optionally end with a semicolon

    // Main command types
    command: create_command
           | delete_command
           | update_command         // For SECRET, CONFIGMAP, PARAMETER resources
           // Script-specific commands
           | create_script_command
           | get_script_command
           | list_scripts_command
           | delete_script_command
           | update_script_command  // For SCRIPT resources
           | execute_script_command

    // --- Definitions for standard resource commands (Secret, ConfigMap, Parameter) ---
    create_command: "CREATE" resource_type_value_rule resource_name "WITH" fields -> create_resource
    delete_command: "DELETE" resource_type_value_rule resource_name -> delete_resource
    update_command: "UPDATE" resource_type_value_rule resource_name "WITH" fields -> update_resource

    // Keywords for resource types
    SECRET_KW: "SECRET"
    CONFIGMAP_KW: "CONFIGMAP"
    PARAMETER_KW: "PARAMETER"
    resource_type_value_rule: SECRET_KW | CONFIGMAP_KW | PARAMETER_KW // Rule to capture the resource type

    resource_name: NAME // A generic name rule for resources
    fields: field ("," field)* // A list of key-value pairs
    field: NAME "=" ESCAPED_STRING // A single key-value pair

    // --- Script Language Extensions ---
    SCRIPT_KW: "SCRIPT" // Keyword for script operations
    script_name: NAME   // Name for a script resource

    // Command to create a script
    create_script_command: "CREATE" SCRIPT_KW script_name "TYPE" script_type_value ["ENGINE" script_engine_value] "WITH" script_content_fields -> create_script
    
    script_content_fields: script_content_field ("," script_content_field)* // Fields within the WITH clause for scripts
    // Specific fields for script content; 'i' makes them case-insensitive
    script_content_field: "CODE"i "=" ESCAPED_STRING -> script_code_field
                        | "CODE_FROM_FILE"i "=" ESCAPED_STRING -> script_code_from_file_field
                        | "PARAMS_SPEC"i "=" ESCAPED_STRING -> script_params_spec_field
                        | "DESCRIPTION"i "=" ESCAPED_STRING -> script_description_field

    // Keywords for script types
    PYTHON_KW: "PYTHON"
    PYSPARK_KW: "PYSPARK"
    SQL_SPARK_KW: "SQL_SPARK"
    script_type_value: PYTHON_KW | PYSPARK_KW | SQL_SPARK_KW // Rule for script type

    // Keywords for script execution engines
    K8S_JOB_KW: "K8S_JOB"
    SPARK_OPERATOR_KW: "SPARK_OPERATOR"
    script_engine_value: K8S_JOB_KW | SPARK_OPERATOR_KW // Rule for script engine

    // Other script commands
    get_script_command: "GET" SCRIPT_KW script_name -> get_script
    list_scripts_command: "LIST" SCRIPT_KW -> list_scripts
    delete_script_command: "DELETE" SCRIPT_KW script_name -> delete_script

    // --- UPDATE SCRIPT Command ---
    update_script_command: "UPDATE" SCRIPT_KW script_name "SET" script_update_fields -> update_script

    script_update_fields: script_update_field ("," script_update_field)* // Fields for updating a script
    // Specific fields that can be updated in a script
    script_update_field: "CODE"i "=" ESCAPED_STRING -> update_script_code_field
                       | "PARAMS_SPEC"i "=" ESCAPED_STRING -> update_script_params_spec_field
                       | "DESCRIPTION"i "=" ESCAPED_STRING -> update_script_description_field
                       | "ENGINE"i "=" script_engine_value -> update_script_engine_field 

    // --- EXECUTE SCRIPT Command ---
    execute_script_command: "EXECUTE" SCRIPT_KW script_name [with_args_clause] [with_params_cm_clause] -> execute_script
    
    // Optional clause for providing inline arguments
    with_args_clause: "WITH" "ARGS" "(" custom_params ")"
    custom_params: custom_param ("," custom_param)*
    custom_param: NAME "=" ESCAPED_STRING // Custom parameter format

    // Optional clause for loading arguments from a ConfigMap
    with_params_cm_clause: "WITH" "PARAMS_FROM_CONFIGMAP" configmap_name ["KEY_PREFIX" prefix_string]
    configmap_name: NAME          // Name of the ConfigMap containing parameters
    prefix_string: ESCAPED_STRING // Optional prefix for keys in the ConfigMap

    // General name rule: starts with a letter/number, can contain hyphens or underscores, ends with letter/number.
    // K8s sanitization will be applied later for actual resource names.
    NAME: /[a-z0-9]([-a-z0-9_]*[a-z0-9])?/ 

    %import common.ESCAPED_STRING // Lark common terminal for quoted strings
    %import common.WS             // Lark common terminal for whitespace
    %ignore WS                    // Ignore whitespace between tokens
"""

# Initialize the Lark parser with the defined grammar and transformer.
# The transformer (KubeTransformer) converts the parse tree into a more usable Python structure (typically dictionaries).
# `maybe_placeholders=True` allows optional grammar rules ([...]) to correctly pass None to the transformer if not present.
kube_cli_parser = Lark(sql_grammar, parser="lalr", transformer=KubeTransformer(), maybe_placeholders=True) # Renamed

def parse_sql(input_sql_command: str): # Renamed
    """
    Parses the KubeCLI SQL-like command string.

    Args:
        input_sql_command: The command string to parse.

    Returns:
        A dictionary representing the parsed command structure, 
        as transformed by KubeTransformer.
    
    Raises:
        Lark errors (e.g., UnexpectedToken, VisitError) if parsing or transformation fails.
    """
    return kube_cli_parser.parse(input_sql_command)