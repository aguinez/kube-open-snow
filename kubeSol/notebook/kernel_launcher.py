# kubeSol/notebook/kernel_launcher.py
from ipykernel.kernelapp import IPKernelApp
from kubeSol.notebook.kernel import KubeSolKernel # Relative import if kernel.py is in the same directory

def main():
    """Launch an instance of the KubeSol Kernel."""
    IPKernelApp.launch_instance(kernel_class=KubeSolKernel)

if __name__ == '__main__':
    main()