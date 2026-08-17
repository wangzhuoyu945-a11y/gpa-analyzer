"""
ai_assistant.py —— AI 问答助手模块

调用智谱 AI(bigmodel.cn)的 OpenAI 兼容接口,使用免费的 glm-4-flash 模型。
接口格式与 OpenAI 一致,以后想换别家 API 只需改 BASE_URL 和 MODEL。

API Key 的读取顺序:
  1. Streamlit Secrets (st.secrets["AI_API_KEY"],部署在云端时用)
  2. 环境变量 AI_API_KEY
  3. 页面临时输入(仅本次会话有效)
"""

import os
import requests

# 智谱 AI 的 OpenAI 兼容接口;glm-4-flash 是官方免费模型
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"

# 调用失败时的统一超时(秒)
TIMEOUT = 60


def get_api_key(st_secrets=None):
    """按优先级获取 API Key:Secrets > 环境变量。返回 None 表示没配置。"""
    if st_secrets is not None:
        try:
            key = st_secrets.get("AI_API_KEY")
            if key:
                return str(key).strip()
        except Exception:
            pass
    env_key = os.environ.get("AI_API_KEY")
    if env_key:
        return env_key.strip()
    return None


def chat_completion(messages, api_key, base_url=None, model=None):
    """
    调用 AI 接口,返回助手回复文本。

    messages: OpenAI 格式的对话列表
              [{"role": "system", "content": ...}, {"role": "user", "content": ...}, ...]
    失败时抛出异常,由调用方捕获并显示友好错误信息。
    """
    resp = requests.post(
        base_url or BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model or MODEL,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 1024,
        },
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        # 常见错误:Key 无效(401)、触发限流(429)
        raise RuntimeError(f"AI 接口返回错误 {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def build_system_prompt(gpa_context=None):
    """
    构建系统提示词,告诉 AI 它的身份,并注入用户的真实成绩数据。

    gpa_context: dict,来自 app.py 计算结果,包含:
        {rule_name, scale, gpa, avg, courses_text}
    没有计算结果时传 None,AI 也能回答通用绩点问题。
    """
    prompt = (
        "你是「GPA 分析器」网页工具里内置的 AI 绩点助手,服务中国大学生。"
        "你的职责:\n"
        "1. 解答绩点、加权平均分、学分相关的计算规则问题\n"
        "2. 根据用户提供的真实成绩数据,给出分析和提分建议\n"
        "3. 回答如\"我还差多少学分""要考多少分才能把GPA提到X\"这类规划问题\n\n"
        "要求:\n"
        "- 用中文回答,简洁、口语化,重点内容加粗\n"
        "- 涉及计算时列出算式过程,让用户能看懂\n"
        "- 给建议要具体(哪门课、目标多少分),不要空话\n"
        "- 如果用户的数据里没有你需要的信息,直接说明并让用户补充\n"
    )

    if gpa_context:
        prompt += (
            f"\n=== 用户当前的成绩数据(真实数据,回答须基于它) ===\n"
            f"使用的绩点规则: {gpa_context.get('rule_name', '未知')} "
            f"(满绩 {gpa_context.get('scale', '?')})\n"
            f"当前 GPA: {gpa_context.get('gpa', '?')}\n"
            f"加权平均分: {gpa_context.get('avg', '?')}\n"
            f"课程明细(学期 | 课程名 | 学分 | 成绩 | 绩点):\n"
            f"{gpa_context.get('courses_text', '无')}\n"
            "=== 数据结束 ==="
        )
    else:
        prompt += (
            "\n注意:用户还没有在工具里计算过 GPA,没有成绩数据。"
            "如果用户问的问题需要具体数据,请引导他先到「计算GPA」页面输入成绩。"
        )

    return prompt
