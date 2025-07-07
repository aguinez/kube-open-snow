# kubesol/modules/__init__.py
import pkgutil
import importlib
import sys

def load_all_command_modules():
    print("INFO: Discovering and loading KubeSol command modules...")
    for finder, name, ispkg in pkgutil.iter_modules(__path__):
        if ispkg:
            full_module_name = f"{__name__}.{name}"
            try:
                module = importlib.import_module(full_module_name)
            except Exception as e:
                print(f"WARNING: Could not load KubeSol module '{full_module_name}': {e}")
                import traceback
                traceback.print_exc()