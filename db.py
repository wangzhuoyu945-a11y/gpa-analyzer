"""
db.py —— 数据存储层

用 SQLite 保存每位测试者的成绩数据和 GPA 对比结果。
SQLite 是 Python 自带的,不需要额外安装,数据存在一个 .db 文件里。

数据库结构:
  submissions 表: 每次提交的元数据(时间、规则、计算GPA、学长填的GPA、差异)
  courses 表: 每次提交包含的各门课程明细
"""

import sqlite3
import os
import json
from datetime import datetime

# 数据库文件路径(与项目根目录同级)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "submissions.db")

# 管理员密码(部署到公网时请改成你自己的密码,不要用默认值)
ADMIN_PASSWORD = "ymyc2026"


def _get_conn():
    """获取数据库连接,自动创建 data/ 目录和表结构。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让查询结果可以通过列名访问
    _init_tables(conn)
    return conn


def _init_tables(conn):
    """创建数据库表(如果不存在的话)。"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT DEFAULT '',
            rule_name TEXT NOT NULL,
            rule_scale REAL NOT NULL,
            calc_gpa REAL NOT NULL,
            calc_weighted_avg REAL NOT NULL,
            declared_gpa REAL,
            gpa_diff REAL,
            total_credits REAL,
            total_courses INTEGER,
            submitted_at TEXT NOT NULL,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            semester TEXT,
            course_name TEXT,
            credits REAL,
            score REAL,
            gpa_point REAL,
            FOREIGN KEY (submission_id) REFERENCES submissions(id)
        );
    """)
    conn.commit()


def save_submission(nickname, rule_name, rule_scale, courses_df, calc_gpa,
                    calc_weighted_avg, declared_gpa=None, notes=""):
    """保存一次提交到数据库。

    参数:
        nickname: 测试者昵称(可选)
        rule_name: 使用的规则名称
        rule_scale: 满绩点
        courses_df: DataFrame,包含 [学期, 课程名, 学分, 成绩, 绩点] 列
        calc_gpa: 计算出的 GPA
        calc_weighted_avg: 计算出的加权平均分
        declared_gpa: 测试者填的"学校给的GPA"(可选)
        notes: 备注信息(可选)
    返回:
        submission_id
    """
    conn = _get_conn()
    gpa_diff = None
    if declared_gpa is not None and declared_gpa != "":
        gpa_diff = round(calc_gpa - float(declared_gpa), 3)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.execute(
        """INSERT INTO submissions
           (nickname, rule_name, rule_scale, calc_gpa, calc_weighted_avg,
            declared_gpa, gpa_diff, total_credits, total_courses, submitted_at, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (nickname, rule_name, rule_scale, calc_gpa, calc_weighted_avg,
         declared_gpa, gpa_diff,
         float(courses_df["学分"].sum()), len(courses_df), now, notes)
    )
    sub_id = cursor.lastrowid

    # 保存每门课程
    for _, row in courses_df.iterrows():
        conn.execute(
            """INSERT INTO courses (submission_id, semester, course_name, credits, score, gpa_point)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sub_id, str(row["学期"]), str(row["课程名"]),
             float(row["学分"]), float(row["成绩"]), float(row.get("绩点", 0)))
        )

    conn.commit()
    conn.close()
    return sub_id


def get_all_submissions():
    """获取所有提交记录(按时间倒序)。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM submissions ORDER BY submitted_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_submission_courses(submission_id):
    """获取某次提交的所有课程。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM courses WHERE submission_id = ? ORDER BY id",
        (submission_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_submissions_df():
    """获取所有提交的 DataFrame(方便 Streamlit 展示和导出)。"""
    import pandas as pd
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM submissions ORDER BY submitted_at DESC", conn
    )
    conn.close()
    return df


def get_stats():
    """获取汇总统计(用于管理员仪表盘)。"""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    with_declared = conn.execute(
        "SELECT COUNT(*) FROM submissions WHERE declared_gpa IS NOT NULL"
    ).fetchone()[0]
    avg_diff_row = conn.execute(
        "SELECT AVG(ABS(gpa_diff)) FROM submissions WHERE declared_gpa IS NOT NULL"
    ).fetchone()
    avg_diff = round(avg_diff_row[0], 3) if avg_diff_row[0] is not None else None
    matched = conn.execute(
        "SELECT COUNT(*) FROM submissions WHERE ABS(gpa_diff) < 0.01 AND declared_gpa IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    return {
        "总提交数": total,
        "含对比GPA数": with_declared,
        "平均绝对偏差": avg_diff,
        "完全匹配数": matched,
    }
