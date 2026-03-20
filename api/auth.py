import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
API_KEY = os.environ.get("API_KEY","dc-monitor-secret-key")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def require_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key. Include 'X-API-Key' header.",
        )
    return key