# kubesol/__init__.py
from .__version__ import __version__
from kubesol.dispatch.command_registry import global_command_registry
try:
    from kubesol import modules
    modules.load_all_command_modules()
    print(f"INFO: KubeSol modules loaded. Version: {__version__}")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to load KubeSol command modules: {e}")