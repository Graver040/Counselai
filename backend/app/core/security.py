from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(pwd: str) -> str:
    return generate_password_hash(pwd)

def verify_password(pwd: str, hashed: str) -> bool:
    return check_password_hash(hashed, pwd)
