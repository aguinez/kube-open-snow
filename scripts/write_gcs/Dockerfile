FROM python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install system dependencies if any (less likely for this minimal setup)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Install Python libraries
# pyarrow for Parquet, gcsfs for GCS filesystem interface (pulls google-cloud-storage)
RUN pip install \
    pyarrow>=10.0.0 \
    gcsfs>=2023.0.0 \
    google-auth>=2.0.0

# Create a working directory
WORKDIR /app

# The KubeSol job will mount the script here (e.g., as /kubesol_scripts/code)
# And the command will be something like ["python", "/kubesol_scripts/code"]
# No specific CMD or ENTRYPOINT needed here if the K8s job defines the command.

# Add a non-root user and switch to it (good practice)
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
USER appuser

# For debugging: show installed packages
RUN pip freeze