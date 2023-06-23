# Load .env
from dotenv import load_dotenv
dot_env_loaded = load_dotenv()

# Import dependencies
from fastapi import Depends, FastAPI, HTTPException, Request
from google.cloud import storage, firestore
from google.oauth2 import id_token, service_account
from fastapi.middleware.cors import CORSMiddleware
from app.model import Document, PubSubRequest
from app.method5 import compute_method5
import base64
import json
import os
import tempfile
import cachecontrol
import google.auth.transport.requests
import requests

# FastAPI app
app = FastAPI(redoc_url=None, docs_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cached request
session = requests.session()
cached_session = cachecontrol.CacheControl(session)
request = google.auth.transport.requests.Request(session=cached_session)

# Define GCP services
service_account_info = json.loads(os.getenv("SERVICE_ACCOUNT_INFO"))
credentials = service_account.Credentials.from_service_account_info(service_account_info)
storage_client = storage.Client(project=os.getenv("PROJECT_ID"), credentials=credentials)
firestore_client = firestore.Client(project=os.getenv("PROJECT_ID"), credentials=credentials)

def get_token_auth_header(authorization):
    parts = authorization.split()

    if parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail='Authorization header must start with Bearer')
    elif len(parts) == 1:
        raise HTTPException(status_code=401, detail='Authorization token not found')
    elif len(parts) > 2:
        raise HTTPException(status_code=401, detail='Authorization header be Bearer token')
    
    token = parts[1]
    return token

def verify_token(req: Request):
    try:
        token = get_token_auth_header(req.headers["Authorization"])
        return id_token.verify_token(token, request)
    except:
        raise HTTPException(status_code=401, detail="Unauthenticated")

@app.post('/')
def process(req: PubSubRequest, user: any = Depends(verify_token)):
    # Check if user is service account
    if user["email"] != os.getenv("SERVICE_ACCOUNT_EMAIL"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Decode message
    json_str = base64.b64decode(req.message.data)
    document = Document(**json.loads(json_str))

    # Download file
    pdf_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    bucket = storage_client.bucket(os.getenv("BUCKET_NAME"))
    blob = bucket.blob(f"{document.email}/{document.filename}")
    blob.download_to_file(pdf_file)
    pdf_file.close()

    # Compute
    data = compute_method5(pdf_file)

    # Save data to firestore
    result_ref = firestore_client.collection(f"users/{document.email}/result").document(document.id)
    result_ref.update({"method5": data})

    doc_ref = firestore_client.collection(f"users/{document.email}/documents").document(document.id)
    doc_ref.update({"status": "invalid" if len(data["pages"]) > 0 else "valid"})

    user_ref = firestore_client.collection(f"users").document(document.email)
    user_ref.update({"idle": True, "jobCreatedAt": None})

    # Clean up temporary file
    if os.path.exists(pdf_file.name):
        os.unlink(pdf_file.name)

    return "OK"
