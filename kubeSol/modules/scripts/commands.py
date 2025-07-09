# kubesol/modules/scripts/commands.py
from lark import Lark, Transformer, v_args
import os
import sys

from kubesol.dispatch.command_registry import global_command_registry
from kubesol.core.context import KubeSolContext
from kubesol.modules.scripts import handlers # Import the handlers from the same module

# --- 1. Define the Lark Grammar for Scripts Module ---
# CORREGIDO: Expresión regular para IMAGE_NAME (WORKAROUND - muy permisiva).
_SCRIPTS_COMMANDS_GRAMMAR = r"""
    ?start: command [SEMICOLON]

    command: execute_script_cmd

    execute_script_cmd: EXECUTE SCRIPT optional_job_name FROM FILE FILE_PATH script_options -> execute_script_job

    optional_job_name: JOB_NAME | 

    script_options: (with_image_clause | with_params_clause)* | 

    with_image_clause: WITH IMAGE IMAGE_NAME -> with_image
    with_params_clause: WITH PARAMS FROM FILE FILE_PATH -> with_params_from_file

    // --- Tokens ---
    EXECUTE: "EXECUTE"i
    SCRIPT: "SCRIPT"i
    FROM: "FROM"i
    FILE: "FILE"i
    WITH: "WITH"i
    IMAGE: "IMAGE"i
    PARAMS: "PARAMS"i

    JOB_NAME: /[a-zA-Z0-9_-]+/ 
    FILE_PATH: ESCAPED_STRING
    
    // CORREGIDO (WORKAROUND): Expresión regular para IMAGE_NAME.
    // Usamos una regex muy permisiva para evitar el error persistente con el guion y el backslash.
    // Esto coincide con cualquier secuencia de caracteres que no sea espacio, comillas o punto y coma.
    // La VALIDACIÓN REAL del formato de la imagen DEBERÁ hacerse en el código Python del manager.
    IMAGE_NAME: /[^\s"';]+/ // <--- CORRECCIÓN AQUÍ (regex muy permisiva)

    SEMICOLON: ";"

    ESCAPED_STRING : /"([^"]|\\")*"/ | /'([^']|\\')*'/ 

    %import common.WS
    %ignore WS
    %ignore SEMICOLON
"""

# Compile the Lark parser for this module
_scripts_parser = Lark(_SCRIPTS_COMMANDS_GRAMMAR, start='command', parser='earley', propagate_positions=False)

# --- 2. Define el Transformer para Scripts Module ---
@v_args(inline=True)
class ScriptTransformer(Transformer):
    def command(self, parsed_command_dict):
        return parsed_command_dict

    def JOB_NAME(self, s):
        return str(s)

    def FILE_PATH(self, s):
        return s.strip("\"'").replace('\\"', '"').replace("\\'", "'")

    def IMAGE_NAME(self, s):
        return str(s)

    def optional_job_name(self, job_name_value=None):
        return job_name_value 

    def script_options(self, *items):
        return list(items)

    def with_image(self, with_token, image_token, image_name_value):
        return {"image": image_name_value}

    def with_params_from_file(self, with_token, params_token, from_token, file_token, file_path_value):
        return {"params_yaml_file_path": file_path_value}

    def execute_script_job(self, execute_token, script_token, job_name_result, from_token, file_token, script_path_value, script_options_list):
        job_name = job_name_result
        script_path = script_path_value
        image = None
        params_yaml_file_path = None

        for option_dict in script_options_list:
            if isinstance(option_dict, dict):
                if "image" in option_dict:
                    image = option_dict["image"]
                if "params_yaml_file_path" in option_dict:
                    params_yaml_file_path = option_dict["params_yaml_file_path"]

        return {
            "command_type": "execute_script_job",
            "job_name": job_name,
            "script_path_local": script_path,
            "image": image,
            "params_yaml_file_path": params_yaml_file_path
        }

    def EXECUTE(self, token): return str(token)
    def SCRIPT(self, token): return str(token)
    def FROM(self, token): return str(token)
    def FILE(self, token): return str(token)
    def WITH(self, token): return str(token)
    def IMAGE(self, token): return str(token)
    def PARAMS(self, token): return str(token)
    def SEMICOLON(self, token): return None

# --- 3. Punto de Entrada del Módulo para el Despachador (y Auto-Registro) ---

SCRIPTS_COMMAND_PATTERNS = [
    "EXECUTE SCRIPT"
]

def parse_and_handle_command(raw_command_string: str, context: KubeSolContext) -> bool:
    print(f"DEBUG_SCRIPTS_COMMANDS: Comando recibido para parsing: '{raw_command_string}'")
    try:
        tree = _scripts_parser.parse(raw_command_string)
        print(f"DEBUG_SCRIPTS_COMMANDS: Parseado exitosamente en árbol: {tree.pretty()}")
        
        parsed_args = ScriptTransformer().transform(tree)
        print(f"DEBUG_SCRIPTS_COMMANDS: Argumentos transformados: {parsed_args}")

        command_type = parsed_args.get("command_type")

        handler_map = {
            "execute_script_job": handlers.handle_execute_script,
        }

        target_handler_func = handler_map.get(command_type)

        if target_handler_func:
            target_handler_func(parsed_args=parsed_args, context=context)
            return True
        else:
            return False

    except Exception as e:
        print(f"DEBUG_SCRIPTS_COMMANDS: Falló el parsing/manejo para '{raw_command_string}': {type(e).__name__} - {e}")
        return False

# --- Auto-Registro del Módulo ---
global_command_registry.register_module_commands(
    module_name="scripts",
    patterns=SCRIPTS_COMMAND_PATTERNS,
    handler_function=parse_and_handle_command
)
print("DEBUG_SCRIPTS_COMMANDS: scripts/commands.py cargado e intentando registrarse.")