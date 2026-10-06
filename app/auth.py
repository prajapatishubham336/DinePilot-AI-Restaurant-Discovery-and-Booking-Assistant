import hashlib
import secrets
import sqlite3
from .db import DB_PATH


def init_auth():
    con = sqlite3.connect(DB_PATH)

    con.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.commit()
    con.close()


def hash_password(password):
    salt = secrets.token_hex(16)

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100000
    )

    return f"{salt}${key.hex()}"


def verify_password(password, stored):
    try:
        salt, saved_key = stored.split("$")

        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000
        )

        return key.hex() == saved_key

    except ValueError:
        return False


def register_user(name, email, password, role="user"):
    init_auth()

    con = sqlite3.connect(DB_PATH)

    try:
        con.execute("""
        INSERT INTO users(name,email,password_hash,role)
        VALUES(?,?,?,?)
        """, (
            name,
            email.lower().strip(),
            hash_password(password),
            role
        ))

        con.commit()
        return True, "Account created."

    except sqlite3.IntegrityError:
        return False, "Email already exists."

    finally:
        con.close()


def login_user(email, password):
    init_auth()

    con = sqlite3.connect(DB_PATH)

    row = con.execute("""
    SELECT id, name, email, password_hash, role
    FROM users
    WHERE email=?
    """, (email.lower().strip(),)).fetchone()

    con.close()

    if not row:
        return None

    user_id, name, email, password_hash, role = row

    if not verify_password(password, password_hash):
        return None

    return {
        "id": user_id,
        "name": name,
        "email": email,
        "role": role
    }