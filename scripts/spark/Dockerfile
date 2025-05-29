# Choose a base image that has Spark and Python installed.
# For example, apache/spark-py provides Python and Spark.
# Ensure the Spark version in the image is compatible with your GCS connector.
ARG SPARK_VERSION=3.5.0 # Or your desired version
FROM apache/spark-py:${SPARK_VERSION}

USER root # Switch to root to install packages if needed, then switch back

# Set environment variables (SPARK_HOME is usually set by the base image)
ENV PYTHONUNBUFFERED=1
ENV PYSPARK_PYTHON=python3

# Example: Install additional Python packages if your script needs them
# RUN pip3 install google-cloud-storage # Only if using Python GCS client directly, not usually needed for Spark GCS connector

# Download and add the GCS connector JAR to Spark's jars directory
# Find the latest/compatible version from: https://cloud.google.com/dataproc/docs/concepts/connectors/cloud-storage
# The version should match the Hadoop version bundled with your Spark. Spark 3.5 typically uses Hadoop 3.3.x.
ARG GCS_CONNECTOR_FILENAME=gcs-connector-hadoop3-latest.jar
ADD https://storage.googleapis.com/hadoop-lib/gcs/${GCS_CONNECTOR_FILENAME} ${SPARK_HOME}/jars/

# Copy your PySpark application script into the image
COPY gcs_writer.py /app/gcs_writer.py

WORKDIR /app

# The KubeSol job will specify the command to run (e.g., python /app/gcs_writer.py)
# So, ENTRYPOINT or CMD are not strictly necessary here for KubeSol's current K8S_JOB engine.