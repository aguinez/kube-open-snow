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
