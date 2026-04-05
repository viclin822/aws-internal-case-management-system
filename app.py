from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import os
import boto3
import uuid
from functools import wraps
from datetime import datetime, date
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key")

# Logging 設定
if not app.debug:
    handler = RotatingFileHandler(
        'logs/app.log', maxBytes=1024*1024*10, backupCount=3
    )
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.WARNING)

S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file_to_s3(file, case_id):
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"cases/{case_id}/{uuid.uuid4().hex}.{ext}"
    s3 = boto3.client("s3", region_name=S3_REGION)
    s3.upload_fileobj(file, S3_BUCKET, unique_filename)
    file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{unique_filename}"
    return unique_filename, file_url, file.filename, ext

db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="ticket_pool",
    pool_size=5,
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "ticket_user"),
    password=os.getenv("DB_PASSWORD", "Ticket@2026"),
    database=os.getenv("DB_NAME", "aws_ticket_system"),
    charset="utf8mb4"
)

def get_db_connection():
    return db_pool.get_connection()

def fetchone_as_dict(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))

def fetchall_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("請先登入系統", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if "user_id" not in session:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, department FROM users WHERE id = %s", (session["user_id"],))
    user = fetchone_as_dict(cursor)
    cursor.close()
    conn.close()
    return user

# ── 通知輔助函數 ──────────────────────────────────────────

def create_notification(user_id, case_id, message, event_type):
    """建立單一通知"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notifications (user_id, case_id, message, event_type, is_read, created_at) VALUES (%s,%s,%s,%s,0,%s)",
            (user_id, case_id, message, event_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass  # 通知失敗不影響主流程

def notify_agents(case_id, message, event_type):
    """通知所有 Agent 與 Admin"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE role IN ('agent', 'admin')")
        agents = cursor.fetchall()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for (agent_id,) in agents:
            cursor.execute(
                "INSERT INTO notifications (user_id, case_id, message, event_type, is_read, created_at) VALUES (%s,%s,%s,%s,0,%s)",
                (agent_id, case_id, message, event_type, now_str)
            )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

