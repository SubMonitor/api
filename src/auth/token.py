from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

from src.core import config, get_logger
from src.db.users.schemas import TokenPayload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, config.secret_key, algorithm=config.algorithm)

def decode_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[config.algorithm])
        payload["sub"] = int(payload["sub"])
        return TokenPayload(**payload)
    except JWTError as e:
        get_logger(__name__).warning(e)
        return None