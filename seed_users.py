import sqlite3
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DATABASE = os.getenv("DATABASE_PATH", "database.db")

users = [
    ("submitter01", generate_password_hash("submitter123"), "submitter", "業務部"),
    ("agent01", generate_password_hash("agent123"), "agent", "客服部"),
    ("admin01", generate_password_hash("admin123"), "admin", "管理部"),
]

try:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    for username, password_hash, role, department in users:
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, role, department)
            VALUES (?, ?, ?, ?)
        """, (username, password_hash, role, department))

    conn.commit()
    conn.close()

    print("測試帳號建立完成")
    print("submitter01 / submitter123")
    print("agent01 / agent123")
    print("admin01 / admin123")

except Exception as e:
    print(f"建立測試帳號失敗：{e}")