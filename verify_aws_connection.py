import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def run_test():
    # Path to the secrets file
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    
    print("=== AWS S3 Connection Tester ===")
    if not os.path.exists(secrets_path):
        print(f"Error: Secrets file not found at: {os.path.abspath(secrets_path)}")
        return

    # Parse secrets manually to verify exactly what's written on disk
    secrets = {}
    with open(secrets_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                secrets[k.strip()] = v.strip().strip('"').strip("'")
    
    access_key = secrets.get("AWS_ACCESS_KEY")
    secret_key = secrets.get("AWS_SECRET_KEY")
    bucket_name = secrets.get("AWS_BUCKET_NAME")
    s3_base_folder = secrets.get("S3_BASE_FOLDER", "safety_dashboards")
    
    if not access_key or not secret_key or not bucket_name:
        print("Error: Missing credentials in secrets.toml.")
        print(f"Found: AWS_ACCESS_KEY={access_key}, AWS_SECRET_KEY={'***' if secret_key else None}, AWS_BUCKET_NAME={bucket_name}")
        return

    print(f"1. Read secrets from: {os.path.abspath(secrets_path)}")
    print(f"   - AWS Access Key : {access_key[:6]}...{access_key[-4:]}")
    print(f"   - AWS Bucket Name: {bucket_name}")
    print(f"   - S3 Base Folder : {s3_base_folder}")
    
    print("\n2. Pinging AWS S3 (Checking bucket status)...")
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        s3 = session.client('s3')
        
        # head_bucket returns 200 OK if bucket exists and credentials have permission
        s3.head_bucket(Bucket=bucket_name)
        print("   -> Success! Connection established and credentials verified.")
        
        print(f"\n3. Listing files in S3 bucket under '{s3_base_folder}/'...")
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_base_folder)
        
        if 'Contents' in response:
            print("   -> Found files:")
            for obj in response['Contents']:
                print(f"      - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("   -> Connection worked, but no files were found under that prefix.")
            
    except NoCredentialsError:
        print("   -> Error: AWS credentials were not found or initialized.")
    except ClientError as ce:
        error_code = ce.response.get('Error', {}).get('Code', 'Unknown')
        print(f"   -> AWS S3 Error: {ce}")
        if error_code == '403':
            print("      Suggestion: Verify that your IAM User has 's3:ListBucket' and 's3:GetObject' permissions.")
        elif error_code == '404':
            print("      Suggestion: Verify that the bucket name is correct.")
    except Exception as e:
        print(f"   -> Unexpected Error: {e}")

if __name__ == "__main__":
    run_test()
