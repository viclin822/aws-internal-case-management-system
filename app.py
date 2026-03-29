from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
from functools import wraps
from datetime import datetime
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key")


# =========================
# Database
# =========================
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "ticket_user"),
        password=os.getenv("DB_PASSWORD", "Ticket@2026"),
        database=os.getenv("DB_NAME", "aws_ticket_system"),
        charset="utf8mb4"
    )
    return conn


def fetchone_as_dict(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def fetchall_as_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# =========================
# Login Required Decorator
# =========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("請先登入系統", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# =========================
# Current User Helper
# =========================
def get_current_user():
    if "user_id" not in session:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, role, department
        FROM users
        WHERE id = %s
    """, (session["user_id"],))
    user = fetchone_as_dict(cursor)
    cursor.close()
    conn.close()
    return user


# =========================
# Choices
# =========================
CATEGORIES = [
    "課程問題",
    "教師問題",
    "教材問題",
    "系統問題",
    "客服問題",
    "排課問題",
    "其他"
]

PRIORITY_OPTIONS = ["低", "中", "高"]

STATUS_OPTIONS = ["待處理", "處理中", "待追蹤", "已結案"]


# =========================
# Login
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM users
            WHERE username = %s
        """, (username,))
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


# =========================
# Logout
# =========================
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("已登出系統", "success")
    return redirect(url_for("login"))


