"""
gpa.py —— 绩点(GPA)计算引擎

核心概念(面试时能讲清楚这个,说明你真懂了):
  GPA(平均学分绩点)= 每门课的绩点 × 该课学分,全部加起来,再除以总学分。
  这就是"加权平均"——学分高的课权重大,对 GPA 影响更大。

绩点规则:不同学校"多少分对应多少绩点"不一样,
所以规则被设计成可替换的(RuleSet 对象),支持从 JSON 配置文件加载,
详见 rules_loader.py 和 configs/ 文件夹。
"""

from dataclasses import dataclass


# 内置默认规则:分数下限 -> 对应绩点(从高到低排列,取第一个满足的)
# 例如 90 分以上(含90)是 4.0,87 分在 [87, 90) 区间是 3.7
DEFAULT_RULES = [
    (90, 4.0),
    (87, 3.7),
    (83, 3.3),
    (80, 3.0),
    (77, 2.7),
    (73, 2.3),
    (70, 2.0),
    (67, 1.7),
    (63, 1.3),
    (60, 1.0),
    (0, 0.0),
]


@dataclass
class RuleSet:
    """一套完整的绩点规则。

    属性:
        name: 规则名称,如 "标准5.0制"
        scale: 满绩点,如 4.0 或 5.0(用于展示)
        rules: [(分数下限, 绩点), ...] 从高到低排列
        description: 规则说明(可选)
        grade_map: 等级成绩到百分制的映射(可选),如 {"优秀": 95}
    """
    name: str
    scale: float
    rules: list
    description: str = ""
    grade_map: dict = None


# 程序内置的默认规则(不依赖任何配置文件,保证开箱即用)
DEFAULT_RULESET = RuleSet(
    name="内置标准4.0制",
    scale=4.0,
    rules=DEFAULT_RULES,
    description="多数高校采用的细分绩点制,90分及以上满绩4.0",
)


def _extract_rules(rules):
    """兼容两种传参:RuleSet 对象 或 规则列表。都不传则用内置默认规则。"""
    if rules is None:
        return DEFAULT_RULES
    if isinstance(rules, RuleSet):
        return rules.rules
    return rules


def score_to_gpa(score: float, rules=None) -> float:
    """把一门课的百分制成绩换算成绩点。

    参数:
        score: 百分制成绩,例如 86.5
        rules: RuleSet 对象或规则列表,不传就用内置默认规则
    返回:
        绩点,例如 3.7
    """
    rule_list = _extract_rules(rules)
    for lowest, gpa in rule_list:
        if score >= lowest:
            return gpa
    return 0.0


def calc_weighted_avg(df) -> float:
    """计算所有课程的学分加权平均分(与绩点规则无关)。

    公式: Σ(成绩 × 学分) / Σ(学分)
    """
    total = (df["成绩"] * df["学分"]).sum()
    credits = df["学分"].sum()
    return total / credits if credits else 0.0


def calc_gpa(df, rules=None) -> float:
    """计算整个成绩单的 GPA(学分加权平均绩点)。

    公式: Σ(绩点 × 学分) / Σ(学分)
    参数 rules 可以是 RuleSet 或规则列表,实现不同学校规则切换。
    """
    rule_list = _extract_rules(rules)
    gpa_points = df["成绩"].apply(lambda s: score_to_gpa(s, rule_list))
    total = (gpa_points * df["学分"]).sum()
    credits = df["学分"].sum()
    return total / credits if credits else 0.0
