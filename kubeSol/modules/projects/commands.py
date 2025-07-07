# kubesol/modules/projects/commands.py
from lark import Lark, Transformer, v_args
import sys
import os

from kubesol.dispatch.command_registry import global_command_registry
from kubesol.core.context import KubeSolContext
from kubesol.modules.projects import handlers

# --- 1. Definición de la Gramática Lark para Comandos de Proyectos ---
_PROJECTS_COMMANDS_GRAMMAR = r"""
    ?start: command [SEMICOLON]

    command: create_project_cmd
           | create_env_cmd
           | list_projects_cmd
           | get_project_cmd
           | update_project_cmd
           | drop_project_cmd
           | drop_env_cmd
           | use_project_env_cmd

    create_project_cmd: CREATE PROJECT PROJECT_NAME -> create_project
    create_env_cmd: CREATE ENV ENV_NAME (project_specifier_clause)? (DEPENDS ON ENV_NAME)? -> create_environment
    
    // CAMBIO AQUÍ: list_projects_cmd ahora usa el token plural PROJECTS_PLURAL
    list_projects_cmd: LIST PROJECTS_PLURAL -> list_projects 
    
    get_project_cmd: GET PROJECT (PROJECT_NAME | KEYWORD_THIS_PROJECT) -> get_project
    update_project_cmd: UPDATE PROJECT PROJECT_NAME TO PROJECT_NAME -> update_project
    drop_project_cmd: DROP PROJECT PROJECT_NAME -> drop_project 
    drop_env_cmd: DROP ENV ENV_NAME (project_specifier_clause)? -> drop_environment
    use_project_env_cmd: USE PROJECT PROJECT_NAME ENV ENV_NAME -> use_project_environment

    project_specifier_clause: FOR (KEYWORD_THIS_PROJECT | PROJECT PROJECT_NAME) -> for_project_specifier

    KEYWORD_THIS_PROJECT: THIS PROJECT 

    PROJECT_NAME: /[a-zA-Z0-9_-]+/
    ENV_NAME: /[a-zA-Z0-9_-]+/

    // --- Definición de Tokens ---
    CREATE: "CREATE"i
    PROJECT: "PROJECT"i // Token singular para PROJECT
    PROJECTS_PLURAL: "PROJECTS"i // NUEVO: Token plural para PROJECTS
    ENV: "ENV"i | "ENVIRONMENT"i
    FOR: "FOR"i
    DEPENDS: "DEPENDS"i
    ON: "ON"i
    LIST: "LIST"i
    GET: "GET"i
    UPDATE: "UPDATE"i
    TO: "TO"i
    DROP: "DROP"i
    FROM: "FROM"i
    USE: "USE"i
    THIS: "THIS"i

    SEMICOLON: ";" 
    
    %import common.WS
    %ignore WS
    %ignore SEMICOLON 
"""

# Compila el parser Lark para este módulo
_projects_parser = Lark(_PROJECTS_COMMANDS_GRAMMAR, start='command', parser='earley', propagate_positions=False) 

