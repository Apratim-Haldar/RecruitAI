import os
import io
import time
import boto3
import pymongo
import zipfile
import pypdf
from docx import Document
from botocore.exceptions import ClientError
from typing import Optional
from dotenv import load_dotenv

# Load credentials and configuration from .env file
load_dotenv()

# Environment variables from .env
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
# GOOGLE_API_KEY is available but not used in this sample

# Setup AWS S3 client with boto3
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# Setup MongoDB client using pymongo
mongo_client = pymongo.MongoClient(MONGO_DB_URI)
# Assuming that your connection URI includes the database name,
# otherwise you can specify the db name e.g., mongo_client["your_db_name"]
db = mongo_client.get_default_database()
applications_collection = db["applications"]

# --------------------------------------------------------------------
# Helper Function: Extract Text from S3 CV (provided sample function)
def extract_text_from_cv(s3_client: boto3.client, bucket_name: str, object_key: str) -> Optional[str]:
    """Downloads CV from S3 and extracts text content from PDF, DOCX, or TXT files."""
    if not s3_client:
        print("   S3 client not available. Cannot extract text.")
        return None

    filename = os.path.basename(object_key)  # Get filename for logging/extension check
    _, file_extension = os.path.splitext(filename)
    file_extension = file_extension.lower()

    # Focus on text-extractable types
    if file_extension not in ['.pdf', '.docx', '.txt']:
        print(f"   INFO: Skipping text extraction for non-text file type '{file_extension}' (Object: '{object_key}').")
        return None

    print(f"   Attempting to download and extract text from: s3://{bucket_name}/{object_key}")
    try:
        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        # Read the content into memory (bytes)
        file_content_bytes = response['Body'].read()
        print(f"      Successfully downloaded {filename} ({len(file_content_bytes)} bytes).")

        text = None  # Initialize text variable
        if file_extension == '.pdf':
            with io.BytesIO(file_content_bytes) as pdf_file:
                try:
                    reader = pypdf.PdfReader(pdf_file)
                    if reader.is_encrypted:
                        print(f"      ❌ Error: PDF '{filename}' is encrypted and cannot be read.")
                        return None
                    extracted_pages = []
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_pages.append(page_text)
                    if extracted_pages:
                        text = "\n".join(extracted_pages)
                except pypdf.errors.PdfReadError as pdf_err:
                    print(f"      ❌ Error parsing PDF content for '{filename}': {pdf_err}. File might be corrupted.")
                    return None

        elif file_extension == '.docx':
            with io.BytesIO(file_content_bytes) as docx_file:
                try:
                    doc = Document(docx_file)
                    para_texts = [para.text for para in doc.paragraphs if para.text is not None]
                    if para_texts:
                        text = "\n".join(para_texts)
                except (KeyError, ValueError, zipfile.BadZipFile) as docx_err:
                    print(f"      ❌ Error processing DOCX content for '{filename}': {docx_err}. File might be corrupted or not a valid DOCX.")
                    return None

        elif file_extension == '.txt':
            try:
                text = file_content_bytes.decode('utf-8', errors='ignore')
            except Exception as decode_err:
                print(f"      ❌ Error decoding TXT file '{filename}': {decode_err}")
                return None

        if text and text.strip():
            print(f"      ✅ Text extraction successful (Length: {len(text)}).")
            return text.strip()
        else:
            print(f"      INFO: No text content could be extracted from '{filename}'.")
            return None

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == 'NoSuchKey':
            print(f"      ❌ Error: S3 object key not found: '{object_key}' in bucket '{bucket_name}'.")
        elif error_code == 'NoSuchBucket':
            print(f"      ❌ Error: S3 bucket not found: '{bucket_name}'. Check bucket name and region.")
        elif error_code == 'AccessDenied':
            print(f"      ❌ Error: Access Denied trying to get object '{object_key}' from bucket '{bucket_name}'. Check IAM permissions.")
        else:
            print(f"      ❌ Error downloading/accessing S3 object '{object_key}': {e}")
        return None
    except Exception as e:
        print(f"      ❌ Unexpected error processing content of '{filename}' from S3 object '{object_key}': {e}")
        return None

# --------------------------------------------------------------------
# Background Worker: Listen for new Applications and update resume_details

def process_new_application(document: dict):
    """
    For an incoming application document, if the resume_details field is absent,
    fetch and extract resume text from S3 and update the document.
    """
    app_id = document.get("_id")
    s3_file_key = document.get("s3FileKey")
    if not s3_file_key:
        print(f"Document {_id} does not have an 's3FileKey'. Skipping processing.")
        return

    print(f"\nProcessing Application ID: {app_id} with s3FileKey: {s3_file_key}")
    resume_text = extract_text_from_cv(s3_client, AWS_S3_BUCKET_NAME, s3_file_key)

    if resume_text:
        update_result = applications_collection.update_one(
            {"_id": app_id},
            {"$set": {"resume_details": resume_text}}
        )
        if update_result.modified_count:
            print(f"Updated Application ID {app_id} with resume_details.")
        else:
            print(f"Failed to update Application ID {app_id}.")
    else:
        print(f"No text extracted for Application ID {app_id}.")

def watch_applications_change_stream():
    """
    Open a change stream on the Applications collection to listen for new insert events.
    When a new document is detected, process the resume extraction.
    """
    try:
        pipeline = [
            {"$match": {"operationType": "insert"}}
        ]
        with applications_collection.watch(pipeline, full_document='updateLookup') as change_stream:
            print("Listening for new application documents...")
            for change in change_stream:
                full_doc = change.get("fullDocument")
                if full_doc:
                    # Process only if resume_details is not already present.
                    if not full_doc.get("resume_details"):
                        process_new_application(full_doc)
                    else:
                        print(f"Application ID {full_doc.get('_id')} already contains resume_details. Skipping.")
    except Exception as e:
        print(f"Error in change stream: {e}")

if __name__ == "__main__":
    print("Starting the Resume Parsing Background Worker...")
    while True:
        try:
            watch_applications_change_stream()
        except Exception as general_e:
            print(f"Encountered error in the worker loop: {general_e}")
            # Pause briefly before trying to reinitialize the change stream
            time.sleep(5)
