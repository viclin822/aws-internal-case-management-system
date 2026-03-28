import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

conn = mysql.connector.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    user=os.environ.get("DB_USER", "ticket_user"),
    password=os.environ.get("DB_PASSWORD", "Ticket@2026"),
    database=os.environ.get("DB_NAME", "aws_ticket_system")
)
cursor = conn.cursor()

# 建立使用者
users = [
    ("submitter01", generate_password_hash("submitter123"), "submitter", "業務部"),
    ("agent01", generate_password_hash("agent123"), "agent", "客服部"),
    ("admin01", generate_password_hash("admin123"), "admin", "管理部"),
]
for u in users:
    cursor.execute("""
        INSERT INTO users (username, password_hash, role, department)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE role=VALUES(role)
    """, u)

# 建立測試案件
tickets = [
    ("系統登入異常", "系統問題", "高", "處理中", "wes123456", "王小明", "John", "業務部", "學員反映無法登入系統，錯誤代碼 403。"),
    ("課程影片無法播放", "課程問題", "中", "待處理", "wes234567", "李小華", "Mary", "業務部", "點擊播放後畫面空白，已嘗試重整無效。"),
    ("退費申請處理", "退費問題", "高", "待處理", "wes345678", "陳大同", "Tom", "客服部", "學員申請退費，需確認是否符合退費條件。"),
    ("學習進度顯示錯誤", "系統問題", "低", "已結案", "wes456789", "林美玲", "Mary", "業務部", "進度條顯示 0%，但實際已完成 80% 課程。"),
    ("講師回覆延遲", "課程問題", "中", "處理中", "wes567890", "張志明", "John", "客服部", "發問後超過 72 小時未獲回覆，學員反映強烈。"),
]
for t in tickets:
    cursor.execute("""
        INSERT INTO tickets (title, category, priority, status, student_id, student_name, tutor, department, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, t)

conn.commit()
cursor.close()
conn.close()
print("✅ 測試資料建立完成！")