# =========================
# Index
# =========================
@app.route("/")
@login_required
def index():
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()

    if current_user["role"] == "submitter":
        cursor.execute("""
            SELECT COUNT(*) AS count FROM cases WHERE submitter_id = %s
        """, (current_user["id"],))
        total_cases = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) AS count FROM cases
            WHERE submitter_id = %s AND status IN ('待處理', '處理中', '待追蹤')
        """, (current_user["id"],))
        pending_cases = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) AS count FROM cases
            WHERE submitter_id = %s AND status = '已結案'
        """, (current_user["id"],))
        closed_cases = cursor.fetchone()[0]

        cursor.execute("""
            SELECT * FROM cases WHERE submitter_id = %s
            ORDER BY created_at DESC, id DESC LIMIT 5
        """, (current_user["id"],))
        recent_cases = fetchall_as_dict(cursor)
    else:
        cursor.execute("SELECT COUNT(*) FROM cases")
        total_cases = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM cases WHERE status IN ('待處理', '處理中', '待追蹤')
        """)
        pending_cases = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cases WHERE status = '已結案'")
        closed_cases = cursor.fetchone()[0]

        cursor.execute("""
            SELECT c.*, u.username AS submitter_name
            FROM cases c
            LEFT JOIN users u ON c.submitter_id = u.id
            ORDER BY c.created_at DESC, c.id DESC LIMIT 5
        """)
        recent_cases = fetchall_as_dict(cursor)

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        current_user=current_user,
        user_role=current_user["role"],
        total_cases=total_cases,
        pending_cases=pending_cases,
        closed_cases=closed_cases,
        recent_cases=recent_cases
    )


# =========================
# Ticket List
# =========================
@app.route("/tickets")
@login_required
def ticket_list():
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()

    status_filter = request.args.get("status", "").strip()
    category_filter = request.args.get("category", "").strip()
    keyword = request.args.get("keyword", "").strip()

    base_query = """
        SELECT c.*, u.username AS submitter_name
        FROM cases c
        LEFT JOIN users u ON c.submitter_id = u.id
        WHERE 1 = 1
    """
    params = []

    if current_user["role"] == "submitter":
        base_query += " AND c.submitter_id = %s "
        params.append(current_user["id"])

    if status_filter:
        base_query += " AND c.status = %s "
        params.append(status_filter)

    if category_filter:
        base_query += " AND c.category = %s "
        params.append(category_filter)

    if keyword:
        base_query += """
            AND (
                c.title LIKE %s
                OR c.student_account LIKE %s
                OR c.student_name LIKE %s
                OR c.teacher_name LIKE %s
                OR c.description LIKE %s
            )
        """
        keyword_like = f"%{keyword}%"
        params.extend([keyword_like] * 5)

    base_query += " ORDER BY c.created_at DESC, c.id DESC "

    cursor.execute(base_query, params)
    cases = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()

    return render_template(
        "ticket_list.html",
        current_user=current_user,
        user_role=current_user["role"],
        cases=cases,
        categories=CATEGORIES,
        status_options=STATUS_OPTIONS,
        selected_status=status_filter,
        selected_category=category_filter,
        keyword=keyword
    )


# =========================
# Create Ticket
# =========================
@app.route("/tickets/create", methods=["GET", "POST"])
@login_required
def create_ticket():
    current_user = get_current_user()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        priority = request.form.get("priority", "中").strip()
        student_account = request.form.get("student_account", "").strip()
        student_name = request.form.get("student_name", "").strip()
        teacher_name = request.form.get("teacher_name", "").strip()
        department = request.form.get("department", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not category or not student_account or not description:
            flash("請填寫完整必填欄位", "danger")
            return render_template(
                "create_ticket.html",
                current_user=current_user,
        user_role=current_user["role"],
                categories=CATEGORIES,
                priority_options=PRIORITY_OPTIONS
            )

        if not student_account.startswith("wes") or len(student_account) != 9 or not student_account[3:].isdigit():
            flash("學員帳號格式錯誤，請輸入 wes + 6位數字", "danger")
            return render_template(
                "create_ticket.html",
                current_user=current_user,
        user_role=current_user["role"],
                categories=CATEGORIES,
                priority_options=PRIORITY_OPTIONS
            )

        status = "待處理"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO cases (
                    title, category, priority, student_account, student_name,
                    teacher_name, department, description, status,
                    submitter_id, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                title,
                category,
                priority if current_user["role"] in ["agent", "admin"] else "中",
                student_account,
                student_name,
                teacher_name,
                department if department else current_user["department"],
                description,
                status,
                current_user["id"],
                now_str,
                now_str
            ))

            case_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO case_status_logs (
                    case_id, old_status, new_status, changed_by, note, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (case_id, None, status, current_user["id"], "案件建立", now_str))

            conn.commit()
            flash("案件新增成功", "success")
            return redirect(url_for("ticket_detail", case_id=case_id))

        except Exception as e:
            conn.rollback()
            flash(f"新增案件失敗：{str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template(
        "create_ticket.html",
        current_user=current_user,
        user_role=current_user["role"],
        categories=CATEGORIES,
        priority_options=PRIORITY_OPTIONS
    )


# =========================
# Ticket Detail
# =========================
@app.route("/tickets/<int:case_id>")
@login_required
def ticket_detail(case_id):
    current_user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, u.username AS submitter_name, u.department AS submitter_department
        FROM cases c
        LEFT JOIN users u ON c.submitter_id = u.id
        WHERE c.id = %s
    """, (case_id,))
    case = fetchone_as_dict(cursor)

    if not case:
        cursor.close()
        conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))

    if current_user["role"] == "submitter" and case["submitter_id"] != current_user["id"]:
        cursor.close()
        conn.close()
        flash("你沒有權限查看此案件", "danger")
        return redirect(url_for("ticket_list"))

    cursor.execute("""
        SELECT * FROM case_attachments WHERE case_id = %s ORDER BY created_at DESC, id DESC
    """, (case_id,))
    attachments = fetchall_as_dict(cursor)

    cursor.execute("""
        SELECT cc.*, u.username AS created_by_name
        FROM case_comments cc
        LEFT JOIN users u ON cc.created_by = u.id
        WHERE cc.case_id = %s ORDER BY cc.created_at DESC, cc.id DESC
    """, (case_id,))
    comments = fetchall_as_dict(cursor)

    cursor.execute("""
        SELECT l.*, u.username AS changed_by_name
        FROM case_status_logs l
        LEFT JOIN users u ON l.changed_by = u.id
        WHERE l.case_id = %s ORDER BY l.created_at DESC, l.id DESC
    """, (case_id,))
    status_logs = fetchall_as_dict(cursor)

    cursor.close()
    conn.close()

    return render_template(
        "ticket_detail.html",
        current_user=current_user,
        user_role=current_user["role"],
        case=case,
        attachments=attachments,
        comments=comments,
        status_logs=status_logs
    )


