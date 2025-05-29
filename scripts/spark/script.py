from pyspark.sql import SparkSession
import argparse

def main(bucket_name, output_path):
    # Initialize SparkSession
    # When running in a K8s pod, this will typically run Spark in "local" mode
    # unless configured to connect to a K8s master for distributed Spark.
    # For this example, we'll assume Spark runs locally within the pod.
    spark = SparkSession.builder.appName("SparkToGCSWriter").getOrCreate()

    # Example: Create a sample DataFrame
    data = [("ProductA", 100, "Electronics"),
            ("ProductB", 150, "Books"),
            ("ProductC", 200, "Electronics"),
            ("ProductD", 50, "HomeGoods")]
    columns = ["product_name", "price", "category"]
    df = spark.createDataFrame(data, columns)

    print("Sample DataFrame:")
    df.show()

    # Define the full GCS output path
    # e.g., gs://your-bucket-name/spark_data/my_output
    full_gcs_path = f"gs://{bucket_name}/{output_path}"

    print(f"Attempting to write DataFrame to GCS path: {full_gcs_path}")

    # Write the DataFrame to GCS in Parquet format
    # The GCS connector needs to be available in Spark's classpath.
    df.write.mode("overwrite").parquet(full_gcs_path)

    print(f"Successfully wrote DataFrame to {full_gcs_path}")

    spark.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PySpark application to write data to GCS.")
    parser.add_argument("--bucket_name", required=True, help="Target GCS bucket name.")
    parser.add_argument("--output_path", required=True, help="Output path within the GCS bucket (e.g., data/my_table).")
    
    args = parser.parse_args()
    main(args.bucket_name, args.output_path)