"""
main.py —— 程序入口

使用方法:
  python main.py                          # 使用示例数据 + 内置4.0规则
  python main.py 我的成绩单.csv            # 指定成绩单文件
  python main.py --school 标准5.0制        # 使用某个学校的绩点规则预设
  python main.py --config 我的规则.json    # 使用自定义规则配置文件
  python main.py --list-schools           # 查看所有可用的规则预设
  python main.py --show-rules             # 显示当前规则的成绩-绩点对照表
  python main.py --no-chart               # 不生成图表(纯终端查看)
"""

import argparse
import sys

from utils import read_transcript
from gpa import DEFAULT_RULESET, score_to_gpa
from analyzer import analyze_by_semester, find_weak_courses, credit_distribution, overall_stats
from report import generate_trend_chart, generate_pie_chart, generate_radar_chart

# 默认示例数据文件路径
DEFAULT_SAMPLE = "sample/成绩单示例.csv"


def parse_args():
    """解析命令行参数。argparse 是 Python 自带的命令行工具库。"""
    parser = argparse.ArgumentParser(
        prog="gpa-analyzer",
        description="📊 成绩分析与 GPA 计算器:读取成绩单,计算 GPA,生成趋势图和雷达图",
    )
    parser.add_argument(
        "file", nargs="?", default=DEFAULT_SAMPLE,
        help="成绩单文件路径(.csv / .xlsx),不填则使用内置示例数据",
    )
    parser.add_argument(
        "-s", "--school", metavar="名称",
        help="使用 configs/ 目录中的学校规则预设,如: --school 标准5.0制",
    )
    parser.add_argument(
        "-c", "--config", metavar="路径",
        help="使用自定义规则配置文件(.json),优先级高于 --school",
    )
    parser.add_argument(
        "--list-schools", action="store_true",
        help="列出所有可用的学校规则预设后退出",
    )
    parser.add_argument(
        "--show-rules", action="store_true",
        help="在终端显示当前使用的成绩-绩点对照表",
    )
    parser.add_argument(
        "--no-chart", action="store_true",
        help="不生成图表,只在终端查看分析结果",
    )
    return parser.parse_args()


def resolve_ruleset(args, console):
    """根据命令行参数决定用哪套绩点规则。

    优先级: --config > --school > 内置默认规则
    返回 RuleSet 对象。
    """
    from rules_loader import load_rule_set, find_school

    if args.config:
        ruleset = load_rule_set(args.config)
        console.print(f"⚙️  已加载自定义规则: [cyan]{ruleset.name}[/cyan] (满绩 {ruleset.scale})")
        return ruleset

    if args.school:
        ruleset = find_school(args.school)
        console.print(f"🏫 已加载学校规则: [cyan]{ruleset.name}[/cyan] (满绩 {ruleset.scale})")
        if ruleset.description:
            console.print(f"   [dim]{ruleset.description}[/dim]")
        return ruleset

    return DEFAULT_RULESET


def show_rules_table(ruleset, console):
    """打印当前规则的成绩-绩点对照表,方便核对规则是否配对。"""
    from rich.table import Table

    table = Table(title=f"当前绩点规则: {ruleset.name} (满绩 {ruleset.scale})", show_lines=False)
    table.add_column("分数区间", style="cyan")
    table.add_column("绩点", justify="center")

    rules = ruleset.rules
    for i, (lowest, gpa) in enumerate(rules):
        # 每档的上限 = 上一档的下限 - 1
        upper = rules[i - 1][0] - 1 if i > 0 else 100
        if lowest <= 0:
            span = f"< {rules[i - 1][0]:g} 分" if i > 0 else "全部"
        else:
            span = f"{lowest:g} ~ {upper:g} 分"
        table.add_row(span, f"{gpa:g}")
    console.print(table)
    console.print()


