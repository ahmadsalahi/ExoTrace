"""
lib/auth.py — Authentication and Persistent Session Management for ExoTrace.
"""
import os
import json
import time
import hashlib
import secrets

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AUTH_FILE = os.path.join(_PROJECT_ROOT, "data", "auth.json")
_SESSIONS_FILE = os.path.join(_PROJECT_ROOT, "data", "sessions.json")

# 30 minutes inactivity timeout
SESSION_TIMEOUT_SECONDS = 30 * 60


def _legacy_hash_password(pw: str) -> str:
    return hashlib.sha256(pw.strip().encode("utf-8")).hexdigest()

def _hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.strip().encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"

def _verify_password(pw: str, stored: str) -> bool:
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iters, salt_hex, digest_hex = stored.split("$", 3)
            digest = hashlib.pbkdf2_hmac("sha256", pw.strip().encode("utf-8"), bytes.fromhex(salt_hex), int(iters))
            return secrets.compare_digest(digest.hex(), digest_hex)
        except Exception:
            return False
    return secrets.compare_digest(_legacy_hash_password(pw), stored)


def _init_default_auth() -> dict:
    default_data = {
        "username": "admin",
        "password_hash": _hash_password("admin123")
    }
    os.makedirs(os.path.dirname(_AUTH_FILE), exist_ok=True)
    with open(_AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(default_data, f, indent=2, ensure_ascii=False)
    return default_data


def get_auth_data() -> dict:
    if not os.path.exists(_AUTH_FILE):
        return _init_default_auth()
    try:
        with open(_AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "username" in data and "password_hash" in data:
                return data
            return _init_default_auth()
    except Exception:
        return _init_default_auth()


def verify_login(username: str, password: str) -> bool:
    data = get_auth_data()
    expected_user = str(data.get("username", "")).strip().lower()
    provided_user = str(username).strip().lower()
    if provided_user != expected_user:
        return False
    ok = _verify_password(password, data.get("password_hash", ""))
    if ok and not str(data.get("password_hash", "")).startswith("pbkdf2_sha256$"):
        data["password_hash"] = _hash_password(password)
        try:
            with open(_AUTH_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass
    return ok


def change_password(current_password: str, new_password: str) -> tuple[bool, str]:
    data = get_auth_data()
    if not _verify_password(current_password, data.get("password_hash", "")):
        return False, "كلمة المرور الحالية غير صحيحة."
    if len(new_password.strip()) < 8:
        return False, "يجب أن تتكون كلمة المرور الجديدة من 8 خانات على الأقل."

    data["password_hash"] = _hash_password(new_password)
    try:
        with open(_AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True, "تم تحديث كلمة المرور بنجاح!"
    except Exception as e:
        return False, f"حدث خطأ أثناء الحفظ: {e}"


# ── Session Management (30 Minutes Inactivity Timeout) ───────────────

def _load_sessions() -> dict:
    os.makedirs(os.path.dirname(_SESSIONS_FILE), exist_ok=True)
    if not os.path.exists(_SESSIONS_FILE):
        return {}
    try:
        with open(_SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_sessions(sessions: dict):
    os.makedirs(os.path.dirname(_SESSIONS_FILE), exist_ok=True)
    try:
        with open(_SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def create_session(username: str) -> str:
    """Create a new session token with a 30-minute inactivity timer."""
    sessions = _load_sessions()
    # Cleanup expired sessions first
    now = time.time()
    clean_sessions = {
        sid: s for sid, s in sessions.items()
        if now - s.get("last_activity", 0) <= SESSION_TIMEOUT_SECONDS
    }
    
    token = secrets.token_hex(24)
    clean_sessions[token] = {
        "username": username,
        "last_activity": now,
        "created_at": now
    }
    _save_sessions(clean_sessions)
    return token


def validate_and_refresh_session(session_id: str | None) -> tuple[bool, str | None]:
    """
    Validate session token. If valid and not expired, refreshes last_activity.
    Returns:
        (True, username) if session is valid and refreshed.
        (False, 'expired') if session exceeded 30 min idle time.
        (False, None) if session token does not exist.
    """
    if not session_id:
        return False, None

    sessions = _load_sessions()
    session = sessions.get(session_id)
    if not session:
        return False, None

    now = time.time()
    last_act = session.get("last_activity", 0)
    elapsed = now - last_act

    if elapsed > SESSION_TIMEOUT_SECONDS:
        # Inactivity timeout exceeded (30 mins without action)
        del sessions[session_id]
        _save_sessions(sessions)
        return False, "expired"

    # Refresh activity timestamp
    session["last_activity"] = now
    _save_sessions(sessions)
    return True, session.get("username", "admin")


def destroy_session(session_id: str | None):
    """Invalidate session on logout."""
    if not session_id:
        return
    sessions = _load_sessions()
    if session_id in sessions:
        del sessions[session_id]
        _save_sessions(sessions)


def set_session_theme(session_id: str | None, theme: str):
    """Save user theme preference in session storage."""
    if not session_id or theme not in ("light", "dark"):
        return
    sessions = _load_sessions()
    if session_id in sessions:
        sessions[session_id]["theme"] = theme
        _save_sessions(sessions)


def get_session_theme(session_id: str | None) -> str | None:
    """Retrieve user theme preference from session storage."""
    if not session_id:
        return None
    sessions = _load_sessions()
    session = sessions.get(session_id)
    if session and isinstance(session, dict):
        return session.get("theme")
    return None


def set_session_lang(session_id: str | None, lang: str):
    """Save user language preference in session storage."""
    if not session_id or lang not in ("ar", "en"):
        return
    sessions = _load_sessions()
    if session_id in sessions:
        sessions[session_id]["lang"] = lang
        _save_sessions(sessions)


def get_session_lang(session_id: str | None) -> str | None:
    """Retrieve user language preference from session storage."""
    if not session_id:
        return None
    sessions = _load_sessions()
    session = sessions.get(session_id)
    if session and isinstance(session, dict):
        return session.get("lang")
    return None
