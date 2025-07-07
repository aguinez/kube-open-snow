# kubesol/dispatch/command_registry.py
from typing import Callable, List, Tuple
from kubesol.core.context import KubeSolContext # Importamos KubeSolContext para tipado

# Define el tipo para la función de manejo de comandos de un módulo
# Esta función intentará parsear y manejar una cadena de comando cruda.
# Debe retornar True si el comando fue manejado exitosamente, False de lo contrario.
ModuleCommandHandler = Callable[[str, KubeSolContext], bool]

class CommandRegistry:
    """
    Un registro Singleton para almacenar los patrones de comando y sus
    funciones de manejo asociadas de los diferentes módulos.
    """
    _instance = None # Para el patrón Singleton

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CommandRegistry, cls).__new__(cls)
            # Inicializa el registro cuando se crea la primera instancia
            cls._instance._registered_modules: List[Tuple[str, ModuleCommandHandler]] = []
            print("INFO: CommandRegistry singleton initialized.")
        return cls._instance

    def register_module_commands(self, module_name: str, patterns: List[str], handler_function: ModuleCommandHandler):
        """
        Registra los patrones de comando de un módulo y su función de manejo.
        
        Args:
            module_name (str): El nombre del módulo que se está registrando (solo para depuración/logging).
            patterns (List[str]): Una lista de cadenas de inicio que este módulo puede manejar (ej. ["CREATE PROJECT", "LIST PROJECTS"]).
                                   Se recomienda ordenar de más específico a menos específico dentro del módulo.
            handler_function (ModuleCommandHandler): La función del módulo que intentará parsear y manejar
                                                      la cadena de comando completa.
        """
        for pattern in patterns:
            # Almacenamos el patrón y la función del manejador.
            # Podríamos añadir más metadatos (ej., prioridad, nombre del módulo) si fuera necesario.
            # Mantener un registro plano para simplificar la iteración del despachador.
            self._registered_modules.append((pattern, handler_function))
            print(f"DEBUG_REGISTRY: Module '{module_name}' registered pattern: '{pattern}'")
        
        # Opcional: Ordenar los patrones registrados por longitud (más largos primero)
        # para priorizar coincidencias más específicas en el despachador.
        self._registered_modules.sort(key=lambda x: len(x[0]), reverse=True)
        print(f"DEBUG_REGISTRY: Current registered patterns count: {len(self._registered_modules)}")


    def get_registered_commands(self) -> List[Tuple[str, ModuleCommandHandler]]:
        """
        Retorna la lista de todos los patrones de comando registrados y sus funciones de manejo.
        """
        return self._registered_modules

# Instancia global del registro de comandos
global_command_registry = CommandRegistry()