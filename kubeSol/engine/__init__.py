# kubeSol/engine/__init__.py
"""
KubeSol Engine Package.
Handles the execution of parsed commands and interaction with Kubernetes.
"""
from .executor import execute_command
# You might also want to expose other key components from the engine package here
# from .k8s_api import create_k8s_job # example
# from .script_runner import run_script_as_k8s_job # example

__all__ = [
    'execute_command',
    # 'create_k8s_job', 
    # 'run_script_as_k8s_job',
]