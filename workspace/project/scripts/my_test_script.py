# my_test_script.py
import os
import sys

print("--- Script de Prueba KubeSol Iniciado ---", flush=True)
print(f"Versión de Python: {sys.version}", flush=True)

# Imprimir variables de entorno (parámetros del YAML)
print("\n--- Parámetros del Entorno (de YAML) ---", flush=True)
for key, value in os.environ.items():
    if key.startswith("MY_PARAM_"): # Prefijo para identificar parámetros inyectados
        print(f"  {key}: {value}", flush=True)

print("\n--- Script de Prueba KubeSol Finalizado Exitosamente ---", flush=True)