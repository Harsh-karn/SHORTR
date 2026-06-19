import os
import jwt
from fastapi import Request, HTTPException
import httpx
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import User

# In production, set CLERK_PEM_PUBLIC_KEY in your .env or fetch JWKS.
# For simplicity in this build, we fetch the JWKS directly from Clerk.
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "https://api.clerk.dev/v1/jwks")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")

# Cache the JWK so we don't fetch it on every request
_jwks_cache = None

async def get_clerk_jwks():
    global _jwks_cache
    if not _jwks_cache:
        # In a real app, you'd fetch this from your specific Clerk Frontend API URL
        # e.g., https://clerk.yourdomain.com/.well-known/jwks.json
        # Here we'll expect the user to set CLERK_JWKS_URL
        if not CLERK_JWKS_URL:
            raise Exception("CLERK_JWKS_URL is not configured")
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(CLERK_JWKS_URL)
            if resp.status_code == 200:
                _jwks_cache = resp.json()
            else:
                raise Exception("Failed to fetch JWKS")
    return _jwks_cache

async def get_current_user(request: Request):
    """
    Dependency to get the current authenticated user via Clerk JWT.
    If the user does not exist in our Postgres DB yet, upsert them.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
        
    token = auth_header.split(" ")[1]
    
    try:
        # Get unverified header to find the kid (Key ID)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        jwks = await get_clerk_jwks()
        
        # Find the correct key in JWKS
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
                
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token key")
            
        # Verify the token using the PyJWT PyJWKClient or by converting JWK to PEM.
        # Since we just have the raw JWK, we'll use jwt.algorithms.RSAAlgorithm
        from jwt.algorithms import RSAAlgorithm
        public_key = RSAAlgorithm.from_jwk(rsa_key)
        
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False} # Validate audience in production
        )
        
        clerk_id = payload.get("sub")
        if not clerk_id:
            raise HTTPException(status_code=401, detail="Token missing subject")
            
        # JIT User Upsert in PostgreSQL
        async with AsyncSessionLocal() as session:
            # Look up user by clerk_id
            user_record = await session.scalar(
                select(User).where(User.clerk_id == clerk_id)
            )
            
            if not user_record:
                # Create the user on the fly.
                user_record = User(
                    clerk_id=clerk_id,
                    email=payload.get("email_addresses", [""])[0] if payload.get("email_addresses") else "",
                    plan="free" # Default plan
                )
                session.add(user_record)
                await session.commit()
                await session.refresh(user_record)
                
            return user_record

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