def get_unread_count(user_id):
    """取得未讀通知數量"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception:
        return 0

# ── 日期工具 ──────────────────────────────────────────────

def get_date_range(period):
    today = date.today()
    year = today.year
    month = today.month
    if period == "this_month":
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    elif period == "last_month":
        if month == 1:
            start = date(year - 1, 12, 1)
            end = date(year, 1, 1)
        else:
            start = date(year, month - 1, 1)
            end = date(year, month, 1)
    elif period == "q1":
        start = date(year, 1, 1); end = date(year, 4, 1)
    elif period == "q2":
        start = date(year, 4, 1); end = date(year, 7, 1)
    elif period == "q3":
        start = date(year, 7, 1); end = date(year, 10, 1)
    elif period == "q4":
        start = date(year, 10, 1); end = date(year + 1, 1, 1)
    elif period == "this_year":
        start = date(year, 1, 1); end = date(year + 1, 1, 1)
    else:
        return None, None
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

CATEGORIES = [
    "老師言語騷擾／不當行為", "退費爭議", "帳號違規（私自轉讓他人使用）",
    "投訴消基會／消保會", "7天鑑賞期學員上課不滿意（退費風險）",
    "老師上課品質不佳（打瞌睡／不認真）", "老師情緒問題／態度不良",
    "老師無故缺席（放鴿子）", "老師頻繁斷線", "系統異常／平台問題",
    "錄影檔問題（不完整／未上傳）", "課後評語／報告未上傳",
    "老師異動／代課不接受", "教材問題", "其他"
]
PRIORITY_OPTIONS = ["低", "中", "高"]
STATUS_OPTIONS = ["待處理", "處理中", "待追蹤", "已結案"]
PERIOD_OPTIONS = [
    ("", "全部"),
    ("this_month", "本月"),
    ("last_month", "上個月"),
    ("q1", "Q1（1-3月）"),
    ("q2", "Q2（4-6月）"),
    ("q3", "Q3（7-9月）"),
    ("q4", "Q4（10-12月）"),
    ("this_year", "今年"),
]

# ── 認證 Routes ───────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = fetchone_as_dict(cursor)
        cursor.close()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash("登入成功", "success")
            return redirect(url_for("index"))
        else:
            flash("帳號或密碼錯誤", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("已登出系統", "success")
    return redirect(url_for("login"))

# ── 首頁 ──────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    if current_user["role"] == "submitter":
        cursor.execute("SELECT COUNT(*) FROM cases WHERE submitter_id = %s", (current_user["id"],))
        total_cases = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cases WHERE submitter_id = %s AND status IN ('待處理','處理中','待追蹤')", (current_user["id"],))
        pending_cases = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cases WHERE submitter_id = %s AND status = '已結案'", (current_user["id"],))
        closed_cases = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM cases WHERE submitter_id = %s ORDER BY created_at DESC, id DESC LIMIT 5", (current_user["id"],))
        recent_cases = fetchall_as_dict(cursor)
    else:
        cursor.execute("SELECT COUNT(*) FROM cases")
        total_cases = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cases WHERE status IN ('待處理','處理中','待追蹤')")
        pending_cases = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cases WHERE status = '已結案'")
        closed_cases = cursor.fetchone()[0]
        cursor.execute("SELECT c.*, u.username AS submitter_name FROM cases c LEFT JOIN users u ON c.submitter_id = u.id ORDER BY c.created_at DESC, c.id DESC LIMIT 5")
        recent_cases = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()
    unread_count = get_unread_count(current_user["id"])
    return render_template("index.html", current_user=current_user, total_cases=total_cases,
        pending_cases=pending_cases, closed_cases=closed_cases, recent_cases=recent_cases,
        unread_count=unread_count)

# ── 通知 Routes ───────────────────────────────────────────

@app.route("/notifications")
@login_required
def notifications():
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.*, c.title as case_title
        FROM notifications n
        LEFT JOIN cases c ON n.case_id = c.id
        WHERE n.user_id = %s
        ORDER BY n.created_at DESC
        LIMIT 50
    """, (current_user["id"],))
    notifs = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()
    unread_count = get_unread_count(current_user["id"])
    return render_template("notifications.html", current_user=current_user,
                           notifications=notifs, unread_count=unread_count)

