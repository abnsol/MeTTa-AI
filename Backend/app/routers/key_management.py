import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from pymongo.database import Database
from fastapi import APIRouter, HTTPException, status, Depends, Query, Response, Request
from app.db.db import update_chunk, delete_chunk, get_chunk_by_id, get_chunks
from app.dependencies import get_mongo_db, get_kms, get_current_user
from datetime import datetime, timedelta 
from app.services.key_management_service import KMS
import json


router = APIRouter(
    prefix="/api/kms",
    tags=["kms"],
    responses={404: {"description": "Not found"}},
)

@router.post("/store")
def store_api_key(api_key: str, service_name: str, response: Response, user = Depends(get_current_user), kms: KMS = Depends(get_kms), mongo_db: Database = Depends(get_mongo_db)):
    encrypted_value = kms.encrypt_and_store(user["_id"], service_name, api_key, mongo_db)
    response.set_cookie(
        key=service_name,
        value=encrypted_value,
        httponly=True,   # prevents JS access
        secure=True,     # only sent over HTTPS
        samesite="Strict", # no csrf  
        expires=datetime.now() + timedelta(days=7) 
    )

    # to have more protection against csrf
    # works for old browsers
    x_csrf_random_value = kms.generate_dsc_key(32)  # cryptographically secure random bytes
    response.set_cookie(
        key=f"x_csrf_random_value_{service_name}",
        value=x_csrf_random_value,
        httponly=False,    # allow JS access
        secure=True,       # only sent over HTTPS
        samesite="Strict", # no csrf
        expires=datetime.now() + timedelta(days=7)
    )

    return {"message": "API key stored securely in cookie"} 

@router.get("/services")
def get_api_services(user = Depends(get_current_user), kms: KMS = Depends(get_kms), mongo_db: Database = Depends(get_mongo_db)):
    services = kms.get_api_services(user["_id"], mongo_db)
    if not services:
        raise HTTPException(status_code=404, detail="No services found")
    return {"services": services}

@router.delete("/delete/{service_name}")
def delete_api_key(service_name: str, user = Depends(get_current_user), kms: KMS = Depends(get_kms), mongo_db: Database = Depends(get_mongo_db)):
    deleted = kms.delete_api_key(user["_id"], service_name, mongo_db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Service not found or could not be deleted")

    # remove cookies for the service and the csrf token
    resp = Response(
        content=json.dumps({"message": f"API key for service '{service_name}' deleted successfully"}),
        media_type="application/json",
        status_code=status.HTTP_200_OK
    )
    resp.delete_cookie(service_name)
    resp.delete_cookie(f"x_csrf_random_value_{service_name}")
    return resp







