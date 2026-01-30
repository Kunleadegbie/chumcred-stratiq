from db.repository import create_user
from services.auth import hash_password

create_user(
    email="admin@company.com",
    name="System Admin",
    password_hash=hash_password("admin123"),
    role="Admin"
)

print("Admin created")
