from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.users import repository


def register(db: Session, email: str, password: str) -> str:
    """Creates a new user and returns a JWT access token."""
    if repository.get_by_email(db, email):
        raise ConflictError("Email already registered")
    user = repository.create(db, email=email, hashed_password=hash_password(password))
    return create_access_token(str(user.id))


def login(db: Session, email: str, password: str) -> str:
    """Verifies credentials and returns a JWT access token."""
    user = repository.get_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")
    return create_access_token(str(user.id))
