import boto3
from botocore.exceptions import NoCredentialsError

def upload_to_s3(file_path, bucket_name, s3_file_name):
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_path, bucket_name, s3_file_name)
        print(f"File {file_path} uploaded to S3 bucket {bucket_name} as {s3_file_name}")
    except FileNotFoundError:
        print("The file was not found")
        raise
    except NoCredentialsError:
        print("Credentials not available")
        raise

