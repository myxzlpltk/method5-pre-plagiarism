from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from google.cloud import storage, firestore
from google.oauth2 import service_account
from model import PubSubRequest, Document
from google.oauth2 import id_token
from fastapi.middleware.cors import CORSMiddleware
import method5
import base64
import json
import os
import tempfile
import cachecontrol
import google.auth.transport.requests
import requests

# Load .env
load_dotenv()

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
credentials = service_account.Credentials.from_service_account_file(filename="service-account.json")
storage_client = storage.Client(project=os.environ.get("PROJECT_ID"), credentials=credentials)
firestore_client = firestore.Client(project=os.environ.get("PROJECT_ID"), credentials=credentials)

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
    if user["email"] != os.environ.get("SERVICE_ACCOUNT_EMAIL"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Decode message
    json_str = base64.b64decode(req.message.data)
    document = Document(**json.loads(json_str))

    # Download file
    pdf_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    bucket = storage_client.bucket(os.environ.get("BUCKET_NAME"))
    blob = bucket.blob(f"{document.email}/{document.filename}")
    blob.download_to_file(pdf_file)
    pdf_file.close()

    # Compute
    data = method5.compute(pdf_file)

    # Save data to firestore
    doc_ref = firestore_client.collection(f"users/{document.email}/result").document(document.id)
    doc_ref.update({"method5": data})

    # Clean up temporary file
    if os.path.exists(pdf_file.name):
        os.unlink(pdf_file.name)

    return "OK"
