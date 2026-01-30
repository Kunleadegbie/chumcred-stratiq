# ==================================================
# services/auth.py — Authentication Service
# ==================================================

import hashlib

from db.repository import get_user_by_email


# ==================================================
# PASSWORD HASH
# ==================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ==================================================
# AUTHENTICATE USER
# ==================================================

def authenticate(email: str, password: str):
    """
    Authenticate user and enforce admin approval.
    Raises ValueError for pending users.
    """

    user = get_user_by_email(email)

    # User not found
    if not user:
        return None


    # Unpack DB row
    user_id, _, name, pw_hash, role, active = user


    # Account not yet approved
    if active != 1:
        raise ValueError(
            "Account pending approval. Please wait for admin."
        )


    # Wrong password
    if hash_password(password) != pw_hash:
        return None


    # Success
    return {
        "id": user_id,
        "name": name,
        "email": email,
        "role": role
    }
