"""
analyzer.py —— 统计分析模块

对成绩单做多维度分析,为报告生成提供数据:
  1. 各学期 GPA/加权平均分趋势
  2. 薄弱课程识别(成绩偏低的课程)
  3. 学分分布(专业课 vs 公共课等)
  4. 总学分、总课程数等基本统计
"""

from collections import defaultdict
from gpa import calc_gpa, calc_weighted_avg


def analyze_by_semester(df, rules=None):
    """按学期分组,计算每个学期的统计指标。

    参数 rules: 绩点规则(RuleSet 或规则列表),传 None 用内置默认规则。
    返回一个列表,每个元素是一个学期的分析结果(字典)。
    """
    semesters = []
    grouped = df.groupby("学期", sort=False)
    for name, group in grouped:
        semesters.append({
            "学期": name,
            "课程数": len(group),
            "总学分": group["学分"].sum(),
            "加权平均分": round(calc_weighted_avg(group), 2),
            "GPA": round(calc_gpa(group, rules), 3),
            "最高分": group["成绩"].max(),
            "最低分": group["成绩"].min(),
        })
    return semesters


def find_weak_courses(df, threshold=70) -> list:
    """找出成绩低于阈值的课程(默认70分),帮助发现薄弱环节。

    返回列表,每个元素是一个字典,包含课程名、成绩、学分、绩点。
    """
    weak = df[df["成绩"] < threshold].sort_values("成绩")
    return weak[["课程名", "成绩", "学分", "学期"]].to_dict("records")


def credit_distribution(df) -> dict:
    """统计学分分布(按课程类别关键词粗略分类)。

    这个功能是个简化版:根据课程名中的关键词判断类别。
    真实成绩单一般有"课程类别"列,后续可以扩展。

    返回 {"类别名": 学分总和} 的字典。
    """
    category_keywords = {
        "数学类": ["数学", "高数", "线代", "概率", "统计", "数理"],
        "物理类": ["物理", "力学"],
        "英语类": ["英语", "外语", "写作"],
        "体育类": ["体育", "军训"],
        "思政类": ["思政", "马克思", "毛泽东", "思想道德", "形势"],
        "计算机类": ["计算机", "程序", "编程", "数据结构", "算法"],
        "专业课": ["电子", "电路", "信号", "通信", "嵌入式"],
    }

    dist = defaultdict(float)
    other = 0.0
    for _, row in df.iterrows():
        name = str(row["课程名"])
        matched = False
        for category, keywords in category_keywords.items():
            if any(kw in name for kw in keywords):
                dist[category] += row["学分"]
                matched = True
                break
        if not matched:
            other += row["学分"]

    if other > 0:
        dist["其他"] = other
    return dict(dist)


def overall_stats(df, rules=None):
    """计算总体统计数据。

    参数 rules: 绩点规则(RuleSet 或规则列表),传 None 用内置默认规则。
    返回一个字典,包含总课程数、总学分、总GPA、总加权平均分等。
    """
    return {
        "总课程数": len(df),
        "总学分": df["学分"].sum(),
        "加权平均分": round(calc_weighted_avg(df), 2),
        "GPA": round(calc_gpa(df, rules), 3),
        "最高分": df["成绩"].max(),
        "最低分": df["成绩"].min(),
        "全部课程平均分": round(df["成绩"].mean(), 2),
    }
