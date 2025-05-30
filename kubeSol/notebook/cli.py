# kubeSol/notebook/cli.py
import subprocess
import shutil
import os
import sys

def _install_kernelspec_if_needed(kernelspec_dir_name="kubesol_sql_kernel"):
    """
    Checks if the KubeSol kernelspec is installed and offers to install it.
    This is a helper and might need adjustment based on your project layout.
    """
    jupyter_executable = shutil.which("jupyter")
    if not jupyter_executable:
        return False # Jupyter not found

    try:
        installed_kernels = subprocess.check_output([jupyter_executable, "kernelspec", "list", "--json"], text=True)
        import json
        kernels = json.loads(installed_kernels)
        if kernelspec_dir_name in kernels.get("kernelspecs", {}):
            print(f"ℹ️ KubeSol SQL kernel ('{kernelspec_dir_name}') appears to be installed.")
            return True
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Could not reliably check for existing KubeSol kernelspec: {e}")
        # Proceed to offer installation

    # Try to find the kernelspec directory within the installed kubeSol package
    # This assumes 'kernelspec' is a sub-directory of 'kubeSol.notebook'
    try:
        import kubeSol.notebook.kernelspec as kernelspec_module
        # The __path__ attribute of a package gives a list containing the path to the package.
        kernelspec_path_in_package = os.path.join(kernelspec_module.__path__[0], kernelspec_dir_name)
        
        # A more robust way to get kernelspec_path might be to use importlib.resources for package data
        # from importlib import resources
        # with resources.path("kubeSol.notebook.kernelspec", kernelspec_dir_name) as path_obj:
        #    kernelspec_path_in_package = str(path_obj)


        if not os.path.isdir(kernelspec_path_in_package): # Check if the specific kernel dir exists
             # Fallback for finding kernelspec relative to this cli.py file if packaged differently
            current_dir = os.path.dirname(os.path.abspath(__file__))
            kernelspec_path_in_package = os.path.join(current_dir, "kernelspec", kernelspec_dir_name)


        if os.path.isdir(kernelspec_path_in_package):
            print(f"Found KubeSol kernelspec at: {kernelspec_path_in_package}")
            confirm_install = input(f"KubeSol SQL kernel not found or unconfirmed. Install it from '{kernelspec_path_in_package}'? (y/n): ").strip().lower()
            if confirm_install == 'y':
                try:
                    print(f"Installing KubeSol SQL kernelspec using: {jupyter_executable} kernelspec install {kernelspec_path_in_package} --user")
                    subprocess.run([jupyter_executable, "kernelspec", "install", kernelspec_path_in_package, "--user", "--replace"], check=True)
                    print("✅ KubeSol SQL kernelspec installed successfully.")
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError) as install_e:
                    print(f"❌ Failed to install KubeSol SQL kernelspec: {install_e}")
                    return False
            else:
                print("Kernel installation skipped by user.")
                return False
        else:
            print(f"❌ Could not find KubeSol kernelspec directory for installation. Expected near: {kernelspec_path_in_package}")
            print("   Please ensure KubeSol is installed correctly or install the kernelspec manually.")
            return False
            
    except ImportError:
        print("❌ Error: Could not determine path to KubeSol kernelspec (ImportError).")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred trying to find/install kernelspec: {e}")
        return False


def launch_notebook_server(port: int = 8888, kernel_name: str = "kubesol_sql_kernel"):
    """
    Launches a local Jupyter Notebook or JupyterLab server.
    """
    jupyter_executables_to_try = ["jupyter-lab", "jupyter-notebook", "jupyter"]
    selected_jupyter_executable = None

    for executable in jupyter_executables_to_try:
        if shutil.which(executable):
            selected_jupyter_executable = shutil.which(executable)
            # Prefer jupyter-lab if available
            if "jupyter-lab" in executable:
                break 
            # If jupyter-notebook found, use it, but keep looking for lab
            if "jupyter-notebook" in executable and not selected_jupyter_executable.endswith("jupyter-lab"):
                 # If lab was not found before, use notebook
                 pass # selected_jupyter_executable is already set from a previous iteration if jupyter-lab wasn't found
            # If just "jupyter" is found, it could launch either, but let's be specific.
            # The loop will find jupyter-lab or jupyter-notebook first if they are distinct.


    if not selected_jupyter_executable:
        print("❌ Jupyter Notebook or JupyterLab is not found in your PATH.")
        print("   Please install it: pip install notebook jupyterlab")
        return

    print(f"ℹ️ Using Jupyter executable: {selected_jupyter_executable}")

    # Attempt to install/verify kernelspec
    # The kernelspec directory name inside kubeSol/notebook/kernelspec/
    # should match the 'kernel_name' argument if different from default.
    # For simplicity, let's assume a fixed kernelspec directory name.
    # The actual name registered with Jupyter might differ slightly (e.g. underscores vs hyphens)
    # based on the directory name given to `jupyter kernelspec install`.
    # For this example, assume the directory is named `kubesol_sql_kernel`.
    if not _install_kernelspec_if_needed("kubesol_sql_kernel"): # Pass the directory name of your kernelspec
        print("Proceeding to launch Jupyter, but KubeSol kernel might not be available.")

    launch_mode = "lab" if "jupyter-lab" in selected_jupyter_executable else "notebook"
    print(f"🚀 Launching Jupyter {launch_mode.capitalize()} server on port {port}...")
    print(f"   If a browser doesn't open, navigate to the URL printed by Jupyter (usually http://localhost:{port}/).")
    print("   In Jupyter, create a new notebook and select the 'KubeSol SQL' kernel (or similar).")
    print("   Press Ctrl+C in this terminal (possibly multiple times) to stop the Jupyter server.")
    
    try:
        cmd = [selected_jupyter_executable, f"--port={port}"]
        # To try and open a specific notebook or default to KubeSol kernel:
        # cmd.append(f"--NotebookApp.default_kernel_name={kernel_name}") # This only works for notebook, lab has different config.
        # For now, let's keep it simple and let the user select the kernel.
        
        subprocess.run(cmd, check=False) # check=False to not raise error if user stops it
    except KeyboardInterrupt:
        print("\nJupyter server launch interrupted or stopped by user.")
    except Exception as e:
        print(f"❌ Jupyter server failed to start or an error occurred: {e}")