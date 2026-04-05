import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    charset="utf8mb4"
)
cursor = conn.cursor()

users = [
    ("admin01", generate_password_hash("admin123"), "admin", "管理部"),
    ("agent01", generate_password_hash("agent123"), "agent", "客服部"),
    ("submitter01", generate_password_hash("submitter123"), "submitter", "業務部"),
]

for username, password_hash, role, department in users:
    cursor.execute("""
        INSERT IGNORE INTO users (username, password_hash, role, department)
        VALUES (%s, %s, %s, %s)
    """, (username, password_hash, role, department))

conn.commit()
cursor.close()
conn.close()

print("測試帳號建立完成")
print("admin01 / admin123")
print("agent01 / agent123")
print("submitter01 / submitter123")