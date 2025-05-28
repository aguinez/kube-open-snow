# kubeSol/parser/transformer.py
from lark import Transformer, v_args, Token
from kubeSol import constants # Updated import

class KubeTransformer(Transformer): # Class name kept as KubeTransformer as it's tied to Lark's convention
    # --- Terminal Transformers ---
    def NAME(self, token: Token):
        return str(token.value)

    def ESCAPED_STRING(self, token: Token):
        return token.value[1:-1]

    # --- Basic Field/Fields Transformers ---
    @v_args(inline=True)
    def field(self, key_name_str: str, value_str: str):
        return key_name_str, value_str

    def fields(self, field_list: list):
        return dict(field_list)
    
    # --- Keyword Terminals Transformers ---
    def SECRET_KW(self, token: Token): return str(token.value).upper()
    def CONFIGMAP_KW(self, token: Token): return str(token.value).upper()
    def PARAMETER_KW(self, token: Token): return str(token.value).upper()
    def SCRIPT_KW(self, token: Token): return str(token.value).upper() 

    def PYTHON_KW(self, token: Token): return constants.SCRIPT_TYPE_PYTHON
    def PYSPARK_KW(self, token: Token): return constants.SCRIPT_TYPE_PYSPARK
    def SQL_SPARK_KW(self, token: Token): return constants.SCRIPT_TYPE_SQL_SPARK
    
    def K8S_JOB_KW(self, token: Token): return constants.SCRIPT_ENGINE_K8S_JOB
    def SPARK_OPERATOR_KW(self, token: Token): return constants.SCRIPT_ENGINE_SPARK_OPERATOR

    # --- Rule Transformers for Resource Types and Names ---
    def resource_type_value_rule(self, items: list):
        return items[0]

    def resource_name(self, items: list):
        return items[0]

    def script_name(self, items: list): 
        return items[0]

    def script_type_value(self, items: list):
        return items[0]

    def script_engine_value(self, items: list):
        return items[0]

    # --- Transformers for script_content_fields in CREATE SCRIPT ---
    @v_args(inline=True)
    def script_code_field(self, value_str: str): 
        print(f"[DEBUG TRANSFORMER] script_code_field producing: ({constants.SCRIPT_CM_KEY_CODE}, '{value_str[:30]}...')")
        return (constants.SCRIPT_CM_KEY_CODE, value_str)

    @v_args(inline=True)
    def script_code_from_file_field(self, file_path_str: str): 
        print(f"[DEBUG TRANSFORMER] script_code_from_file_field producing: ({constants.SCRIPT_CM_KEY_CODE_FROM_FILE}, '{file_path_str}')")
        return (constants.SCRIPT_CM_KEY_CODE_FROM_FILE, file_path_str)

    @v_args(inline=True)
    def script_params_spec_field(self, value_str: str): 
        print(f"[DEBUG TRANSFORMER] script_params_spec_field producing: ({constants.SCRIPT_CM_KEY_PARAMS_SPEC}, '{value_str[:30]}...')")
        return (constants.SCRIPT_CM_KEY_PARAMS_SPEC, value_str)

    @v_args(inline=True)
    def script_description_field(self, value_str: str): 
        print(f"[DEBUG TRANSFORMER] script_description_field producing: ({constants.SCRIPT_CM_KEY_DESCRIPTION}, '{value_str[:30]}...')")
        return (constants.SCRIPT_CM_KEY_DESCRIPTION, value_str)

    def script_content_fields(self, field_tuples_list: list): 
        print(f"[DEBUG TRANSFORMER] script_content_fields received list of tuples: {field_tuples_list}")
        try:
            content_dict = dict(field_tuples_list) 
            print(f"[DEBUG TRANSFORMER] script_content_fields successfully created dict: {content_dict}")
            return content_dict
        except Exception as e:
            print(f"[DEBUG TRANSFORMER] ERROR in script_content_fields creating dict: {e}. Field list was: {field_tuples_list}")
            raise 

    # --- Transformers for command structures ---
    def create_resource(self, items: list):
        print(f"[DEBUG TRANSFORMER] create_resource items: {items}")
        return {"action": constants.ACTION_CREATE, "type": items[0], "name": items[1], "fields": items[2]}

    def delete_resource(self, items: list):
        print(f"[DEBUG TRANSFORMER] delete_resource items: {items}")
        return {"action": constants.ACTION_DELETE, "type": items[0], "name": items[1]}

    def update_resource(self, items: list):
        print(f"[DEBUG TRANSFORMER] update_resource items: {items}")
        return {"action": constants.ACTION_UPDATE, "type": items[0], "name": items[1], "fields": items[2]}

    def create_script(self, items: list):
        print(f"[DEBUG TRANSFORMER] create_script received items: {items}")
        
        script_resource_type = items[0] 
        script_identifier = items[1]    
        script_type_constant = items[2] 
        
        script_engine_constant = None 
        script_content_dictionary = None 

        if len(items) == 5: 
            script_engine_constant = items[3]
            script_content_dictionary = items[4]
        elif len(items) == 4: 
            script_content_dictionary = items[3] 
        else:
            raise ValueError(f"Internal parsing error in create_script: Unexpected number of items. Items: {items}")

        executor_details = {} 
        if script_content_dictionary:
            executor_details.update(script_content_dictionary)
        executor_details[constants.SCRIPT_CM_KEY_TYPE] = script_type_constant
        
        if script_engine_constant: 
            executor_details[constants.SCRIPT_CM_KEY_ENGINE] = script_engine_constant
        
        print(f"[DEBUG TRANSFORMER] create_script returning: name='{script_identifier}', details={executor_details}")
        return {
            "action": constants.ACTION_CREATE,
            "type": script_resource_type, 
            "name": script_identifier,
            "details": executor_details
        }

    def get_script(self, items: list):
        print(f"[DEBUG TRANSFORMER] get_script items: {items}")
        return {"action": constants.ACTION_GET, "type": items[0], "name": items[1]}

    def list_scripts(self, items: list):
        print(f"[DEBUG TRANSFORMER] list_scripts items: {items}")
        return {"action": constants.ACTION_LIST, "type": items[0]} 

    def delete_script(self, items: list):
        print(f"[DEBUG TRANSFORMER] delete_script items: {items}")
        return {"action": constants.ACTION_DELETE, "type": items[0], "name": items[1]}

    # --- Transformers for UPDATE SCRIPT fields ---
    @v_args(inline=True)
    def update_script_code_field(self, value_str: str): 
        return (constants.SCRIPT_CM_KEY_CODE, value_str)

    @v_args(inline=True)
    def update_script_params_spec_field(self, value_str: str): 
        return (constants.SCRIPT_CM_KEY_PARAMS_SPEC, value_str)

    @v_args(inline=True)
    def update_script_description_field(self, value_str: str): 
        return (constants.SCRIPT_CM_KEY_DESCRIPTION, value_str)

    @v_args(inline=True)
    def update_script_engine_field(self, engine_constant_str: str): 
        return (constants.SCRIPT_CM_KEY_ENGINE, engine_constant_str)

    def script_update_fields(self, field_tuples_list: list): 
        print(f"[DEBUG TRANSFORMER] script_update_fields received: {field_tuples_list}")
        return dict(field_tuples_list)

    def update_script(self, items: list):
        print(f"[DEBUG TRANSFORMER] update_script items: {items}")
        script_resource_type = items[0]  
        script_identifier = items[1]     
        update_fields_dictionary = items[2] 
        return {
            "action": constants.ACTION_UPDATE,
            "type": script_resource_type,
            "name": script_identifier,
            "updates": update_fields_dictionary
        }

    # --- Transformers for EXECUTE SCRIPT clauses ---
    @v_args(inline=True)
    def custom_param(self, param_name_str: str, param_value_str: str): 
        return (param_name_str, param_value_str)

    def custom_params(self, param_tuples_list: list): 
        return dict(param_tuples_list)

    def with_args_clause(self, items: list):
        return {"custom_args": items[0]}

    @v_args(inline=True)
    def configmap_name(self, name_str: str): 
        return name_str
    
    @v_args(inline=True)
    def prefix_string(self, prefix_str: str): 
        return prefix_str

    def with_params_cm_clause(self, items: list):
        cm_info_dict = {"cm_name": items[0]} 
        if len(items) > 1 and items[1] is not None: 
            cm_info_dict["key_prefix"] = items[1]
        else:
            cm_info_dict["key_prefix"] = "" 
        return {"args_from_configmap": cm_info_dict}

    def execute_script(self, items: list):
        print(f"[DEBUG TRANSFORMER] execute_script received items: {items}")

        script_resource_type = items[0] 
        script_identifier = items[1]    

        instruction_dict = { 
            "action": constants.ACTION_EXECUTE,
            "type": script_resource_type,
            "name": script_identifier,
            "custom_args": None,
            "args_from_configmap": None
        }
        
        for i in range(2, len(items)):
            clause_data = items[i]
            if clause_data is not None: 
                if "custom_args" in clause_data:
                    instruction_dict["custom_args"] = clause_data["custom_args"]
                elif "args_from_configmap" in clause_data:
                    instruction_dict["args_from_configmap"] = clause_data["args_from_configmap"]
        
        print(f"[DEBUG TRANSFORMER] execute_script returning: {instruction_dict}")
        return instruction_dict

    # --- General command and start rules ---
    def command(self, items: list):
        return items[0]

    def start(self, items: list):
        return items[0]