@app.route("/notifications/unread")
@login_required
def notifications_unread():
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.id, n.message, n.event_type, n.case_id, n.created_at, c.title as case_title
        FROM notifications n
        LEFT JOIN cases c ON n.case_id = c.id
        WHERE n.user_id = %s AND n.is_read = 0
        ORDER BY n.created_at DESC
        LIMIT 10
    """, (current_user["id"],))
    notifs = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()
    for n in notifs:
        if n.get("created_at"):
            n["created_at"] = n["created_at"].strftime("%m/%d %H:%M")
    return jsonify({"count": len(notifs), "notifications": notifs})

@app.route("/notifications/read_all", methods=["POST"])
@login_required
def notifications_read_all():
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (current_user["id"],))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(request.referrer or url_for("notifications"))

@app.route("/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def notification_read(notif_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE id = %s AND user_id = %s", (notif_id, current_user["id"]))
    notif = fetchone_as_dict(cursor)
    if notif:
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = %s", (notif_id,))
        conn.commit()
    cursor.close()
    conn.close()
    if notif:
        return redirect(url_for("ticket_detail", case_id=notif["case_id"]))
    return redirect(url_for("notifications"))

# ── 案件 Routes ───────────────────────────────────────────

@app.route("/tickets")
@login_required
def ticket_list():
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    status_filter = request.args.get("status", "").strip()
    category_filter = request.args.get("category", "").strip()
    keyword = request.args.get("keyword", "").strip()
    period = request.args.get("period", "").strip()
    start_date, end_date = get_date_range(period)

    base_query = "SELECT c.*, u.username AS submitter_name FROM cases c LEFT JOIN users u ON c.submitter_id = u.id WHERE 1=1"
    params = []
    if current_user["role"] == "submitter":
        base_query += " AND c.submitter_id = %s"
        params.append(current_user["id"])
    if status_filter:
        base_query += " AND c.status = %s"
        params.append(status_filter)
    if category_filter:
        base_query += " AND c.category = %s"
        params.append(category_filter)
    if keyword:
        base_query += " AND (c.title LIKE %s OR c.student_account LIKE %s OR c.student_name LIKE %s OR c.teacher_name LIKE %s OR c.description LIKE %s)"
        kw = f"%{keyword}%"
        params.extend([kw]*5)
    if start_date and end_date:
        base_query += " AND c.created_at >= %s AND c.created_at < %s"
        params.extend([start_date, end_date])
    base_query += " ORDER BY c.created_at DESC, c.id DESC"
    cursor.execute(base_query, params)
    cases = fetchall_as_dict(cursor)

    stat_query = "SELECT category, COUNT(*) as cnt FROM cases WHERE 1=1"
    stat_params = []
    if current_user["role"] == "submitter":
        stat_query += " AND submitter_id = %s"
        stat_params.append(current_user["id"])
    if start_date and end_date:
        stat_query += " AND created_at >= %s AND created_at < %s"
        stat_params.extend([start_date, end_date])
    stat_query += " GROUP BY category"
    cursor.execute(stat_query, stat_params)
    category_stats = fetchall_as_dict(cursor)

    cursor.close()
    conn.close()
    unread_count = get_unread_count(current_user["id"])
    return render_template("ticket_list.html", current_user=current_user, cases=cases,
        categories=CATEGORIES, status_options=STATUS_OPTIONS, period_options=PERIOD_OPTIONS,
        selected_status=status_filter, selected_category=category_filter,
        keyword=keyword, category_stats=category_stats, selected_period=period,
        unread_count=unread_count)

@app.route("/tickets/create", methods=["GET", "POST"])
@login_required
def create_ticket():
    current_user = get_current_user()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        priority = request.form.get("priority", "中").strip()
        student_account = request.form.get("student_account", "").strip().lower()
        student_name = request.form.get("student_name", "").strip()
        teacher_name = request.form.get("teacher_name", "").strip()
        department = request.form.get("department", "").strip()
        description = request.form.get("description", "").strip()
        refund_points = 1 if request.form.get("refund_points") == "on" else 0
        if not title or not category or not student_account or not description:
            flash("請填寫完整必填欄位", "danger")
            return render_template("create_ticket.html", current_user=current_user, categories=CATEGORIES, priority_options=PRIORITY_OPTIONS)
        if not student_account.startswith("wes") or len(student_account) != 9 or not student_account[3:].isdigit():
            flash("學員帳號格式錯誤，請輸入 wes + 6位數字", "danger")
            return render_template("create_ticket.html", current_user=current_user, categories=CATEGORIES, priority_options=PRIORITY_OPTIONS)
        if priority not in PRIORITY_OPTIONS:
            priority = "中"
        status = "待處理"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO cases (title, category, priority, student_account, student_name, teacher_name, department, description, status, submitter_id, refund_points, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (title, category, priority, student_account, student_name, teacher_name,
                  department if department else current_user["department"],
                  description, status, current_user["id"], refund_points, now_str, now_str))
            case_id = cursor.lastrowid
            cursor.execute("INSERT INTO case_status_logs (case_id, old_status, new_status, changed_by, note, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (case_id, None, status, current_user["id"], "案件建立", now_str))
            conn.commit()

            # 通知所有 Agent 有新案件
            notify_agents(case_id, f"📋 新案件：{title}", "new_case")

            files = request.files.getlist("attachments")
            for file in files:
                if file and file.filename and allowed_file(file.filename):
                    try:
                        s3_key, file_url, original_name, file_type = upload_file_to_s3(file, case_id)
                        cursor.execute("""
                            INSERT INTO case_attachments (case_id, file_name, file_path, file_url, file_type, uploaded_by, created_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (case_id, original_name, s3_key, file_url, file_type, current_user["id"], now_str))
                        conn.commit()
                    except Exception as upload_err:
                        flash(f"附件上傳失敗：{str(upload_err)}", "warning")
            flash("案件新增成功", "success")
            return redirect(url_for("ticket_detail", case_id=case_id))
        except Exception as e:
            conn.rollback()
            flash(f"新增案件失敗：{str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()
    return render_template("create_ticket.html", current_user=current_user, categories=CATEGORIES, priority_options=PRIORITY_OPTIONS)

@app.route("/tickets/<int:case_id>")
@login_required
def ticket_detail(case_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT c.*, u.username AS submitter_name, u.department AS submitter_department FROM cases c LEFT JOIN users u ON c.submitter_id = u.id WHERE c.id = %s", (case_id,))
    case = fetchone_as_dict(cursor)
    if not case:
        cursor.close(); conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))
    if current_user["role"] == "submitter" and case["submitter_id"] != current_user["id"]:
        cursor.close(); conn.close()
        flash("你沒有權限查看此案件", "danger")
        return redirect(url_for("ticket_list"))
    cursor.execute("SELECT * FROM case_attachments WHERE case_id = %s ORDER BY created_at DESC", (case_id,))
    attachments = fetchall_as_dict(cursor)
    if current_user["role"] == "submitter":
        cursor.execute("SELECT cc.*, u.username AS created_by_name FROM case_comments cc LEFT JOIN users u ON cc.created_by = u.id WHERE cc.case_id = %s AND cc.comment_type = 'external' ORDER BY cc.created_at DESC", (case_id,))
    else:
        cursor.execute("SELECT cc.*, u.username AS created_by_name FROM case_comments cc LEFT JOIN users u ON cc.created_by = u.id WHERE cc.case_id = %s ORDER BY cc.created_at DESC", (case_id,))
    comments = fetchall_as_dict(cursor)
    cursor.execute("SELECT l.*, u.username AS changed_by_name FROM case_status_logs l LEFT JOIN users u ON l.changed_by = u.id WHERE l.case_id = %s ORDER BY l.created_at DESC", (case_id,))
    status_logs = fetchall_as_dict(cursor)
    cursor.close(); conn.close()
    unread_count = get_unread_count(current_user["id"])
    return render_template("ticket_detail.html", current_user=current_user, case=case,
        attachments=attachments, comments=comments, status_logs=status_logs,
        status_options=STATUS_OPTIONS, unread_count=unread_count)

