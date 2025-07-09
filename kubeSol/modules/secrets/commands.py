# kubesol/modules/secrets/commands.py
from lark import Lark, Transformer, v_args
import os
import sys

from kubesol.dispatch.command_registry import global_command_registry
from kubesol.core.context import KubeSolContext
from kubesol.modules.secrets import handlers

# --- 1. Define the Lark Grammar for Secrets Module ---
_SECRETS_COMMANDS_GRAMMAR = r"""
    ?start: command [SEMICOLON]

    command: create_secret_cmd
           | get_secret_cmd
           | delete_secret_cmd
           | update_secret_cmd

    // CREATE SECRET <name> FROM FILE <path>
    create_secret_cmd: "CREATE" "SECRET" SECRET_NAME "FROM" "FILE" FILE_PATH -> create_secret_from_file

    // GET SECRET <name>
    get_secret_cmd: "GET" "SECRET" SECRET_NAME -> get_secret

    // DELETE SECRET <name>
    delete_secret_cmd: "DELETE" "SECRET" SECRET_NAME -> delete_secret

    // UPDATE SECRET <name> FROM FILE <path>
    update_secret_cmd: "UPDATE" "SECRET" SECRET_NAME "FROM" "FILE" FILE_PATH -> update_secret_from_file

    // --- Tokens ---
    SECRET: "SECRET"i
    CREATE: "CREATE"i
    GET: "GET"i
    DELETE: "DELETE"i
    UPDATE: "UPDATE"i
    FROM: "FROM"i
    FILE: "FILE"i

    SECRET_NAME: /[a-zA-Z0-9_-]+/ 
    FILE_PATH: ESCAPED_STRING

    SEMICOLON: ";"

    ESCAPED_STRING : /"([^"]|\\")*"/ | /'([^']|\\')*'/

    %import common.WS
    %ignore WS
    %ignore SEMICOLON
"""

# Compile the Lark parser for this module
_secrets_parser = Lark(_SECRETS_COMMANDS_GRAMMAR, start='command', parser='earley', propagate_positions=False)

# --- 2. Define the Transformer for Secrets Module ---
@v_args(inline=True)
class SecretTransformer(Transformer):
    def command(self, parsed_command_dict):
        return parsed_command_dict

    def SECRET_NAME(self, s):
        return str(s)

    def FILE_PATH(self, s):
        return s.strip("\"'").replace('\\"', '"').replace("\\'", "'")

    # --- Command Transformations (Firmas Corregidas) ---
    # Con v_args(inline=True), solo se pasan los resultados de las reglas o tokens nombrados
    # que no son literales directos de la regla. Los literales como "CREATE", "SECRET", etc.
    # son consumidos por la gramática pero no se pasan como argumentos al método.

    # create_secret_cmd: CREATE SECRET SECRET_NAME FROM FILE FILE_PATH
    # Espera solo SECRET_NAME y FILE_PATH
    def create_secret_from_file(self, secret_name_value, file_path_value):
        return {"command_type": "create_secret_from_file", "secret_name": secret_name_value, "file_path": file_path_value}

    # get_secret_cmd: GET SECRET SECRET_NAME
    # Espera solo SECRET_NAME
    def get_secret(self, secret_name_value):
        return {"command_type": "get_secret", "secret_name": secret_name_value}

    # delete_secret_cmd: DELETE SECRET SECRET_NAME
    # Espera solo SECRET_NAME
    def delete_secret(self, secret_name_value):
        return {"command_type": "delete_secret", "secret_name": secret_name_value}

    # update_secret_cmd: UPDATE SECRET SECRET_NAME FROM FILE FILE_PATH
    # Espera solo SECRET_NAME y FILE_PATH
    def update_secret_from_file(self, secret_name_value, file_path_value):
        return {"command_type": "update_secret_from_file", "secret_name": secret_name_value, "file_path": file_path_value}

    # Métodos para los tokens (asegura que retornen su valor de string)
    # Estos métodos son para los tokens que se usan como parte de una regla
    # y quieres que su valor sea pasado si no son literales directos en el método transformador.
    # En este caso, al estar 'inline=True', si estos tokens son literales en las reglas de comando,
    # no se pasarán explícitamente a los métodos de transformación de comandos.
    # Se mantienen aquí por si acaso se usan en otras reglas más complejas, o para un futuro.
    def CREATE(self, token): return str(token)
    def SECRET(self, token): return str(token)
    def GET(self, token): return str(token)
    def DELETE(self, token): return str(token)
    def UPDATE(self, token): return str(token)
    def FROM(self, token): return str(token)
    def FILE(self, token): return str(token)
    def SEMICOLON(self, token): return None

# --- 3. Module's Entry Point for Dispatcher (and Self-Registration) ---

# Define the patterns this module claims to handle
SECRETS_COMMAND_PATTERNS = [
    "CREATE SECRET",
    "GET SECRET",
    "DELETE SECRET",
    "UPDATE SECRET"
]

def parse_and_handle_command(raw_command_string: str, context: KubeSolContext) -> bool:
    print(f"DEBUG_SECRETS_COMMANDS: Comando recibido para parsing: '{raw_command_string}'")
    try:
        tree = _secrets_parser.parse(raw_command_string)
        print(f"DEBUG_SECRETS_COMMANDS: Parseado exitosamente en árbol: {tree.pretty()}")
        
        parsed_args = SecretTransformer().transform(tree)
        print(f"DEBUG_SECRETS_COMMANDS: Argumentos transformados: {parsed_args}")

        command_type = parsed_args.get("command_type")

        handler_map = {
            "create_secret_from_file": handlers.handle_create_secret_from_file,
            "get_secret": handlers.handle_get_secret,
            "delete_secret": handlers.handle_delete_secret,
            "update_secret_from_file": handlers.handle_update_secret_from_file,
        }

        target_handler_func = handler_map.get(command_type)

        if target_handler_func:
            target_handler_func(parsed_args=parsed_args, context=context)
            return True
        else:
            return False

    except Exception as e:
        print(f"DEBUG_SECRETS_COMMANDS: Falló el parsing/manejo para '{raw_command_string}': {type(e).__name__} - {e}")
        # import traceback; traceback.print_exc() # Descomentar para depuración
        return False

# --- Auto-Registro del Módulo ---
global_command_registry.register_module_commands(
    module_name="secrets",
    patterns=SECRETS_COMMAND_PATTERNS,
    handler_function=parse_and_handle_command
)
print("DEBUG_SECRETS_COMMANDS: secrets/commands.py cargado e intentando registrarse.")