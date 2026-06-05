import os
S3_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME", "your-s3-bucket-name")

SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "")
