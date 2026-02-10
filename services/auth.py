# services/auth.py
import os
import hashlib
import streamlit as st
from db.repository import get_user_by_email


def hash_password(password: str) -> str:
    salt = st.secrets.get("AUTH_SALT", os.environ.get("AUTH_SALT", "change_me_salt"))
    pepper = st.secrets.get("AUTH_PEPPER", os.environ.get("AUTH_PEPPER", "change_me_pepper"))
    return hashlib.sha256((password + salt + pepper).encode("utf-8")).hexdigest()


def check_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == (password_hash or "")


def authenticate(email: str, password: str):
    """
    Returns:
      {id,email,name,role} on success
      None on invalid credentials
      "PENDING" when inactive user tries to login (non-admin)
    """
    user = get_user_by_email(email)
    if not user:
        return None

    user_id, _, name, pw_hash, role, active = user

    if not check_password(password, pw_hash):
        return None

    role_norm = (role or "").strip().lower()

    # ✅ Allow Admin/CEO to login even if is_active=0 (prevents lockout)
    if role_norm not in ("admin", "ceo"):
        if int(active or 0) != 1:
            return "PENDING"

    return {
        "id": user_id,
        "email": email.strip(),
        "name": name or "",
        "role": role or "User"
    }