# =========================
# Edit Ticket
# =========================
@app.route("/tickets/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
def edit_ticket(case_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, role, department FROM users WHERE id = %s
    """, (session["user_id"],))
    current_user = fetchone_as_dict(cursor)

    cursor.execute("""
        SELECT c.*, u.username AS submitter_name, u.department AS submitter_department
        FROM cases c
        LEFT JOIN users u ON c.submitter_id = u.id
        WHERE c.id = %s
    """, (case_id,))
    case = fetchone_as_dict(cursor)

    if not case:
        cursor.close()
        conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))

    if current_user["role"] == "submitter" and case["submitter_id"] != current_user["id"]:
        cursor.close()
        conn.close()
        flash("你沒有權限編輯此案件", "danger")
        return redirect(url_for("ticket_list"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        priority = request.form.get("priority", "").strip()
        student_account = request.form.get("student_account", "").strip()
        student_name = request.form.get("student_name", "").strip()
        teacher_name = request.form.get("teacher_name", "").strip()
        department = request.form.get("department", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "").strip()
        new_comment = request.form.get("new_comment", "").strip()

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
                    new_comment = ""
                else:
                    if status not in STATUS_OPTIONS:
                        status = case["status"]
                    if priority not in PRIORITY_OPTIONS:
                        priority = case["priority"]

                cursor.execute("""
                    UPDATE cases SET
                        title=%s, category=%s, priority=%s, student_account=%s,
                        student_name=%s, teacher_name=%s, department=%s,
                        description=%s, status=%s, updated_at=%s
                    WHERE id=%s
                """, (
                    title, category, priority, student_account,
                    student_name, teacher_name, department,
                    description, status, now_str, case_id
                ))

                if current_user["role"] in ["agent", "admin"] and old_status != status:
                    cursor.execute("""
                        INSERT INTO case_status_logs (
                            case_id, old_status, new_status, changed_by, note, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        case_id, old_status, status, current_user["id"],
                        new_comment if new_comment else f"案件狀態由「{old_status}」更新為「{status}」",
                        now_str
                    ))
                elif current_user["role"] in ["agent", "admin"] and new_comment:
                    cursor.execute("""
                        INSERT INTO case_status_logs (
                            case_id, old_status, new_status, changed_by, note, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (case_id, status, status, current_user["id"], new_comment, now_str))

                conn.commit()
                flash("案件資料已更新", "success")
                cursor.close()
                conn.close()
                return redirect(url_for("ticket_detail", case_id=case_id))

            except Exception as e:
                conn.rollback()
                flash(f"更新失敗：{str(e)}", "danger")

    cursor.execute("""
        SELECT l.*, u.username AS changed_by_name
        FROM case_status_logs l
        LEFT JOIN users u ON l.changed_by = u.id
        WHERE l.case_id = %s ORDER BY l.created_at DESC, l.id DESC
    """, (case_id,))
    status_logs = fetchall_as_dict(cursor)

    cursor.close()
    conn.close()

    return render_template(
        "edit_ticket.html",
        case=case,
        current_user=current_user,
        user_role=current_user["role"],
        categories=CATEGORIES,
        priority_options=PRIORITY_OPTIONS,
        status_options=STATUS_OPTIONS,
        status_logs=status_logs
    )


# =========================
# Add Comment
# =========================
@app.route("/tickets/<int:case_id>/comments/add", methods=["POST"])
@login_required
def add_comment(case_id):
    current_user = get_current_user()
    comment = request.form.get("comment", "").strip()

    if not comment:
        flash("請輸入備註內容", "danger")
        return redirect(url_for("ticket_detail", case_id=case_id))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    case = fetchone_as_dict(cursor)

    if not case:
        cursor.close()
        conn.close()
        flash("查無此案件", "danger")
        return redirect(url_for("ticket_list"))

    if current_user["role"] == "submitter" and case["submitter_id"] != current_user["id"]:
        cursor.close()
        conn.close()
        flash("你沒有權限操作此案件", "danger")
        return redirect(url_for("ticket_list"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute("""
            INSERT INTO case_comments (case_id, comment, created_by, created_at)
            VALUES (%s, %s, %s, %s)
        """, (case_id, comment, current_user["id"], now_str))
        conn.commit()
        flash("備註新增成功", "success")
    except Exception as e:
        conn.rollback()
        flash(f"新增備註失敗：{str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("ticket_detail", case_id=case_id))


# =========================
# Error Handlers
# =========================
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


# =========================
# Run App
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)