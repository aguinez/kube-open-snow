# kubesol/dispatch/dispatcher.py
from kubesol.dispatch.command_registry import global_command_registry
from kubesol.core.context import KubeSolContext
import traceback

def execute_command(command_string: str, context: KubeSolContext):
    """
    Ejecuta un comando de KubeSol. Intenta encontrar el módulo responsable
    usando el CommandRegistry global y delega el parsing y manejo completo a ese módulo.
    """
    command_string_lower = command_string.strip().lower()
    print(f"DEBUG_DISPATCHER: Comando recibido (original): '{command_string}' (Minúsculas: '{command_string_lower}')") # <--- AÑADIDA LÍNEA DE DEBUG
    
    matched_pattern_found = False

    for pattern, module_handler_func in global_command_registry.get_registered_commands():
        pattern_lower = pattern.lower()
        print(f"DEBUG_DISPATCHER: Intentando patrón: '{pattern}' (Minúsculas: '{pattern_lower}')") # <--- AÑADIDA LÍNEA DE DEBUG

        if command_string_lower.startswith(pattern_lower):
            matched_pattern_found = True
            print(f"DEBUG_DISPATCHER: Patrón coincidente: '{pattern}'. Delegando al manejador del módulo.") # <--- AÑADIDA LÍNEA DE DEBUG
            try:
                # Pasamos la cadena de comando ORIGINAL al manejador del módulo.
                # Es responsabilidad del módulo manejar su propio parsing,
                # incluyendo cualquier punto y coma u otros caracteres.
                was_handled = module_handler_func(command_string, context)
                if was_handled:
                    print(f"DEBUG_DISPATCHER: Comando manejado exitosamente por el módulo para el patrón '{pattern}'.") # <--- AÑADIDA LÍNEA DE DEBUG
                    return
                else:
                    print(f"❌ Error de sintaxis o interno: El módulo para '{pattern}' no pudo procesar completamente el comando '{command_string}'.")
                    # Si devuelve False, significa que el parser interno del módulo falló.
                    # Asumimos que si un patrón coincide, este es el módulo intencionado.
                    return

            except Exception as e:
                print(f"❌ Error inesperado al delegar o ejecutar el comando '{command_string}' a su módulo: {type(e).__name__} - {e}")
                traceback.print_exc()
                return
    
    if not matched_pattern_found:
        print(f"❌ Comando no reconocido o no soportado: '{command_string}'")