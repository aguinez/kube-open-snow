# gcs_parquet_writer.py
import pyarrow as pa
import pyarrow.parquet as pq
import gcsfs
import os
import uuid
import argparse # For parsing command-line arguments

def main():
    parser = argparse.ArgumentParser(description="PyArrow script to write Parquet to GCS.")
    # Ensure these argument names match what KubeSol EXECUTE SCRIPT WITH ARGS generates
    parser.add_argument(
        "--gcs_key_file_path_arg", # Matches the key from KubeSol's ARGS
        required=True,
        help="Path to the GCS service account key file mounted in the pod."
    )
    parser.add_argument(
        "--gcs_bucket_name_arg", # Matches the key from KubeSol's ARGS
        required=True,
        help="Name of the GCS bucket to write to."
    )
    # Example of adding another optional argument
    parser.add_argument(
        "--output_sub_directory",
        default="output_from_kubesol",
        help="Subdirectory within the GCS bucket for the output."
    )


    args = parser.parse_args()
    print(f"Script arguments received: key_file_path='{args.gcs_key_file_path_arg}', bucket_name='{args.gcs_bucket_name_arg}', output_subdir='{args.output_sub_directory}'")


    # --- 1. Set up GCS Authentication using the provided argument ---
    # The path provided via --gcs_key_file_path_arg is used to set GOOGLE_APPLICATION_CREDENTIALS
    # This environment variable is then used by gcsfs and google-cloud-storage
    
    # Assign directly from args to the variable that will be checked by os.path.exists
    gcs_key_file_to_check = args.gcs_key_file_path_arg

    if not gcs_key_file_to_check: # Should not happen if required=True and arg is passed
        print(f"❌ ERROR: The path for GCS key file (--gcs_key_file_path_arg) was not provided or is empty.")
        exit(1)
        
    # Set the environment variable for Google Cloud libraries
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcs_key_file_to_check
    print(f"ℹ️ GOOGLE_APPLICATION_CREDENTIALS environment variable set to: {gcs_key_file_to_check}")

    # Now, re-fetch it from env to confirm for the os.path.exists check and for clarity
    # This is the variable that was None in your traceback
    gcs_key_file_from_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not gcs_key_file_from_env:
        print(f"❌ ERROR: GOOGLE_APPLICATION_CREDENTIALS could not be retrieved from environment after setting.")
        print(f"   This indicates an issue with how the environment variable was set or fetched.")
        exit(1)

    # Line 23 (approximately) in your script that failed:
    if not os.path.exists(gcs_key_file_from_env):
        print(f"❌ ERROR: GCS key file not found at the specified path: {gcs_key_file_from_env}")
        print("   Please ensure the secret is correctly mounted in the pod at this path,")
        print("   and that this path was correctly passed as an argument to the script.")
        exit(1)
    
    print(f"ℹ️ Verified GCS key file exists at: {gcs_key_file_from_env}")
    
    gcs_bucket_name = args.gcs_bucket_name_arg # Use the bucket name from args

    # --- 2. Prepare Data (Example: Create a PyArrow Table) ---
    print("ℹ️ Preparing sample data using PyArrow...")
    try:
        names = pa.array(["ArgUser1", "ArgUser2", "ArgUser3", "ArgUser4"], type=pa.string())
        ids = pa.array([301, 302, 303, 304], type=pa.int32())
        values = pa.array([float(i * 1.23) for i in range(4)], type=pa.float64())
        
        table_to_write = pa.Table.from_arrays(
            [names, ids, values],
            names=['user_name_arg', 'user_id_arg', 'value_arg']
        )
        print("ℹ️ Sample PyArrow Table created successfully:")
        print(table_to_write)
    except Exception as e:
        print(f"❌ ERROR: Failed to create PyArrow table: {e}")
        exit(1)

    # --- 3. Define GCS Output Path ---
    unique_id = str(uuid.uuid4())[:8]
    file_name = f"data_{unique_id}.parquet"
    gcs_output_path = f"gs://{gcs_bucket_name}/{args.output_sub_directory}/{file_name}"
    
    print(f"ℹ️ Target GCS path for Parquet file: {gcs_output_path}")

    # --- 4. Initialize GCSFileSystem ---
    try:
        fs = gcsfs.GCSFileSystem() 
        print("ℹ️ GCSFileSystem initialized successfully.")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize GCSFileSystem: {e}")
        exit(1)

    # --- 5. Write the PyArrow Table to GCS as a Parquet file ---
    try:
        print(f"ℹ️ Attempting to write Parquet file to {gcs_output_path}...")
        pq.write_table(table_to_write, gcs_output_path, filesystem=fs)
        print(f"✅ Successfully wrote Parquet file to {gcs_output_path}")

        if fs.exists(gcs_output_path):
            print(f"ℹ️ File verification: {gcs_output_path} exists on GCS.")
        else:
            print(f"⚠️ File verification: {gcs_output_path} NOT found on GCS immediately after write.")

    except Exception as e:
        print(f"❌ ERROR: Failed to write Parquet file to GCS: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    print("✅ Parquet to GCS writer script finished successfully.")

if __name__ == "__main__":
    main() # No explicit exit code needed here, main will exit with 1 on errors