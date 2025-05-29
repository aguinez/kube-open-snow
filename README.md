# KubeSol: SQL-like Interface for Kubernetes

KubeSol is a command-line tool that provides an SQL-like interface to interact with Kubernetes clusters. It simplifies managing Kubernetes resources and executing scripts by allowing users to write declarative commands.

## Overview

KubeSol aims to bridge the gap between SQL-like syntax and Kubernetes operations. Instead of using complex `kubectl` commands or YAML files for common tasks, you can use intuitive KubeSol commands. The tool is particularly useful for developers and platform engineers who need to manage application configurations, secrets, and run batch jobs/scripts on Kubernetes.

It currently supports interacting with [KinD (Kubernetes in Docker)](https://kind.sigs.k8s.io/) clusters for local development and testing.

## Key Features

* **SQL-like Command Syntax:** Manage Kubernetes resources and scripts using familiar SQL verbs like `CREATE`, `DELETE`, `UPDATE`, `GET`, `LIST`, and `EXECUTE`.
* **Interactive Shell:** Provides an easy-to-use interactive shell that supports multi-line commands.
* **Resource Management:**
    * **Secrets:** Create, delete, and update Kubernetes Secrets. Supports both string data and data from local files.
    * **ConfigMaps:** Create, delete, and update Kubernetes ConfigMaps.
    * **Parameters:** (Implemented as Secrets, typically for storing simple key-value pairs or small script snippets).
* **Script Management & Execution:**
    * **Define Scripts:** Create and manage script definitions (stored as ConfigMaps) with their code, type (Python, PySpark), execution engine, and parameters.
    * **Source Code:** Script code can be provided inline or loaded from a local file.
    * **Execution Engine:** Currently supports running scripts as Kubernetes Jobs (`K8S_JOB`).
    * **Parameterization:** Pass arguments to scripts during execution, either inline or by loading them from a ConfigMap.
    * **Secret Mounting:** Securely mount secrets into script execution environments (Kubernetes Jobs).
* **KinD Cluster Management:** Automatically detects and allows selection of available KinD clusters to work with.
* **Namespace Awareness:** Operates within a specified Kubernetes namespace, defaulting to `default`.

## Requirements

* Python 3.x
* [KinD (Kubernetes in Docker)](https://kind.sigs.k8s.io/) installed and configured.
* `kubectl` installed and configured, with access to a Kubernetes cluster (KinD is used by default for cluster selection).
* Kubernetes Python client library (`kubernetes`).

## Setup and Installation

1.  **Clone the repository (if applicable) or ensure all project files are in a directory named `kubeSol`.**
    ```bash
    # git clone <repository_url>
    # cd kubeSol
    ```
2.  **Install dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install kubernetes lark
    ```
3.  **Ensure your `kubeconfig` is set up** correctly and `kubectl` can access your KinD cluster(s).
    You can create a KinD cluster if you don't have one:
    ```bash
    kind create cluster --name my-kubesol-cluster
    ```

## Running KubeSol



Execute the `main.py` script from the root of the `kubeSol` project directory:

```bash
python -m kubeSol.main
```
* **Create a Script with code from a local file:**
    ```sql
    CREATE SCRIPT script_from_file TYPE PYTHON ENGINE K8S_JOB WITH
        CODE_FROM_FILE="/path/to/your/local_script.py",
        DESCRIPTION="Script loaded from a local file";
    ```

* **Supported Script Types:** `PYTHON`, `PYSPARK`
* **Supported Script Engines:** `K8S_JOB` (default if not specified)

* **Get Script details:**
    ```sql
    GET SCRIPT my_python_script;
    ```

* **List all Scripts:**
    ```sql
    LIST SCRIPT;
    ```

* **Update a Script:**
    You can update `CODE`, `PARAMS_SPEC`, `DESCRIPTION`, or `ENGINE`.
    ```sql
    UPDATE SCRIPT my_python_script SET
        DESCRIPTION="An updated simple Python script",
        CODE="print('This is the new code!')";
    ```

* **Delete a Script:**
    ```sql
    DELETE SCRIPT my_python_script;
    ```

### 5. Executing Scripts

Scripts are executed as Kubernetes Jobs.

* **Execute a Script with inline arguments:**
    ```sql
    EXECUTE SCRIPT my_python_script WITH ARGS (NAME="KubeSol User", ITERATIONS="3");
    ```

* **Execute a Script with arguments from a ConfigMap:**
    First, create a ConfigMap (e.g., `script_params_cm`) with keys like `prefix_NAME="Alice"`, `prefix_ITERATIONS="2"`.
    ```sql
    EXECUTE SCRIPT my_python_script WITH PARAMS_FROM_CONFIGMAP script_params_cm KEY_PREFIX "prefix_";
    ```

* **Execute a Script mounting a Secret:**
    This mounts the `secret_key` from Kubernetes Secret `my-kube-secret` to the path `/mnt/secrets/mysecret/secret_key` inside the script's pod.
    ```sql
    EXECUTE SCRIPT my_python_script
        WITH ARGS (NAME="SecureUser")
        WITH SECRET my-kube-secret KEY "secret_key" AS "/mnt/secrets/mysecret/secret_key";
    ```
    *(Note: Ensure the Secret `my-kube-secret` with a key `secret_key` exists in the Kubernetes namespace.)*

* **Execute a Script with all clauses:**
    ```sql
    EXECUTE SCRIPT my_python_script
        WITH ARGS (NAME="Galaxy", ITERATIONS="2")
        WITH PARAMS_FROM_CONFIGMAP script_run_config KEY_PREFIX "run_"
        WITH SECRET first_secret KEY "api_token" AS "/etc/tokens/api.token"
        WITH SECRET second_secret KEY "config.json" AS "/app/config/settings.json";
    ```

## Project Structure

* `kubeSol/main.py`: Main entry point and interactive shell.
* `kubeSol/constants.py`: Defines application-wide constants.
* `kubeSol/parser/`:
    * `parser.py`: Lark grammar definition and parser initialization.
    * `transformer.py`: Transforms parsed tokens into a structured command dictionary.
* `kubeSol/engine/`:
    * `executor.py`: Dispatches parsed commands to appropriate handlers.
    * `k8s_api.py`: Handles direct interactions with the Kubernetes API using the `kubernetes` Python client.
    * `script_runner.py`: Logic for running scripts (e.g., as Kubernetes Jobs).
    * `kind_manager.py`: Manages listing and selecting KinD clusters.

## Future Development Ideas

* Support for more Kubernetes resources (Deployments, Services, etc.).
* Enhanced `GET` and `LIST` commands with filtering and output formatting.
* Support for other script execution engines (e.g., Spark Operator if `SCRIPT_TYPE_PYSPARK` is to be fully utilized).
* More robust error handling and user feedback.
* Non-interactive mode for scripting KubeSol commands.
* Integration with other Kubernetes cluster types beyond KinD.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements.
