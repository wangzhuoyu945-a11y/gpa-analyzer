"""
rules_loader.py —— 学校绩点规则加载器

不同学校的绩点规则不同(4.0制、5.0制、细分/断崖式……),
所以把规则从代码里抽出来,存成 configs/ 文件夹下的 JSON 配置文件。

这样做的好处(面试可以讲"配置化设计"):
  - 加一所新学校 = 加一个 JSON 文件,不用改任何代码
  - 非程序员(同学)也能看懂和修改规则
"""

import json
import os
from dataclasses import dataclass, field

from gpa import RuleSet

# 规则配置文件所在文件夹(与本文件同级)
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")


def list_schools(config_dir: str = CONFIG_DIR) -> list:
    """列出所有可用的学校规则预设。

    扫描配置文件夹里的所有 .json 文件,返回字典列表:
      [{"名称": ..., "文件": ..., "满绩": ..., "说明": ...}, ...]
    """
    schools = []
    if not os.path.isdir(config_dir):
        return schools

    for filename in sorted(os.listdir(config_dir)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(config_dir, filename)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            schools.append({
                "名称": data.get("name", os.path.splitext(filename)[0]),
                "文件": filename,
                "满绩": data.get("scale", "?"),
                "说明": data.get("description", ""),
            })
        except (json.JSONDecodeError, KeyError) as e:
            # 某个配置文件写错了,跳过它但不影响其他文件
            print(f"警告: 跳过无效配置文件 {filename} ({e})")
    return schools


def load_rule_set(path: str) -> RuleSet:
    """从 JSON 文件加载一套绩点规则。

    JSON 格式示例:
    {
        "name": "我的学校",
        "scale": 4.0,
        "description": "可选的说明文字",
        "rules": [[90, 4.0], [80, 3.0], [70, 2.0], [60, 1.0], [0, 0.0]],
        "等级成绩映射": {"优秀": 95, "良好": 85}   <- 可选
    }
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到配置文件: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # ---- 校验必填字段 ----
    if "name" not in data or "rules" not in data:
        raise ValueError(f"配置文件 {path} 缺少 name 或 rules 字段")

    raw_rules = data["rules"]
    if not raw_rules:
        raise ValueError(f"配置文件 {path} 的 rules 不能为空")

    # 转成 (分数下限, 绩点) 元组,并按分数从高到低排序
    rules = []
    for pair in raw_rules:
        if len(pair) != 2:
            raise ValueError(f"配置文件 {path} 中 {pair} 格式不对,每条规则应是 [分数下限, 绩点]")
        rules.append((float(pair[0]), float(pair[1])))
    rules.sort(key=lambda r: r[0], reverse=True)

    # 满绩点: 没写 scale 就取所有规则里的最大绩点
    scale = float(data.get("scale", max(g for _, g in rules)))

    return RuleSet(
        name=data["name"],
        scale=scale,
        rules=rules,
        description=data.get("description", ""),
        grade_map=data.get("等级成绩映射"),
    )


def find_school(name: str, config_dir: str = CONFIG_DIR) -> RuleSet:
    """按名称查找学校规则(支持模糊匹配文件名或配置里的 name 字段)。

    例如 --school 标准5.0制 会匹配 configs/标准5.0制.json
    """
    target = name.strip().lower()

    if not os.path.isdir(config_dir):
        raise FileNotFoundError(f"配置文件夹不存在: {config_dir}")

    for filename in sorted(os.listdir(config_dir)):
        if not filename.endswith(".json"):
            continue
        stem = os.path.splitext(filename)[0]  # 文件名去掉 .json
        path = os.path.join(config_dir, filename)
        try:
            with open(path, encoding="utf-8") as f:
                inner_name = str(json.load(f).get("name", ""))
        except json.JSONDecodeError:
            continue

        # 文件名或配置内的名称,任一匹配即可(忽略大小写)
        if target == stem.lower() or target == inner_name.lower():
            return load_rule_set(path)

    # 没找到,给出友好的错误提示
    available = [s["文件"] for s in list_schools(config_dir)]
    raise ValueError(
        f"没有找到学校规则: {name}\n"
        f"当前可用的规则文件: {', '.join(available) if available else '(无)'}\n"
        f"也可以用 --config 你的规则.json 加载自定义规则"
    )
