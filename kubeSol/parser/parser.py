# kubeSol/parser/parser.py
from lark import Lark
from kubeSol.parser.transformer import KubeTransformer

sql_grammar = r"""
    ?start: command [";"]

    // --- Regla Principal de Comandos ---
    command: create_resource_command
           | delete_resource_command    
           | update_resource_command    
           | create_script_command
           | get_command                
           | list_scripts_command
           | list_projects_command     
           | delete_script_command
           | delete_project_command     
           | delete_env_command         
           | update_script_command
           | update_project_command    
           | execute_script_command
           | create_project_command
           | create_env_command
           | use_project_env_command

    // --- Palabras Clave Principales (Terminals) ---
    // (Keep all your keyword terminals as previously defined and corrected)
    CREATE_KW: "CREATE"i
    DELETE_KW: "DELETE"i
    UPDATE_KW: "UPDATE"i
    GET_KW: "GET"i
    LIST_KW: "LIST"i
    EXECUTE_KW: "EXECUTE"i
    USE_KW: "USE"i 
    DROP_KW: "DROP"i 

    SECRET_KW: "SECRET"i 
    CONFIGMAP_KW: "CONFIGMAP"i
    PARAMETER_KW: "PARAMETER"i 
    SCRIPT_KW: "SCRIPT"i 
    PROJECT_KW: "PROJECT"i
    ENV_KW: "ENV"i | "ENVIRONMENT"i
    
    WITH_KW: "WITH"i
    ARGS_KW: "ARGS"i
    PARAMS_FROM_CONFIGMAP_KW: "PARAMS_FROM_CONFIGMAP"i
    KEY_KW: "KEY"i
    AS_KW: "AS"i
    TYPE_KW: "TYPE"i
    ENGINE_KW: "ENGINE"i
    SET_KW: "SET"i
    FOR_KW: "FOR"i      
    FROM_KW: "FROM"i    
    THIS_KW: "THIS"i
    TO_KW: "TO"i
    KEY_PREFIX_KW: "KEY_PREFIX"i
    DEPENDING_KW: "DEPENDING"i 

    PYTHON_KW: "PYTHON"i
    PYSPARK_KW: "PYSPARK"i
    SQL_SPARK_KW: "SQL_SPARK"i
    K8S_JOB_KW: "K8S_JOB"i
    SPARK_OPERATOR_KW: "SPARK_OPERATOR"i
    
    // --- Definiciones para comandos de recursos estándar ---
    resource_type_value_rule: SECRET_KW | CONFIGMAP_KW | PARAMETER_KW
    create_resource_command: CREATE_KW resource_type_value_rule NAME WITH_KW fields -> create_resource
    delete_resource_command: DELETE_KW resource_type_value_rule NAME -> delete_resource
    update_resource_command: UPDATE_KW resource_type_value_rule NAME WITH_KW fields -> update_resource

    fields: field ("," field)*
    field: NAME "=" ESCAPED_STRING // NAME here is the key of the field

    // --- Extensiones de Lenguaje para Scripts ---
    create_script_command: CREATE_KW SCRIPT_KW NAME TYPE_KW script_type_value [ENGINE_KW script_engine_value] WITH_KW script_content_fields -> create_script
    script_content_fields: script_content_field ("," script_content_field)*
    script_content_field: "CODE"i "=" ESCAPED_STRING -> script_code_field
                        | "CODE_FROM_FILE"i "=" ESCAPED_STRING -> script_code_from_file_field
                        | "PARAMS_SPEC"i "=" ESCAPED_STRING -> script_params_spec_field
                        | "DESCRIPTION"i "=" ESCAPED_STRING -> script_description_field
    script_type_value: PYTHON_KW | PYSPARK_KW | SQL_SPARK_KW
    script_engine_value: K8S_JOB_KW | SPARK_OPERATOR_KW
    
    list_scripts_command: LIST_KW SCRIPT_KW "S"? -> list_scripts 
    delete_script_command: DELETE_KW SCRIPT_KW NAME -> delete_script
    update_script_command: UPDATE_KW SCRIPT_KW NAME SET_KW script_update_fields -> update_script
    script_update_fields: script_update_field ("," script_update_field)*
    script_update_field: "CODE"i "=" ESCAPED_STRING -> update_script_code_field
                       | "PARAMS_SPEC"i "=" ESCAPED_STRING -> update_script_params_spec_field
                       | "DESCRIPTION"i "=" ESCAPED_STRING -> update_script_description_field
                       | "ENGINE"i "=" script_engine_value -> update_script_engine_field 

    // --- Comando EXECUTE SCRIPT ---
    with_args_clause: WITH_KW ARGS_KW "(" custom_params ")"
    custom_params: custom_param ("," custom_param)*
    custom_param: NAME "=" ESCAPED_STRING
    with_params_cm_clause: WITH_KW PARAMS_FROM_CONFIGMAP_KW NAME [KEY_PREFIX_KW ESCAPED_STRING] 
    quoted_string_value: ESCAPED_STRING
    secret_mount_clause: WITH_KW SECRET_KW NAME KEY_KW quoted_string_value AS_KW quoted_string_value -> map_secret_mount
    execute_script_command: EXECUTE_KW SCRIPT_KW NAME \
                            [with_args_clause] \
                            [with_params_cm_clause] \
                            (secret_mount_clause)* \
                            -> execute_script

    // --- Reglas para Gestión de Proyectos y Entornos ---
    create_project_command: CREATE_KW PROJECT_KW NAME -> create_project_cmd

    project_target_clause_project_name_ref: PROJECT_KW NAME -> specified_project_name_transformer
    project_target_clause_this_project_ref: THIS_KW PROJECT_KW -> this_project_transformer
    project_target_clause: (FOR_KW | FROM_KW) (project_target_clause_project_name_ref | project_target_clause_this_project_ref)
    depending_from_clause: DEPENDING_KW FROM_KW ENV_KW NAME -> depending_from_clause
    depends_on_clause: "DEPENDS"i "ON"i NAME -> depends_on_clause

    create_env_command: CREATE_KW ENV_KW NAME [project_target_clause] [depends_on_clause] -> create_env_cmd

    list_projects_command: LIST_KW PROJECT_KW "S"? -> list_projects_cmd 

    // --- REGLAS GET UNIFICADAS ---
    get_script_target_payload: SCRIPT_KW NAME -> get_script_target_transformer
    get_project_by_name_payload: PROJECT_KW NAME -> get_project_by_name_transformer
    get_this_project_payload: THIS_KW PROJECT_KW -> get_this_project_transformer
    get_target_choice: get_script_target_payload
                     | get_project_by_name_payload
                     | get_this_project_payload
    get_command: GET_KW get_target_choice -> get_command_transformer
    
    update_project_command: UPDATE_KW PROJECT_KW NAME TO_KW NAME -> update_project_cmd
    delete_project_command: DROP_KW PROJECT_KW NAME -> drop_project_cmd 
    delete_env_command: DROP_KW ENV_KW NAME [project_target_clause] -> drop_env_cmd 
    use_project_env_command: USE_KW PROJECT_KW NAME ENV_KW NAME -> use_project_env_cmd

    // --- Terminales Comunes ---
    // NAME modificado para permitir puntos y guiones bajos internamente,
    // y asegurar que no empiece/termine con ellos si es un solo carácter.
    // Esto debería permitir que "file_key.json" sea un solo token NAME.
    NAME: /[a-zA-Z0-9]([a-zA-Z0-9_.-]*[a-zA-Z0-9_])?|[a-zA-Z0-9]/

    %import common.ESCAPED_STRING 
    %import common.WS             
    %ignore WS                   
"""

kube_sol_parser = Lark(sql_grammar, parser="lalr", transformer=KubeTransformer(), maybe_placeholders=True) 

def parse_sql(input_sql_command: str) -> dict: 
    return kube_sol_parser.parse(input_sql_command)