# --- 2. Definición del Transformer para Comandos de Proyectos ---
@v_args(inline=True)
class ProjectTransformer(Transformer):
    def command(self, parsed_command_dict):
        return parsed_command_dict

    def PROJECT_NAME(self, s): return str(s)
    def ENV_NAME(self, s): return str(s)
    
    def for_project_specifier(self, for_token, specifier_part_one, project_name_value=None):
        if isinstance(specifier_part_one, str) and specifier_part_one.lower() == "this":
            return "THIS_PROJECT_CONTEXT"
        else:
            return project_name_value 

    # --- Métodos de Transformación de Comandos ---

    # create_project_cmd: CREATE PROJECT PROJECT_NAME
    def create_project(self, create_token, project_token, project_name_value):
        return {"command_type": "create_project", "project_name": project_name_value}

    # create_env_cmd: CREATE ENV ENV_NAME (project_specifier_clause)? (DEPENDS ON ENV_NAME)?
    def create_environment(self, create_token, env_token, env_name_value, project_specifier=None, depends_on_token_1=None, on_token=None, depends_on_env_value=None):
        return {"command_type": "create_environment", "env_name": env_name_value, "project_name_specifier": project_specifier, "depends_on_env": depends_on_env_value}

    # list_projects_cmd: LIST PROJECTS_PLURAL
    # CAMBIO AQUÍ: La firma del método ahora coincide con la regla de gramática actualizada
    def list_projects(self, list_token, projects_plural_token): 
        return {"command_type": "list_projects"}

    # get_project_cmd: GET PROJECT (PROJECT_NAME | KEYWORD_THIS_PROJECT)
    def get_project(self, get_token, project_token, project_name_or_keyword_this_project):
        if isinstance(project_name_or_keyword_this_project, str) and project_name_or_keyword_this_project.lower() == 'this project':
            return {"command_type": "get_project", "project_name_specifier": "THIS_PROJECT_CONTEXT"}
        return {"command_type": "get_project", "project_name_specifier": project_name_or_keyword_this_project}

    # update_project_cmd: UPDATE PROJECT PROJECT_NAME TO PROJECT_NAME
    def update_project(self, update_token, project_token_1, old_project_name_value, to_token, new_project_name_value):
        return {"command_type": "update_project", "old_project_name": old_project_name_value, "new_project_name": new_project_name_value}
    
    # drop_project_cmd: DROP PROJECT PROJECT_NAME
    def drop_project(self, drop_token, project_token, project_name_value):
        return {"command_type": "drop_project", "project_name": project_name_value}
    
    # drop_env_cmd: DROP ENV ENV_NAME (project_specifier_clause)?
    def drop_environment(self, drop_token, env_token, env_name_value, project_specifier=None):
        return {"command_type": "drop_environment", "env_name": env_name_value, "project_name_specifier": project_specifier}
    
    # use_project_env_cmd: USE PROJECT PROJECT_NAME ENV ENV_NAME
    def use_project_environment(self, use_token, project_token_1, project_name_value, env_token, env_name_value):
        return {"command_type": "use_project_environment", "project_name": project_name_value, "env_name": env_name_value}

    # Métodos para los tokens (asegura que retornen su valor de string)
    def CREATE(self, token): return str(token)
    def PROJECT(self, token): return str(token)
    def PROJECTS_PLURAL(self, token): return str(token) # NUEVO: Método para el token plural
    def ENV(self, token): return str(token)
    def FOR(self, token): return str(token)
    def DEPENDS(self, token): return str(token)
    def ON(self, token): return str(token)
    def LIST(self, token): return str(token)
    def GET(self, token): return str(token)
    def UPDATE(self, token): return str(token)
    def TO(self, token): return str(token)
    def DROP(self, token): return str(token)
    def FROM(self, token): return str(token)
    def USE(self, token): return str(token)
    def THIS(self, token): return str(token)
    def SEMICOLON(self, token): return None

# Patrones de comando para el registro global
PROJECTS_COMMAND_PATTERNS = [
    "CREATE PROJECT", "CREATE ENV", "CREATE ENVIRONMENT",
    "LIST PROJECTS", "GET PROJECT", "UPDATE PROJECT",
    "DROP PROJECT", "DROP ENVIRONMENT", "DROP ENV",
    "USE PROJECT"
]

def parse_and_handle_command(raw_command_string: str, context: KubeSolContext) -> bool:
    print(f"DEBUG_PROJECT_COMMANDS: Comando recibido para parsing: '{raw_command_string}'")
    try:
        tree = _projects_parser.parse(raw_command_string)
        print(f"DEBUG_PROJECTS_COMMANDS: Parseado exitosamente en árbol: {tree.pretty()}")
        
        parsed_args = ProjectTransformer().transform(tree)
        print(f"DEBUG_PROJECTS_COMMANDS: Argumentos transformados: {parsed_args}")

        command_type = parsed_args.get("command_type")

        handler_map = {
            "create_project": handlers.handle_create_project, "create_environment": handlers.handle_create_environment,
            "list_projects": handlers.handle_list_projects, "get_project": handlers.handle_get_project,
            "update_project": handlers.handle_update_project, "drop_project": handlers.handle_drop_project,
            "drop_environment": handlers.handle_drop_environment, "use_project_environment": handlers.handle_use_project_environment,
        }

        target_handler_func = handler_map.get(command_type)

        if target_handler_func:
            target_handler_func(parsed_args=parsed_args, context=context)
            return True
        else:
            return False

    except Exception as e:
        print(f"DEBUG_PROJECTS_COMMANDS: Falló el parsing/manejo para '{raw_command_string}': {type(e).__name__} - {e}")
        return False

global_command_registry.register_module_commands(
    module_name="projects",
    patterns=PROJECTS_COMMAND_PATTERNS,
    handler_function=parse_and_handle_command
)
print("DEBUG_PROJECTS_COMMANDS: projects/commands.py cargado e intentando registrarse.")