@app.route("/tickets/<int:case_id>/upload", methods=["POST"])
@login_required
def upload_attachment(case_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    case = fetchone_as_dict(cursor)
    if not case:
        cursor.close(); conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))
    if current_user["role"] == "submitter" and case["submitter_id"] != current_user["id"]:
        cursor.close(); conn.close()
        flash("你沒有權限操作此案件", "danger")
        return redirect(url_for("ticket_list"))
    files = request.files.getlist("attachments")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success_count = 0
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            try:
                s3_key, file_url, original_name, file_type = upload_file_to_s3(file, case_id)
                cursor.execute("""
                    INSERT INTO case_attachments (case_id, file_name, file_path, file_url, file_type, uploaded_by, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (case_id, original_name, s3_key, file_url, file_type, current_user["id"], now_str))
                conn.commit()
                success_count += 1
            except Exception as e:
                flash(f"上傳失敗：{str(e)}", "warning")
        elif file and file.filename:
            flash(f"不支援的檔案類型：{file.filename}", "warning")
    cursor.close(); conn.close()
    if success_count > 0:
        flash(f"成功上傳 {success_count} 個附件", "success")
    return redirect(url_for("ticket_detail", case_id=case_id))

@app.route("/attachments/<int:attachment_id>/view")
@login_required
def view_attachment(attachment_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM case_attachments WHERE id = %s", (attachment_id,))
    attachment = fetchone_as_dict(cursor)
    cursor.close(); conn.close()
    if not attachment:
        flash("查無此附件", "danger")
        return redirect(url_for("ticket_list"))
    if current_user["role"] == "submitter":
        conn2 = get_db_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT submitter_id FROM cases WHERE id = %s", (attachment["case_id"],))
        case = fetchone_as_dict(cursor2)
        cursor2.close(); conn2.close()
        if not case or case["submitter_id"] != current_user["id"]:
            flash("你沒有權限存取此附件", "danger")
            return redirect(url_for("ticket_list"))
    s3 = boto3.client("s3", region_name=S3_REGION)
    s3_key = attachment["file_url"].split(f"{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/")[1]
    presigned_url = s3.generate_presigned_url("get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key}, ExpiresIn=900)
    return redirect(presigned_url)

@app.route("/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def delete_attachment(attachment_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM case_attachments WHERE id = %s", (attachment_id,))
    attachment = fetchone_as_dict(cursor)
    if not attachment:
        cursor.close(); conn.close()
        flash("查無此附件", "danger")
        return redirect(url_for("ticket_list"))
    if current_user["role"] == "submitter" and attachment["uploaded_by"] != current_user["id"]:
        cursor.close(); conn.close()
        flash("你沒有權限刪除此附件", "danger")
        return redirect(url_for("ticket_detail", case_id=attachment["case_id"]))
    case_id = attachment["case_id"]
    try:
        s3 = boto3.client("s3", region_name=S3_REGION)
        s3_key = attachment["file_url"].split(f"{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/")[1]
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        cursor.execute("DELETE FROM case_attachments WHERE id = %s", (attachment_id,))
        conn.commit()
        flash("附件已刪除", "success")
    except Exception as e:
        conn.rollback()
        flash(f"刪除失敗：{str(e)}", "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for("ticket_detail", case_id=case_id))

@app.route("/tickets/<int:case_id>/toggle_refund", methods=["POST"])
@login_required
def toggle_refund(case_id):
    current_user = get_current_user()
    if current_user["role"] not in ["agent", "admin"]:
        flash("你沒有權限執行此操作", "danger")
        return redirect(url_for("ticket_detail", case_id=case_id))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT refund_points, submitter_id FROM cases WHERE id = %s", (case_id,))
    case = fetchone_as_dict(cursor)
    if not case:
        cursor.close(); conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))
    new_value = 0 if case["refund_points"] else 1
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = "已標記歸還" if new_value else "已取消歸還"
    try:
        cursor.execute("UPDATE cases SET refund_points=%s, updated_at=%s WHERE id=%s", (new_value, now_str, case_id))
        cursor.execute("INSERT INTO case_status_logs (case_id, old_status, new_status, changed_by, note, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (case_id, None, None, current_user["id"], f"歸還點數{label}", now_str))
        conn.commit()

        # 通知提交者歸還點數狀態更新
        create_notification(
            case["submitter_id"], case_id,
            f"🔄 你的案件歸還點數狀態：{label}",
            "refund_update"
        )
        flash(f"歸還點數{label}", "success")
    except Exception as e:
        conn.rollback()
        flash(f"操作失敗：{str(e)}", "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for("ticket_detail", case_id=case_id))

@app.route("/tickets/<int:case_id>/update_status", methods=["POST"])
@login_required
def update_status(case_id):
    current_user = get_current_user()
    if current_user["role"] not in ["agent", "admin"]:
        flash("你沒有權限執行此操作", "danger")
        return redirect(url_for("ticket_detail", case_id=case_id))
    new_status = request.form.get("status", "").strip()
    if new_status not in STATUS_OPTIONS:
        flash("無效的狀態", "danger")
        return redirect(url_for("ticket_detail", case_id=case_id))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, submitter_id FROM cases WHERE id = %s", (case_id,))
    case = fetchone_as_dict(cursor)
    if not case:
        cursor.close(); conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))
    old_status = case["status"]
    if old_status == new_status:
        cursor.close(); conn.close()
        return redirect(url_for("ticket_detail", case_id=case_id))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("UPDATE cases SET status=%s, updated_at=%s WHERE id=%s", (new_status, now_str, case_id))
        cursor.execute("INSERT INTO case_status_logs (case_id, old_status, new_status, changed_by, note, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (case_id, old_status, new_status, current_user["id"], f"狀態由「{old_status}」更新為「{new_status}」", now_str))
        conn.commit()

        # 通知提交者狀態已更新
        create_notification(
            case["submitter_id"], case_id,
            f"📌 你的案件狀態已更新為「{new_status}」",
            "status_update"
        )
        flash(f"狀態已更新為「{new_status}」", "success")
    except Exception as e:
        conn.rollback()
        flash(f"更新失敗：{str(e)}", "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for("ticket_detail", case_id=case_id))

@app.route("/tickets/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
def edit_ticket(case_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, department FROM users WHERE id = %s", (session["user_id"],))
    current_user = fetchone_as_dict(cursor)
    cursor.execute("SELECT c.*, u.username AS submitter_name, u.department AS submitter_department FROM cases c LEFT JOIN users u ON c.submitter_id = u.id WHERE c.id = %s", (case_id,))
    case = fetchone_as_dict(cursor)
    if not case:
        cursor.close(); conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))
    if current_user["role"] == "submitter" and case["submitter_id"] != current_user["id"]:
        cursor.close(); conn.close()
        flash("你沒有權限編輯此案件", "danger")
        return redirect(url_for("ticket_list"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        priority = request.form.get("priority", "").strip()
        student_account = request.form.get("student_account", "").strip().lower()
        student_name = request.form.get("student_name", "").strip()
        teacher_name = request.form.get("teacher_name", "").strip()
        department = request.form.get("department", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "").strip()
        new_comment = request.form.get("new_comment", "").strip()
        refund_points = 1 if request.form.get("refund_points") == "on" else 0
        if not title or not category or not student_account or not description:
            flash("請填寫完整必填欄位", "danger")
        elif not student_account.startswith("wes") or len(student_account) != 9 or not student_account[3:].isdigit():
            flash("學員帳號格式錯誤，請輸入 wes + 6位數字", "danger")
        else:
            try:
                old_status = case["status"]
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if current_user["role"] == "submitter":
                    status = case["status"]
                    priority = case["priority"]
                    refund_points = case.get("refund_points", 0)
                    new_comment = ""
                else:
                    if status not in STATUS_OPTIONS:
                        status = case["status"]
                    if priority not in PRIORITY_OPTIONS:
                        priority = case["priority"]
                cursor.execute("""
                    UPDATE cases SET title=%s, category=%s, priority=%s, student_account=%s,
                    student_name=%s, teacher_name=%s, department=%s, description=%s,
                    status=%s, refund_points=%s, updated_at=%s WHERE id=%s
                """, (title, category, priority, student_account, student_name, teacher_name,
                      department, description, status, refund_points,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), case_id))
                if current_user["role"] in ["agent","admin"] and old_status != status:
                    cursor.execute("INSERT INTO case_status_logs (case_id, old_status, new_status, changed_by, note, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                        (case_id, old_status, status, current_user["id"],
                         new_comment if new_comment else f"狀態由「{old_status}」更新為「{status}」",
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    # 通知提交者
                    create_notification(
                        case["submitter_id"], case_id,
                        f"📌 你的案件狀態已更新為「{status}」",
                        "status_update"
                    )
                elif current_user["role"] in ["agent","admin"] and new_comment:
                    cursor.execute("INSERT INTO case_status_logs (case_id, old_status, new_status, changed_by, note, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                        (case_id, status, status, current_user["id"], new_comment,
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                flash("案件資料已更新", "success")
                cursor.close(); conn.close()
                return redirect(url_for("ticket_detail", case_id=case_id))
            except Exception as e:
                conn.rollback()
                flash(f"更新失敗：{str(e)}", "danger")
    cursor.execute("SELECT l.*, u.username AS changed_by_name FROM case_status_logs l LEFT JOIN users u ON l.changed_by = u.id WHERE l.case_id = %s ORDER BY l.created_at DESC", (case_id,))
    status_logs = fetchall_as_dict(cursor)
    cursor.close(); conn.close()
    unread_count = get_unread_count(current_user["id"])
    return render_template("edit_ticket.html", case=case, current_user=current_user,
        categories=CATEGORIES, priority_options=PRIORITY_OPTIONS,
        status_options=STATUS_OPTIONS, status_logs=status_logs, unread_count=unread_count)

@app.route("/tickets/<int:case_id>/comments/add", methods=["POST"])
@login_required
def add_comment(case_id):
    current_user = get_current_user()
    comment = request.form.get("comment", "").strip()
    comment_type = request.form.get("comment_type", "external")
    if current_user["role"] == "submitter":
        comment_type = "external"
    if not comment:
        flash("請輸入備註內容", "danger")
        return redirect(url_for("ticket_detail", case_id=case_id))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    case = fetchone_as_dict(cursor)
    if not case:
        cursor.close(); conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))
    if current_user["role"] == "submitter" and case["submitter_id"] != current_user["id"]:
        cursor.close(); conn.close()
        flash("你沒有權限操作此案件", "danger")
        return redirect(url_for("ticket_list"))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("INSERT INTO case_comments (case_id, comment, comment_type, created_by, created_at) VALUES (%s,%s,%s,%s,%s)",
            (case_id, comment, comment_type, current_user["id"], now_str))
        conn.commit()

        # 通知邏輯
        if comment_type == "external":
            # 外部留言：通知提交者（若留言者不是提交者本人）
            if case["submitter_id"] != current_user["id"]:
                create_notification(
                    case["submitter_id"], case_id,
                    f"💬 你的案件「{case['title']}」有新留言",
                    "new_comment"
                )
        # 所有留言都通知 Agent（排除留言者本人）
        notify_agents_except(case_id, f"💬 案件「{case['title']}」有新留言", "new_comment", current_user["id"])

        flash("備註新增成功", "success")
    except Exception as e:
        conn.rollback()
        flash(f"新增備註失敗：{str(e)}", "danger")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for("ticket_detail", case_id=case_id))

@app.route("/admin/stats")
@login_required
def admin_stats():
    current_user = get_current_user()
    if current_user["role"] != "admin":
        flash("你沒有權限查看此頁面", "danger")
        return redirect(url_for("index"))
    period = request.args.get("period", "").strip()
    start_date, end_date = get_date_range(period)
    conn = get_db_connection()
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute("""
            SELECT u.username, COUNT(c.id) as closed_count
            FROM users u
            LEFT JOIN cases c ON c.submitter_id = u.id
                AND c.status = '已結案'
                AND c.updated_at >= %s AND c.updated_at < %s
            WHERE u.role = 'agent'
            GROUP BY u.id, u.username
            ORDER BY closed_count DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT u.username, COUNT(c.id) as closed_count
            FROM users u
            LEFT JOIN cases c ON c.submitter_id = u.id AND c.status = '已結案'
            WHERE u.role = 'agent'
            GROUP BY u.id, u.username
            ORDER BY closed_count DESC
        """)
    agent_stats = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()
    unread_count = get_unread_count(current_user["id"])
    return render_template("admin_stats.html", current_user=current_user,
        agent_stats=agent_stats, period_options=PERIOD_OPTIONS, selected_period=period,
        unread_count=unread_count)

# ── 額外輔助：通知 Agent 但排除自己 ──────────────────────

def notify_agents_except(case_id, message, event_type, exclude_user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE role IN ('agent', 'admin') AND id != %s", (exclude_user_id,))
        agents = cursor.fetchall()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for (agent_id,) in agents:
            cursor.execute(
                "INSERT INTO notifications (user_id, case_id, message, event_type, is_read, created_at) VALUES (%s,%s,%s,%s,0,%s)",
                (agent_id, case_id, message, event_type, now_str)
            )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

# ── 錯誤處理 ──────────────────────────────────────────────

# ── Health Check ──────────────────────────────────────────

@app.route("/health")
def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 500
    
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
