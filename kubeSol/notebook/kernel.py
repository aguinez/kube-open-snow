# kubeSol/notebook/kernel.py
from ipykernel.kernelbase import Kernel
import traceback
import io
import sys

# Assuming your project structure allows these imports
# You might need to adjust if __version__ is elsewhere or not defined
try:
    from kubeSol import __version__ as kubesol_version
except ImportError:
    kubesol_version = "0.0.0-dev" 

# These imports depend on your existing kubeSol structure
# Ensure they are correct based on where parser and executor are.
from kubeSol.parser import parse_sql #
from kubeSol.engine.executor import execute_command #
from kubeSol.constants import DEFAULT_NAMESPACE #


class KubeSolKernel(Kernel):
    implementation = 'KubeSolSQL'
    implementation_version = kubesol_version
    language = 'kubesol-sql' # Can be 'sql' for generic SQL highlighting
    language_version = kubesol_version # Version of your KubeSol SQL-like language
    language_info = {
        'name': 'KubeSol SQL',
        'mimetype': 'text/x-sql', # Common MIME type for SQL
        'file_extension': '.kubesql', # A potential file extension
    }
    banner = "KubeSol SQL Kernel - Execute KubeSol commands interactively in Jupyter."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_namespace = DEFAULT_NAMESPACE # Each kernel instance has its own namespace context
        # In a more advanced kernel, you might load/save this context or allow changing it via magics.

    def do_execute(self, code, silent, store_history, user_expressions, allow_stdin):
        """
        Executes user code from a notebook cell.
        `code`: The string of code to execute.
        `silent`: If True, no output should be sent to the frontend.
        `store_history`: If True, the code should be added to execution history.
        """
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        # Redirect stdout and stderr to capture print statements from execute_command
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_stdout = io.StringIO()
        redirected_stderr = io.StringIO()
        sys.stdout = redirected_stdout
        sys.stderr = redirected_stderr

        error_content = None
        execution_status = 'ok'

        try:
            # The execute_command function from executor.py currently prints output
            # and handles its own parsing via parse_sql.
            # We pass the raw code string and the kernel's current namespace.
            execute_command(code, namespace=self.current_namespace)
            # If execute_command were refactored to return data, we would handle it here
            # for rich display (e.g., HTML tables for LIST commands).

        except Exception as e:
            execution_status = 'error'
            tb_lines = traceback.format_exc().splitlines()
            error_content = {
                'ename': type(e).__name__,
                'evalue': str(e),
                'traceback': tb_lines
            }
            if not silent:
                self.send_response(self.iopub_socket, 'error', error_content)
            # Also print to our captured stderr for completeness
            print(traceback.format_exc(), file=sys.stderr)
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # Send captured stdout to the frontend
        stdout_value = redirected_stdout.getvalue()
        if not silent and stdout_value:
            stream_out_content = {'name': 'stdout', 'text': stdout_value}
            self.send_response(self.iopub_socket, 'stream', stream_out_content)

        # Send captured stderr to the frontend (if it wasn't already sent as a formal error)
        stderr_value = redirected_stderr.getvalue()
        if not silent and stderr_value and execution_status == 'ok':
            stream_err_content = {'name': 'stderr', 'text': stderr_value}
            self.send_response(self.iopub_socket, 'stream', stream_err_content)
        
        if execution_status == 'error' and error_content:
             return {'status': 'error', 
                    'ename': error_content['ename'], 
                    'evalue': error_content['evalue'], 
                    'traceback': error_content['traceback'],
                    'execution_count': self.execution_count}
        else:
            return {'status': 'ok', 
                    'execution_count': self.execution_count,
                    'payload': [], 
                    'user_expressions': {}}