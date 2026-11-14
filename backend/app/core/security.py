"""Password hashes, API key hashes, and session tokens."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

SESSION_COOKIE = "qaflow_session"
_BCRYPT_ROUNDS = 12
_PASSWORD_MAX_BYTES = 72
_dummy_hash: str | None = None


class SignInNotConfigured(Exception):
    """JWT_SECRET is empty, so a session cookie cannot be issued."""


class TokenError(Exception):
    """The session token is missing, expired, or signed with the wrong secret."""


class PasswordTooLong(Exception):
    """bcrypt only uses the first 72 bytes. Refuse the password instead of truncating it."""


def hash_password(password: str) -> str:
    encoded = _password_bytes(password)
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        encoded = _password_bytes(password)
    except PasswordTooLong:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        return False


def dummy_password_hash() -> str:
    """A real bcrypt hash used when the account has no password, so the check still takes time."""

    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("not-a-real-password")
    return _dummy_hash


def generate_api_key() -> tuple[str, str, str]:
    """Return the plaintext key, its public prefix, and the SHA-256 hex digest."""

    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    token = f"qf_{prefix}_{secret}"
    return token, prefix, hash_api_key(token)


def hash_api_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def encode_user_token(user_id: int) -> str:
    settings = get_settings()
    if not settings.jwt_secret:
        raise SignInNotConfigured
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def decode_user_id(token: str) -> int:
    settings = get_settings()
    if not settings.jwt_secret:
        raise TokenError
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise TokenError from exc


def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > _PASSWORD_MAX_BYTES:
        raise PasswordTooLong
    return encoded
