"""
Databricks Apps Authentication

When deployed as a Databricks App, the platform handles user authentication.
User information is passed via HTTP headers:
- X-Forwarded-Email: User's email address
- X-Forwarded-User: User's display name
- X-Forwarded-Access-Token: OAuth token (if needed for API calls)

For local development, you can:
1. Set LOCAL_DEV_EMAIL env var to simulate a user
2. Pass X-Forwarded-Email header manually
"""
import os
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Generator
from uuid import uuid4
from dotenv import load_dotenv
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import log_info

# Load .env before reading env vars at module level
load_dotenv()

# Import User model only for type checking to avoid circular import
if TYPE_CHECKING:
    from app.models.user import User


# Header names used by Databricks Apps (for backwards compatibility exports)
FORWARDED_EMAIL_HEADER = "X-Forwarded-Email"
FORWARDED_USER_HEADER = "X-Forwarded-User"
FORWARDED_ACCESS_TOKEN_HEADER = "X-Forwarded-Access-Token"

# Extended header list (check both cases for flexibility).
# Includes headers from both this app's original auth module and the ported
# observability module's app.observability.core.dependencies._USER_HEADERS
# (x-databricks-user-email, x-auth-request-user, remote-user) — the two
# sibling apps used different header names for the same Databricks Apps
# proxy identity. See satsyil_lakemeterplus/docs/merge-tasks.md task #7 for
# the deeper unification (one shared resolver function) still to do.
EMAIL_HEADERS = [
    "X-Forwarded-Email",
    "x-forwarded-email",
    "X-Forwarded-Preferred-Username",
    "x-forwarded-preferred-username",
    "X-Databricks-User-Email",
    "x-databricks-user-email",
]
USER_HEADERS = [
    "X-Forwarded-User",
    "x-forwarded-user",
    "X-Forwarded-Name",
    "x-forwarded-name",
    "X-Auth-Request-User",
    "x-auth-request-user",
    "Remote-User",
    "remote-user",
]

# Environment variable for local development
LOCAL_DEV_EMAIL = os.getenv("LOCAL_DEV_EMAIL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")


def get_user_from_headers(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract user info from request headers.
    
    Returns:
        Tuple of (email, display_name)
    """
    email = None
    display_name = None
    
    # Try multiple possible header names (Databricks Apps may use different ones)
    for header in EMAIL_HEADERS:
        email = request.headers.get(header)
        if email:
            break
    
    for header in USER_HEADERS:
        display_name = request.headers.get(header)
        if display_name:
            break
    
    # Fallback to local dev email if set (for local development)
    if not email and LOCAL_DEV_EMAIL:
        email = LOCAL_DEV_EMAIL
        display_name = LOCAL_DEV_EMAIL.split("@")[0]
    
    return email, display_name


def debug_headers(request: Request) -> dict:
    """Return all headers for debugging auth issues."""
    return {
        "all_headers": dict(request.headers),
        "email_found": get_user_from_headers(request)[0],
        "environment": ENVIRONMENT,
        "local_dev_email_set": bool(LOCAL_DEV_EMAIL),
    }


def get_or_create_user(db: Session, email: str, full_name: Optional[str] = None) -> "User":
    """
    Get existing user by email or create a new one.
    
    Args:
        db: Database session
        email: User's email address
        full_name: User's display name (optional)
    
    Returns:
        User object
    """
    # Import User here to avoid circular import
    from app.models.user import User
    
    # Try to find existing user
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        # Only update last_login if it's been > 5 minutes (avoid excessive DB writes)
        now = datetime.utcnow()
        should_update = (
            user.last_login_at is None or 
            (now - user.last_login_at).total_seconds() > 300  # 5 minutes
        )
        
        if should_update or (full_name and not user.full_name):
            if should_update:
                user.last_login_at = now
            if full_name and not user.full_name:
                user.full_name = full_name
            db.commit()
        
        return user
    
    # Create new user
    user = User(
        user_id=uuid4(),
        email=email,
        full_name=full_name,
        role="user",
        is_active=True,
        last_login_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    log_info(f"Created new user: {email}")
    return user


def _get_db() -> Generator[Session, None, None]:
    """Get database session - avoids circular import."""
    from app.database import get_db
    yield from get_db()


async def get_current_user(
    request: Request,
    db: Session = Depends(_get_db)
) -> "User":
    """
    FastAPI dependency to get the current authenticated user.
    
    This extracts user info from Databricks Apps headers and returns
    the corresponding User object from the database.
    
    Raises:
        HTTPException 401 if not authenticated
    """
    email, display_name = get_user_from_headers(request)
    
    if not email:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please access through Databricks Apps.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = get_or_create_user(db, email, display_name)
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is disabled"
        )
    
    return user


async def get_optional_user(
    request: Request,
    db: Session = Depends(_get_db)
) -> Optional["User"]:
    """
    FastAPI dependency to get current user if authenticated, otherwise None.
    
    Use this for endpoints that work with or without authentication.
    """
    email, display_name = get_user_from_headers(request)
    
    if not email:
        return None
    
    try:
        return get_or_create_user(db, email, display_name)
    except Exception:
        return None