def main():
    """主函数:读取成绩 → 分析 → 终端展示 → 生成图表"""
    # 检查依赖是否安装齐全
    import importlib
    try:
        importlib.import_module("pandas")
        importlib.import_module("rich")
        importlib.import_module("matplotlib")
    except ImportError as e:
        print(f"缺少依赖库: {e}")
        print("请先执行: pip install -r requirements.txt")
        sys.exit(1)

    from rich.console import Console
    from rich.table import Table

    console = Console()
    args = parse_args()

    # ──── 列出可用学校规则后退出 ────
    if args.list_schools:
        from rules_loader import list_schools, CONFIG_DIR
        console.rule("[bold blue]🏫 可用的学校绩点规则[/bold blue]")
        console.print(f"(配置文件夹: [cyan]{CONFIG_DIR}[/cyan])\n")
        t = Table(show_header=True, show_lines=True)
        t.add_column("使用方式", style="green")
        t.add_column("规则名称")
        t.add_column("满绩", justify="center")
        t.add_column("说明")
        for s in list_schools():
            t.add_row(f"--school \"{s['文件'].replace('.json', '')}\"", s["名称"], str(s["满绩"]), s["说明"])
        console.print(t)
        console.print("[dim]没有你的学校? 复制 configs/我的学校(模板).json 修改后用 --config 加载[/dim]")
        return

    console.rule("[bold blue]📊 成绩分析与 GPA 计算器[/bold blue]")
    console.print()

    # ──── 确定绩点规则 ────
    try:
        ruleset = resolve_ruleset(args, console)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]❌ {e}[/red]")
        sys.exit(1)

    # ──── 读取成绩单 ────
    try:
        console.print(f"📄 正在读取: [cyan]{args.file}[/cyan]")
        df = read_transcript(args.file, grade_map=ruleset.grade_map)
        console.print(f"   成功读取 [green]{len(df)}[/green] 条成绩记录\n")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]❌ 读取失败: {e}[/red]")
        sys.exit(1)

    # ──── 显示规则对照表(可选) ────
    if args.show_rules:
        show_rules_table(ruleset, console)

    # ──── 总体统计 ────
    stats = overall_stats(df, ruleset)
    console.rule("[bold]📋 总体统计[/bold]")
    summary_table = Table(show_header=False, show_lines=True)
    summary_table.add_column("指标", style="bold", width=18)
    summary_table.add_column("数值", justify="center")
    summary_table.add_row("绩点规则", f"{ruleset.name}")
    summary_table.add_row("总课程数", str(stats["总课程数"]))
    summary_table.add_row("总学分", f"{stats['总学分']:.1f}")
    summary_table.add_row("加权平均分", f"[green]{stats['加权平均分']}[/green]")
    summary_table.add_row(f"GPA({ruleset.scale:g}制)", f"[green]{stats['GPA']}[/green]")
    summary_table.add_row("全部课程平均分", f"{stats['全部课程平均分']}")
    summary_table.add_row("最高分", f"{stats['最高分']}分")
    summary_table.add_row("最低分", f"[red]{stats['最低分']}分[/red]")
    console.print(summary_table)
    console.print()

    # ──── 各学期分析 ────
    semesters = analyze_by_semester(df, ruleset)
    console.rule("[bold]📈 各学期分析[/bold]")
    sem_table = Table(title="")
    sem_table.add_column("学期", style="cyan")
    sem_table.add_column("课程数", justify="center")
    sem_table.add_column("学分", justify="center")
    sem_table.add_column("加权平均分", justify="center")
    sem_table.add_column("GPA", justify="center")
    sem_table.add_column("最高分", justify="center")
    sem_table.add_column("最低分", justify="center")

    for s in semesters:
        sem_table.add_row(
            str(s["学期"]),
            str(s["课程数"]),
            f"{s['总学分']:.1f}",
            f"[green]{s['加权平均分']}[/green]",
            f"[green]{s['GPA']}[/green]",
            str(s["最高分"]),
            str(s["最低分"]),
        )
    console.print(sem_table)
    console.print()

    # ──── 全部课程明细 ────
    console.rule("[bold]📚 全部课程明细[/bold]")
    detail_table = Table(title="")
    detail_table.add_column("学期", style="cyan", width=10)
    detail_table.add_column("课程名", width=25)
    detail_table.add_column("学分", justify="center", width=6)
    detail_table.add_column("成绩", justify="center", width=6)
    detail_table.add_column("绩点", justify="center", width=6)

    for _, row in df.iterrows():
        gpa = score_to_gpa(row["成绩"], ruleset)
        color = "green" if row["成绩"] >= 80 else ("yellow" if row["成绩"] >= 60 else "red")
        detail_table.add_row(
            str(row["学期"]),
            str(row["课程名"]),
            f"{row['学分']:.0f}",
            f"[{color}]{row['成绩']:.0f}[/{color}]",
            f"{gpa:g}",
        )
    console.print(detail_table)
    console.print()

    # ──── 薄弱课程 ────
    weak = find_weak_courses(df)
    if weak:
        console.rule("[bold red]⚠️ 薄弱课程(低于70分)[/bold red]")
        weak_table = Table(title="")
        weak_table.add_column("课程名", style="red")
        weak_table.add_column("成绩", justify="center")
        weak_table.add_column("学分", justify="center")
        weak_table.add_column("学期", style="cyan")
        for w in weak:
            weak_table.add_row(
                str(w["课程名"]),
                f"[red]{w['成绩']:.0f}[/red]",
                f"{w['学分']:.0f}",
                str(w["学期"]),
            )
        console.print(weak_table)
        console.print()

    # ──── 生成图表 ────
    if not args.no_chart:
        console.rule("[bold]🎨 正在生成图表...[/bold]")
        try:
            p1 = generate_trend_chart(semesters)
            console.print(f"   ✅ 趋势分析图 → [cyan]{p1}[/cyan]")

            credit_dist = credit_distribution(df)
            if credit_dist:
                p2 = generate_pie_chart(credit_dist)
                console.print(f"   ✅ 学分分布图 → [cyan]{p2}[/cyan]")

            p3 = generate_radar_chart(df)
            if p3:
                console.print(f"   ✅ 成绩雷达图 → [cyan]{p3}[/cyan]")
            else:
                console.print("   ⚪ 成绩雷达图: 分类数据不足,已跳过")

            console.print()
            console.print("[bold green]✨ 分析完成! 图表保存在 output/ 文件夹中,打开查看即可。[/bold green]")
        except Exception as e:
            console.print(f"[yellow]图表生成失败: {e}[/yellow]")
            console.print("可能原因:缺少中文字体。不影响终端分析结果。")
    else:
        console.print("[dim](使用 --no-chart 跳过了图表生成)[/dim]")

    console.rule("[bold blue]分析结束[/bold blue]")


if __name__ == "__main__":
    main()
