# kubeSol/parser/transformer.py
from lark import Transformer, v_args, Token
from kubeSol import constants # Asegúrate de que tus constantes estén bien definidas aquí
import ast

class KubeTransformer(Transformer):
    # --- Transformadores de Terminales Básicos ---
    def NAME(self, token: Token) -> str:
        """Transforma un token NAME a su valor string."""
        return str(token.value)

    def ESCAPED_STRING(self, token: Token) -> str:
        """Transforma un token ESCAPED_STRING a su contenido string sin escapes."""
        try:
            return ast.literal_eval(token.value)
        except (ValueError, SyntaxError):
            # Fallback si ast.literal_eval falla
            print(f"Warning: ast.literal_eval failed for ESCAPED_STRING: {token.value}. Using basic unquoting.")
            return token.value[1:-1]

    # --- Transformadores para Campos Genéricos (cláusula WITH) ---
    @v_args(inline=True)
    def field(self, key_name_str: str, value_str: str) -> tuple[str, str]:
        return key_name_str, value_str

    def fields(self, field_list: list) -> dict:
        return dict(field_list)
    
    # --- Transformadores para Palabras Clave (Keywords) ---
    # Estos métodos convierten los tokens de keyword a un valor canónico o una constante.
    # Los nombres de los métodos deben coincidir con los nombres de los terminales en la gramática (en mayúsculas).

    # Keywords de Comandos Principales
    def CREATE_KW(self, token: Token): return token.value.upper()
    def DELETE_KW(self, token: Token): return token.value.upper() # Si se define y usa DELETE_KW en lugar de "DELETE"i
    def UPDATE_KW(self, token: Token): return token.value.upper()
    def GET_KW(self, token: Token): return token.value.upper()
    def LIST_KW(self, token: Token): return token.value.upper()
    def EXECUTE_KW(self, token: Token): return token.value.upper()
    def USE_KW(self, token: Token): return token.value.upper()
    def DROP_KW(self, token: Token): return token.value.upper()

    # Keywords de Tipos de Recurso y Lógicos
    def SECRET_KW(self, token: Token): return constants.RESOURCE_SECRET 
    def CONFIGMAP_KW(self, token: Token): return constants.RESOURCE_CONFIGMAP
    def PARAMETER_KW(self, token: Token): return constants.RESOURCE_PARAMETER 
    def SCRIPT_KW(self, token: Token): return constants.RESOURCE_SCRIPT 
    def PROJECT_KW(self, token: Token): return token.value.upper() # Devuelve "PROJECT"
    def ENV_KW(self, token: Token): return token.value.upper()     # Devuelve "ENV" o "ENVIRONMENT"
    
    # Otros Keywords para Cláusulas
    def WITH_KW(self, token: Token): return token.value.upper()
    def ARGS_KW(self, token: Token): return token.value.upper()
    def PARAMS_FROM_CONFIGMAP_KW(self, token: Token): return token.value.upper()
    def KEY_KW(self, token: Token): return token.value.upper()
    def AS_KW(self, token: Token): return token.value.upper()
    def TYPE_KW(self, token: Token): return token.value.upper()
    def ENGINE_KW(self, token: Token): return token.value.upper()
    def SET_KW(self, token: Token): return token.value.upper()
    def FOR_KW(self, token: Token): return token.value.upper()      
    def FROM_KW(self, token: Token): return token.value.upper()    
    def THIS_KW(self, token: Token): return token.value.upper()
    def TO_KW(self, token: Token): return token.value.upper()
    def KEY_PREFIX_KW(self, token: Token): return token.value.upper()

    # Keywords de Tipo/Motor de Script
    def PYTHON_KW(self, token: Token): return constants.SCRIPT_TYPE_PYTHON
    def PYSPARK_KW(self, token: Token): return constants.SCRIPT_TYPE_PYSPARK
    def SQL_SPARK_KW(self, token: Token): return constants.SCRIPT_TYPE_SQL_SPARK
    def K8S_JOB_KW(self, token: Token): return constants.SCRIPT_ENGINE_K8S_JOB
    def SPARK_OPERATOR_KW(self, token: Token): return constants.SCRIPT_ENGINE_SPARK_OPERATOR

    # --- Transformadores para Reglas de Recursos y Nombres ---
    def resource_type_value_rule(self, items: list): return items[0] # Pasa el valor de SECRET_KW, etc.
    # No se necesitan transformadores para 'resource_name' o 'script_name' si son solo 'NAME'
    # y 'NAME' ya tiene su propio transformador. Los valores se pasarán directamente.

    def script_type_value(self, items: list): return items[0] # Pasa el valor de PYTHON_KW, etc.
    def script_engine_value(self, items: list): return items[0] # Pasa el valor de K8S_JOB_KW, etc.
    def quoted_string_value(self, items: list): return items[0] # Pasa el string de ESCAPED_STRING

    # --- Transformadores para Campos de Contenido de Script (CREATE SCRIPT) ---
    @v_args(inline=True)
    def script_code_field(self, value_str: str): # Assuming "CODE" and "=" are literals not passed
        # If "CODE"i was a terminal CODE_KW with a transformer, it would be an argument here.
        # For simplicity, assuming it's just one value if rule is like: "CODE"i "=" ESCAPED_STRING
        return (constants.SCRIPT_CM_KEY_CODE, value_str)
    @v_args(inline=True)
    def script_code_from_file_field(self, file_path_str: str): # Corrected signature
        # This method is called for the rule: "CODE_FROM_FILE"i "=" ESCAPED_STRING -> script_code_from_file_field
        # With @v_args(inline=True), only the transformed result of ESCAPED_STRING is passed
        # if "CODE_FROM_FILE"i and "=" are treated as literals and skipped.
        print(f"[DEBUG TRANSFORMER] script_code_from_file_field received path: {file_path_str}")
        return (constants.SCRIPT_CM_KEY_CODE_FROM_FILE, file_path_str)
    @v_args(inline=True)
    def script_params_spec_field(self, value_str: str): # Corrected signature
        return (constants.SCRIPT_CM_KEY_PARAMS_SPEC, value_str)    @v_args(inline=True)
    def script_description_field(self, value_str: str): # Corrected signature
        return (constants.SCRIPT_CM_KEY_DESCRIPTION, value_str)
    def script_content_fields(self, field_tuples_list: list): 
        # This method receives a list of tuples from the methods above.
        # e.g., [ ("codeFromFilePath", "/path/to/file.py"), ("description", "A script") ]
        return dict(field_tuples_list)
    # --- Transformadores para Comandos de Recursos Estándar ---
    @v_args(inline=True)
    def create_resource(self, create_kw_val, resource_type_val, name_str, with_kw_val, fields_dict):
        return {"action": constants.ACTION_CREATE, "type": resource_type_val, 
                "name": name_str.lower(), "fields": fields_dict} # Canonicalizar nombre aquí también

    @v_args(inline=True)
    def delete_resource(self, delete_kw_val, resource_type_val, name_str):
        return {"action": constants.ACTION_DELETE, "type": resource_type_val, "name": name_str.lower()}

    @v_args(inline=True)
    def update_resource(self, update_kw_val, resource_type_val, name_str, with_kw_val, fields_dict):
        return {"action": constants.ACTION_UPDATE, "type": resource_type_val, 
                "name": name_str.lower(), "fields": fields_dict}

    # --- Transformadores para Comandos de Script ---
    @v_args(inline=True)
    def create_script(self, 
                      create_kw_val,        # From CREATE_KW
                      script_keyword_val,   # From SCRIPT_KW
                      script_name_str,      # From NAME
                      type_keyword_val,     # From TYPE_KW
                      script_type_val,      # From script_type_value
                      # For the optional block: [ENGINE_KW script_engine_value]
                      # If present, engine_kw_arg and engine_val_arg will be populated.
                      # If not present, they will be None if maybe_placeholders=True in Lark()
                      # and if they are correctly handled as optional by Lark's tree building.
                      # A common way @v_args(inline=True) handles an optional group [a b]
                      # is by passing the transformed values of a and b if the group matches.
                      # If the group doesn't match, fewer arguments are passed overall,
                      # or placeholders (None) are passed if Lark is configured with maybe_placeholders=True
                      # and the grammar allows it cleanly.
                      # Let's assume they are passed if present.
                      # The error "10 were given" means they *were* passed.
                      # The error "takes 9" means the signature was missing one.
                      # Previous signature had 8 args after self:
                      # create_kw, script_kw, name, type_kw, type_val, engine_block (1), with_kw, content_fields
                      # If engine_block expands to 2 args (engine_kw, engine_val), then we need 9 args after self.
                      engine_keyword_val,     # From ENGINE_KW (if present)
                      script_engine_val,    # From script_engine_value (if present)
                      with_keyword_val,       # From WITH_KW
                      script_content_fields_dict # From script_content_fields
                     ):
        
        details = script_content_fields_dict 
        details[constants.SCRIPT_CM_KEY_TYPE] = script_type_val
        
        # Check if engine values were actually passed (they would not be None if the optional group matched)
        # The error implies they *are* being passed.
        if script_engine_val is not None: # engine_keyword_val would also be present
            details[constants.SCRIPT_CM_KEY_ENGINE] = script_engine_val
        
        return {
            "action": constants.ACTION_CREATE, 
            "type": constants.RESOURCE_SCRIPT, 
            "name": script_name_str.lower(), 
            "details": details
        }
    
    @v_args(inline=True)
    def list_scripts(self, list_keyword_val, script_keyword_val, plural_s_token=None):
        return {"action": constants.ACTION_LIST, "type": constants.RESOURCE_SCRIPT}

    @v_args(inline=True)
    def delete_script(self, delete_keyword_val, script_keyword_val, script_name_str):
        return {"action": constants.ACTION_DELETE, "type": constants.RESOURCE_SCRIPT, "name": script_name_str.lower()}

    # Para campos de UPDATE SCRIPT
    @v_args(inline=True)
    def update_script_code_field(self, code_literal, eq_literal, value_str): return (constants.SCRIPT_CM_KEY_CODE, value_str)
    @v_args(inline=True)
    def update_script_params_spec_field(self, params_literal, eq_literal, value_str): return (constants.SCRIPT_CM_KEY_PARAMS_SPEC, value_str)
    @v_args(inline=True)
    def update_script_description_field(self, desc_literal, eq_literal, value_str): return (constants.SCRIPT_CM_KEY_DESCRIPTION, value_str)
    @v_args(inline=True)
    def update_script_engine_field(self, engine_literal, eq_literal, engine_value_str): return (constants.SCRIPT_CM_KEY_ENGINE, engine_value_str)
    def script_update_fields(self, field_tuples_list: list): return dict(field_tuples_list)

    @v_args(inline=True)
    def update_script(self, update_keyword_val, script_keyword_val, script_name_str, set_keyword_val, updates_dict):
        return {"action": constants.ACTION_UPDATE, "type": constants.RESOURCE_SCRIPT, 
                "name": script_name_str.lower(), "updates": updates_dict}
                
    # --- Transformadores para Cláusulas de EXECUTE SCRIPT ---
    @v_args(inline=True)
    def custom_param(self, name_str, value_str): return (name_str, value_str)
    def custom_params(self, param_list: list): return dict(param_list)
    
    @v_args(inline=True)
    def with_args_clause(self, with_kw_val, args_kw_val, params_dict):
        return {"custom_args": params_dict} 

    @v_args(inline=True)
    def with_params_cm_clause(self, with_kw_val, params_from_cm_kw_val, cm_name_str, optional_key_prefix_block):
        res = {"cm_name": cm_name_str}
        if optional_key_prefix_block: # Es una lista [KEY_PREFIX_KW_val, prefix_str_val]
            res["key_prefix"] = optional_key_prefix_block[1] 
        return {"args_from_configmap": res}

    @v_args(inline=True)
    def map_secret_mount(self, with_kw_val, secret_kw_val, secret_name_str, key_kw_val, key_in_secret_str, as_kw_val, mount_path_in_pod_str):
        return {"type": "secret_mount_spec", "secret_name": secret_name_str, 
                "key_in_secret": key_in_secret_str, "mount_path_in_pod": mount_path_in_pod_str}

    @v_args(inline=True) # El primer arg es el resultado de SCRIPT_KW
    def execute_script(self, execute_kw_val, script_keyword_val, script_name_str, *optional_clauses):
        # script_name_str es el nombre del script
        # optional_clauses es una tupla de los resultados de with_args_clause, with_params_cm_clause, y secret_mount_clause
        instruction = {
            "action": constants.ACTION_EXECUTE, "type": constants.RESOURCE_SCRIPT, 
            "name": script_name_str.lower(),
            "custom_args": None, "args_from_configmap": None, "secret_mounts": []
        }
        for clause_result in optional_clauses:
            if clause_result and isinstance(clause_result, dict): # Cada cláusula opcional devuelve un dict si coincide
                if "custom_args" in clause_result:
                    instruction["custom_args"] = clause_result["custom_args"]
                elif "args_from_configmap" in clause_result:
                    instruction["args_from_configmap"] = clause_result["args_from_configmap"]
                # secret_mount_clause no devuelve un dict con una clave única, es el dict mismo.
                # Si (secret_mount_clause)* se transforma, *optional_clauses tendrá una lista de estos.
                # La gramática (secret_mount_clause)* significa que map_secret_mount se llamará varias veces
                # y sus resultados se pasarán como argumentos individuales a execute_script después de los fijos.
                elif clause_result.get("type") == "secret_mount_spec":
                     instruction["secret_mounts"].append(clause_result)
        return instruction

    # --- Transformadores para Comandos de Proyecto/Entorno ---
    @v_args(inline=True)
    def create_project_cmd(self, create_kw_val, project_keyword_val, user_project_name_str):
        return {"action": constants.ACTION_CREATE_PROJECT, "type": constants.LOGICAL_TYPE_PROJECT,
                "user_project_name": user_project_name_str.lower()}

    @v_args(inline=True)
    def specified_project_name_transformer(self, project_keyword_val, name_str): # Para PROJECT_KW NAME
        return name_str.lower() # Devuelve solo el nombre, ya en minúsculas

    @v_args(inline=True)
    def this_project_transformer(self, this_keyword_val, project_keyword_val): # Para THIS_KW PROJECT_KW
        return "THIS_PROJECT_CONTEXT"

    @v_args(inline=True)
    def project_target_clause(self, for_or_from_keyword_val, project_specifier):
        # project_specifier es el resultado de specified_project_name_transformer o this_project_transformer
        return project_specifier 

    @v_args(inline=True)
    def create_env_cmd(self, create_kw_val, env_keyword_val, env_name_str, project_specifier=None):
        # project_specifier es el resultado de project_target_clause (opcional)
        return {"action": constants.ACTION_CREATE_ENV, "type": constants.LOGICAL_TYPE_ENVIRONMENT,
                "env_name": env_name_str.lower(), "project_name_specifier": project_specifier}

    @v_args(inline=True) 
    def list_projects_cmd(self, list_kw_val, project_keyword_val, plural_s_token=None):
        return {"action": constants.ACTION_LIST_PROJECTS, "type": constants.LOGICAL_TYPE_PROJECT}

    # Transformadores para la estructura GET unificada
    @v_args(inline=True)
    def get_script_target_transformer(self, script_keyword_val, script_name_str):
        return {
            "target_kind": constants.RESOURCE_SCRIPT, 
            "name": script_name_str.lower()
        }



    @v_args(inline=True)
    def get_project_by_name_transformer(self, project_keyword_val, project_name_str):
        return {
            "target_kind": constants.LOGICAL_TYPE_PROJECT, 
            "project_name_specifier": project_name_str.lower()
        }

    @v_args(inline=True)
    def get_this_project_transformer(self, this_keyword_val, project_keyword_val):
        return {
            "target_kind": constants.LOGICAL_TYPE_PROJECT, 
            "project_name_specifier": "THIS_PROJECT_CONTEXT"
        }
    
    # get_target_choice no necesita un método de transformer, ya que @v_args(inline=True) en 
    # get_command_transformer pasará el resultado del hijo que hizo match.
    @v_args(inline=True)
    def get_target_choice(self, chosen_target_payload):
        # This method is called for the rule:
        # get_target_choice: get_script_target_rule | get_project_by_name_target_rule | get_this_project_target_rule
        # The argument 'chosen_target_payload' will be the dictionary returned by
        # one of the above three _transformer methods that matched.
        return chosen_target_payload # Simply pass the dictionary through

    @v_args(inline=True) 
    def get_command_transformer(self, get_keyword_val, target_payload_dict):
        # Now, target_payload_dict should correctly be the dictionary returned by get_target_choice
        
        target_kind = target_payload_dict["target_kind"] # This should no longer error
        action_to_dispatch = None
        final_instruction_dict = {
            "type": target_kind 
        }

        if target_kind == constants.RESOURCE_SCRIPT:
            action_to_dispatch = constants.ACTION_GET 
            final_instruction_dict["name"] = target_payload_dict["name"]
        elif target_kind == constants.LOGICAL_TYPE_PROJECT:
            action_to_dispatch = constants.ACTION_GET_PROJECT
            final_instruction_dict["project_name_specifier"] = target_payload_dict["project_name_specifier"]
        else:
            action_to_dispatch = "ERROR_UNKNOWN_GET_TARGET"
            final_instruction_dict["error_details"] = target_payload_dict
        
        final_instruction_dict["action"] = action_to_dispatch
        return final_instruction_dict
    
    @v_args(inline=True) 
    def update_project_cmd(self, update_kw_val, project_kw_val, old_name_str, to_kw_val, new_name_str):
        return {"action": constants.ACTION_UPDATE_PROJECT, "type": constants.LOGICAL_TYPE_PROJECT,
                "old_project_name": old_name_str.lower(), "new_project_name": new_name_str.lower()}

    @v_args(inline=True) 
    def drop_project_cmd(self, drop_kw_val, project_kw_val, project_name_str):
        return {"action": constants.ACTION_DROP_PROJECT, "type": constants.LOGICAL_TYPE_PROJECT,
                "user_project_name": project_name_str.lower()}

    @v_args(inline=True) 
    def delete_env_cmd(self, drop_kw_val, env_kw_val, env_name_str, project_specifier=None):
        return {"action": constants.ACTION_DROP_ENV, "type": constants.LOGICAL_TYPE_ENVIRONMENT,
                "env_name": env_name_str.lower(), "project_name_specifier": project_specifier}
    
    @v_args(inline=True) 
    def use_project_env_cmd(self, use_kw_val, project_kw_val, project_name_str, env_kw_val, env_name_str):
        return {"action": constants.ACTION_USE_PROJECT_ENV, "type": constants.LOGICAL_TYPE_PROJECT, 
                "user_project_name": project_name_str.lower(), "env_name": env_name_str.lower()}

    # --- Transformadores Principales `command` y `start` ---
    def command(self, items):
        # Cada método de transformación de comando (ej. create_project_cmd) devuelve un único diccionario.
        # 'items' será una lista que contiene ese diccionario.
        if items and isinstance(items[0], dict):
            return items[0]
        print(f"[DEBUG TRANSFORMER] Warning: 'command' transformer received unexpected items: {items}")
        return {"action": "TRANSFORM_ERROR_COMMAND", "details": str(items)}

    def start(self, items):
        if items and isinstance(items[0], dict):
            return items[0]
        print(f"[DEBUG TRANSFORMER] Warning: 'start' transformer received unexpected items: {items}")
        return {"action": "PARSE_START_ERROR", "details": str(items)}