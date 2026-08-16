"""
utils.py —— 负责读取成绩单文件

支持两种格式:
  1. CSV 文件(教务系统导出后另存为 CSV,或手工整理)
  2. Excel 文件(.xlsx)

成绩单需要包含以下列(列名可以是中文):
  学期 | 课程名 | 学分 | 成绩
"""

import os
import pandas as pd

# 允许的列名写法(教务系统导出的表头五花八门,这里做兼容)
COLUMN_ALIASES = {
    "学期": ["学期", "开课学期", "term", "学期名称"],
    "课程名": ["课程名", "课程名称", "课程", "科目", "course"],
    "学分": ["学分", "credit", "credits"],
    "成绩": ["成绩", "分数", "总评成绩", "score", "grade"],
}


def read_transcript(path: str, grade_map: dict = None) -> pd.DataFrame:
    """读取成绩单文件,返回规范化的 DataFrame(可以理解为一张表格)。

    参数:
        path: 成绩单文件路径,支持 .csv 和 .xlsx
        grade_map: 等级成绩到百分制的映射(如 {"优秀": 95}),
                   来自学校规则配置文件,不传则用默认映射
    返回:
        包含 [学期, 课程名, 学分, 成绩] 四列的表格
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件: {path}\n请检查路径是否正确")

    # 根据扩展名选择读取方式
    if path.lower().endswith(".csv"):
        # encoding 用 utf-8-sig 是为了兼容 Excel 另存 CSV 时加的 BOM 头
        df = pd.read_csv(path, encoding="utf-8-sig")
    elif path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        raise ValueError(f"不支持的文件格式: {path}\n目前支持 .csv 和 .xlsx")

    # 把各种写法的列名统一成标准列名
    df = _normalize_columns(df)

    # 去掉成绩或学分为空的行(比如体育课缓考、还没出分的课)
    df = df.dropna(subset=["成绩", "学分"])

    # 学分转成数字,成绩可能有"95"字符串或"优秀"等级,先统一处理
    df["学分"] = pd.to_numeric(df["学分"], errors="coerce")
    df["成绩"] = df["成绩"].apply(lambda s: _score_to_number(s, grade_map))
    df = df.dropna(subset=["学分", "成绩"])

    return df[["学期", "课程名", "学分", "成绩"]].reset_index(drop=True)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把教务系统各种列名统一映射成标准列名。"""
    rename_map = {}
    for std_name, aliases in COLUMN_ALIASES.items():
        for col in df.columns:
            if str(col).strip().lower() in [a.lower() for a in aliases]:
                rename_map[col] = std_name
                break
    df = df.rename(columns=rename_map)

    missing = [c for c in COLUMN_ALIASES if c not in df.columns]
    if missing:
        raise ValueError(
            f"成绩单缺少这些列: {missing}\n"
            f"请确保表格包含: 学期、课程名、学分、成绩"
        )
    return df


# 默认的等级成绩转换规则(常见高校标准)
DEFAULT_GRADE_MAP = {"优秀": 95, "良好": 85, "中等": 75, "及格": 65, "不及格": 50}


def _score_to_number(score, grade_map: dict = None) -> float:
    """把各种形式的成绩统一转换成百分制数字。

    参数 grade_map 来自学校规则配置文件,可以覆盖默认映射,
    例如有的学校"合格/不合格"两档制,可以配 {"合格": 75, "不合格": 50}。
    """
    # 自定义映射优先,没覆盖到的等级退回默认映射
    effective_map = {**DEFAULT_GRADE_MAP, **(grade_map or {})}
    if isinstance(score, str):
        s = score.strip()
        if s in effective_map:
            return float(effective_map[s])
        try:
            return float(s)
        except ValueError:
            return float("nan")  # 无法识别的成绩,返回空值
    try:
        return float(score)
    except (TypeError, ValueError):
        return float("nan")
