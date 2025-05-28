# mi_script_local.py
import argparse

parser = argparse.ArgumentParser(description='Un script de prueba leído desde un archivo.')
parser.add_argument('--mensaje', type=str, required=True, help='Mensaje a imprimir.')

args = parser.parse_args()
print(f"Script ejecutado desde archivo! Mensaje: {args.mensaje}")
print("¡Funciona!")