"""
report.py —— 图表生成模块

用 matplotlib 生成分析报告图表:
  1. 各学期 GPA 趋势折线图
  2. 各学期加权平均分趋势图
  3. 学分分布饼图
  4. 雷达图(多维度能力展示)
"""

import os
from gpa import score_to_gpa

# 设置中文字体(Windows 系统默认有 SimHei 黑体)
# 如果你的电脑上没有黑体,图表中文会显示为方块,改用 "Microsoft YaHei" 试试
_FONT = "SimHei"


def _setup_font():
    """配置 matplotlib 的中文字体,防止图表中文显示为方块。"""
    import matplotlib
    matplotlib.rcParams["font.sans-serif"] = [_FONT, "Microsoft YaHei", "WenQuanYi Micro Hei"]
    matplotlib.rcParams["axes.unicode_minus"] = False  # 负号显示


def generate_trend_chart(semesters, output_dir="output"):
    """生成各学期 GPA 和加权平均分的趋势折线图。

    参数:
        semesters: analyzer.analyze_by_semester() 的返回值
        output_dir: 图片保存目录
    """
    _setup_font()
    import matplotlib.pyplot as plt

    os.makedirs(output_dir, exist_ok=True)

    names = [s["学期"] for s in semesters]
    gpas = [s["GPA"] for s in semesters]
    avgs = [s["加权平均分"] for s in semesters]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # 左图: GPA 趋势
    ax1.plot(names, gpas, "o-", color="#4A90D9", linewidth=2, markersize=8)
    ax1.set_title("各学期 GPA 趋势", fontsize=14)
    ax1.set_xlabel("学期")
    ax1.set_ylabel("GPA")
    ax1.set_ylim(0, 4.5)
    ax1.axhline(y=4.0, color="green", linestyle="--", alpha=0.5, label="满分 4.0")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 在每个数据点旁边标注数值
    for i, g in enumerate(gpas):
        ax1.annotate(f"{g:.2f}", (names[i], g), textcoords="offset points",
                     xytext=(0, 10), ha="center", fontsize=10)

    # 右图: 加权平均分趋势
    ax2.plot(names, avgs, "s-", color="#E8636F", linewidth=2, markersize=8, label="加权平均分")
    ax2.set_title("各学期加权平均分趋势", fontsize=14)
    ax2.set_xlabel("学期")
    ax2.set_ylabel("分数")
    ax2.set_ylim(0, 100)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    for i, a in enumerate(avgs):
        ax2.annotate(f"{a:.1f}", (names[i], a), textcoords="offset points",
                     xytext=(0, 10), ha="center", fontsize=10)

    plt.tight_layout()
    path = os.path.join(output_dir, "趋势分析.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def generate_pie_chart(credit_dist, output_dir="output"):
    """生成学分分布饼图。

    参数:
        credit_dist: analyzer.credit_distribution() 的返回值
        output_dir: 图片保存目录
    """
    _setup_font()
    import matplotlib.pyplot as plt

    os.makedirs(output_dir, exist_ok=True)

    labels = list(credit_dist.keys())
    sizes = list(credit_dist.values())

    fig, ax = plt.subplots(figsize=(8, 8))
    colors = ["#4A90D9", "#E8636F", "#50C878", "#F5A623", "#9B59B6", "#1ABC9C", "#E74C3C", "#95A5A6"]

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.1f%%",
        colors=colors[:len(labels)], startangle=90,
        pctdistance=0.75, textprops={"fontsize": 11}
    )
    ax.set_title("学分分布", fontsize=14)

    plt.tight_layout()
    path = os.path.join(output_dir, "学分分布.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def generate_radar_chart(df, output_dir="output"):
    """生成多维度成绩雷达图(按课程类别算平均分)。

    面试时展示这个图很有说服力:一眼看出你的能力分布。
    """
    _setup_font()
    import matplotlib.pyplot as plt
    import numpy as np
    from analyzer import credit_distribution

    os.makedirs(output_dir, exist_ok=True)

    # 按类别算平均成绩
    from collections import defaultdict
    category_keywords = {
        "数学": ["数学", "高数", "线代", "概率", "统计"],
        "物理": ["物理", "力学"],
        "英语": ["英语", "外语"],
        "计算机": ["计算机", "程序", "编程", "数据结构"],
        "思政": ["思政", "马克思", "思想道德"],
        "专业课": ["电子", "电路", "信号", "通信"],
    }

    scores_by_cat = defaultdict(list)
    for _, row in df.iterrows():
        name = str(row["课程名"])
        for cat, keywords in category_keywords.items():
            if any(kw in name for kw in keywords):
                scores_by_cat[cat].append(row["成绩"])
                break

    # 只保留有数据的类别
    categories = []
    avg_scores = []
    for cat, scores in scores_by_cat.items():
        if scores:
            categories.append(cat)
            avg_scores.append(round(sum(scores) / len(scores), 1))

    if not categories:
        return None  # 数据不够,无法生成雷达图

    # 画雷达图
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    avg_scores_closed = avg_scores + [avg_scores[0]]
    angles_closed = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.plot(angles_closed, avg_scores_closed, "o-", linewidth=2, color="#4A90D9")
    ax.fill(angles_closed, avg_scores_closed, alpha=0.25, color="#4A90D9")
    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_title("各科类平均成绩", fontsize=14, pad=20)

    # 在每个点旁边标注分数
    for i, (angle, score) in enumerate(zip(angles, avg_scores)):
        ax.annotate(f"{score}", (angle, score), textcoords="offset points",
                     xytext=(8, 8), fontsize=10, color="#333")

    plt.tight_layout()
    path = os.path.join(output_dir, "成绩雷达图.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
