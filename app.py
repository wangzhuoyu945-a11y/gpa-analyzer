"""
app.py —— Streamlit Web 应用

启动方法: streamlit run app.py
部署方法:推到 GitHub 后在 streamlit.cloud 创建 App,选这个仓库即可

学长学姐的使用流程:
  1. 打开链接 → 看到首页
  2. 选择绩点规则(或用默认4.0制)
  3. 上传成绩单 CSV 或手动输入课程
  4. 点击"计算" → 看到 GPA 结果
  5. 输入学校给的GPA → 对比差异
  6. 点击"提交" → 数据自动保存

管理员(你)的流程:
  1. 侧边栏点"📊 管理面板"
  2. 输入密码
  3. 查看所有提交、统计、导出数据
"""

import streamlit as st
import pandas as pd
import os
import sys

# 确保项目根目录在 sys.path 中(部署时工作目录可能不同)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---- 页面基础设置 ----
st.set_page_config(
    page_title="GPA 分析器",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- 导入项目模块 ----
from gpa import score_to_gpa, calc_gpa, calc_weighted_avg, DEFAULT_RULESET
from rules_loader import list_schools, find_school
from analyzer import analyze_by_semester, credit_distribution

# ---- 侧边栏导航 ----
st.sidebar.title("📊 GPA 分析器")
page = st.sidebar.radio(
    "选择功能",
    ["🏠 计算GPA", "🤖 AI助手", "📊 管理面板"],
    horizontal=True,
)

# ---- 缓存绩点规则列表(避免每次刷新都读文件) ----
@st.cache_resource
def _get_available_schools():
    return list_schools()


# ============================================================
# 页面 1: 计算 GPA (学长学姐用的)
# ============================================================
if page == "🏠 计算GPA":

    st.title("📊 成绩分析与 GPA 计算器")
    st.markdown(
        "上传成绩单或手动输入课程，自动计算 GPA，对比学校给出的绩点是否一致。"
    )

    # ---- 基本信息 ----
    col1, col2 = st.columns([1, 2])
    with col1:
        nickname = st.text_input("你的昵称（可选，用于区分不同测试者）", placeholder="如：张三")
        schools = _get_available_schools()
        school_names = ["内置默认(标准4.0制细分)"] + [s["名称"] for s in schools]
        selected_idx = st.selectbox(
            "选择绩点规则",
            range(len(school_names)),
            format_func=lambda i: school_names[i],
        )

    with col2:
        # 根据选择展示规则说明
        if selected_idx == 0:
            st.info("📖 **内置默认 · 标准4.0制（细分）**\n\n"
                    "多数高校采用的绩点规则：\n"
                    "- 满绩 **4.0**（90分及以上）\n"
                    "- 每 **3分** 划为一档（如 90→4.0, 87→3.7, 83→3.3）\n"
                    "- 60分以下绩点为 0\n\n"
                    "**分数对照**：90→4.0 | 87→3.7 | 83→3.3 | 80→3.0 | 77→2.7 | 73→2.3 | 70→2.0 | 60→1.0")
        else:
            rs_preview = find_school(school_names[selected_idx])
            if rs_preview:
                desc = rs_preview.description or "暂无说明"
                rule_lines = []
                for threshold, point in rs_preview.rules:
                    rule_lines.append(f"{threshold}→{point:g}")
                rule_table = " | ".join(rule_lines)
                st.info(f"📖 **{rs_preview.name}**（满绩 {rs_preview.scale:g}）\n\n"
                        f"{desc}\n\n"
                        f"**分数对照**：{rule_table}")
            else:
                st.warning("未找到该规则的说明")

        st.info("💡 **使用提示**\n\n"
                "1. 选择你学校的绩点规则\n"
                "2. 上传成绩单 CSV 或手动输入\n"
                "3. 点击「计算 GPA」查看结果\n"
                "4. 在下方输入学校给你的 GPA 做对比\n"
                "5. 点击「提交反馈」保存数据")

    # 确定规则
    if selected_idx == 0:
        ruleset = DEFAULT_RULESET
    else:
        # 注意用 school_names(含"内置默认"占位项)取名称,而不是 schools 列表,
        # 否则下标会错位一位
        ruleset = find_school(school_names[selected_idx])

    # ---- 数据输入方式 ----
    input_mode = st.radio("数据输入方式", ["📤 上传成绩单 CSV", "✍️ 手动输入课程"], horizontal=True)

    df = None

    if input_mode == "📤 上传成绩单 CSV":
        uploaded = st.file_uploader(
            "选择 CSV 文件（需包含：学期、课程名、学分、成绩 列）",
            type=["csv"],
        )
        if uploaded:
            try:
                df = pd.read_csv(uploaded, encoding="utf-8-sig")
                # 标准化列名
                col_map = {}
                for col in df.columns:
                    c = str(col).strip()
                    if c in ["学期", "开课学期", "term", "学期名称"]:
                        col_map[col] = "学期"
                    elif c in ["课程名", "课程名称", "课程", "科目", "course"]:
                        col_map[col] = "课程名"
                    elif c in ["学分", "credit", "credits"]:
                        col_map[col] = "学分"
                    elif c in ["成绩", "分数", "总评成绩", "score", "grade"]:
                        col_map[col] = "成绩"
                df = df.rename(columns=col_map)
                required = ["学期", "课程名", "学分", "成绩"]
                missing = [c for c in required if c not in df.columns]
                if missing:
                    st.error(f"CSV 缺少这些列: {missing}。需要包含：学期、课程名、学分、成绩")
                    df = None
                else:
                    df["学分"] = pd.to_numeric(df["学分"], errors="coerce")
                    df["成绩"] = pd.to_numeric(df["成绩"], errors="coerce")
                    df = df.dropna(subset=["学分", "成绩"])
                    df = df[required].reset_index(drop=True)
                    st.success(f"成功读取 {len(df)} 门课程")
                    st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"读取失败: {e}")

    else:  # 手动输入
        st.markdown("#### 输入课程（每行一门课）")

        if "course_rows" not in st.session_state:
            # 默认 5 行空数据
            st.session_state["course_rows"] = pd.DataFrame({
                "学期": [""] * 5,
                "课程名": [""] * 5,
                "学分": [""] * 5,
                "成绩": [""] * 5,
            })

        edited = st.data_editor(
            st.session_state["course_rows"],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "学期": st.column_config.TextColumn("学期", help="如：大一上、2024-2025-1"),
                "课程名": st.column_config.TextColumn("课程名"),
                "学分": st.column_config.NumberColumn("学分", min_value=0, step=0.5),
                "成绩": st.column_config.NumberColumn("成绩", min_value=0, max_value=100),
            },
        )
        st.session_state["course_rows"] = edited

        # 校验
        valid = edited.dropna(subset=["课程名", "学分", "成绩"])
        valid = valid[valid["学分"].apply(lambda x: str(x).strip() != "")]
        valid = valid[valid["成绩"].apply(lambda x: str(x).strip() != "")]

        if len(valid) > 0:
            try:
                df = valid.copy()
                df["学期"] = df["学期"].fillna("未分学期").astype(str)
                df["课程名"] = df["课程名"].astype(str)
                df["学分"] = pd.to_numeric(df["学分"], errors="coerce")
                df["成绩"] = pd.to_numeric(df["成绩"], errors="coerce")
                df = df.dropna(subset=["学分", "成绩"])
                df = df.reset_index(drop=True)
            except Exception:
                df = None

        if df is None or len(df) == 0:
            st.warning("请至少填写一门完整的课程信息（课程名、学分、成绩）")

    # ---- 计算按钮 ----
    if df is not None and len(df) > 0:
        st.divider()

        if st.button("🧮 计算 GPA", type="primary", use_container_width=True):
            # 计算每门课的绩点
            df["绩点"] = df["成绩"].apply(lambda s: score_to_gpa(s, ruleset))

            calc_gpa_val = calc_gpa(df, ruleset)
            calc_avg = calc_weighted_avg(df)

            st.session_state["calc_result"] = {
                "df": df,
                "gpa": calc_gpa_val,
                "avg": calc_avg,
                "ruleset": ruleset,
            }

    # ---- 显示结果 ----
    if "calc_result" in st.session_state:
        res = st.session_state["calc_result"]
        result_df = res["df"]
        gpa_val = res["gpa"]
        avg_val = res["avg"]
        rs = res["ruleset"]

        st.success("✅ 计算完成!")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("GPA", f"{gpa_val:.3f}", f"满绩 {rs.scale:g}")
        col_b.metric("加权平均分", f"{avg_val:.2f}")
        col_c.metric("课程数", len(result_df), f"共 {result_df['学分'].sum():.0f} 学分")

        st.dataframe(
            result_df.style.format({"学分": "{:.0f}", "成绩": "{:.0f}", "绩点": "{:.1f}"}),
            use_container_width=True,
            hide_index=True,
        )

        # ---- GPA 对比 ----
        st.divider()
        st.subheader("🔄 与学校给出的 GPA 对比")

        col_l, col_r = st.columns(2)
        with col_l:
            declared_gpa = st.number_input(
                "输入学校教务系统显示的 GPA（留空则跳过对比）",
                min_value=0.0, max_value=10.0, step=0.001,
                key="declared",
                format="%f",
            )
        with col_r:
            st.markdown("对比将帮助你验证这个工具计算是否准确。")

        if declared_gpa > 0:
            diff = round(gpa_val - declared_gpa, 3)
            if abs(diff) < 0.01:
                st.balloons()
                st.success(f"🎉 **完全匹配!** 计算GPA = {gpa_val:.3f}, 学校GPA = {declared_gpa:.3f}")
            elif abs(diff) < 0.1:
                st.warning(f"⚠️ **接近但有偏差**: 计算GPA = {gpa_val:.3f}, 学校GPA = {declared_gpa:.3f}, 差值 = {diff:+.3f}\n\n可能是分档规则略有不同,请联系开发者修正。")
            else:
                st.error(f"❌ **偏差较大**: 计算GPA = {gpa_val:.3f}, 学校GPA = {declared_gpa:.3f}, 差值 = {diff:+.3f}\n\n可能是绩点规则不对,请尝试切换其他规则重新计算。")

        # ---- 提交反馈 ----
        st.divider()
        notes = st.text_area("备注（可选）", placeholder="如：我学校是XX大学、用了什么规则、有什么建议...")

        if st.button("📤 提交反馈（保存数据）", type="secondary", use_container_width=True):
            from db import save_submission
            save_submission(
                nickname=nickname,
                rule_name=rs.name,
                rule_scale=rs.scale,
                courses_df=result_df,
                calc_gpa=gpa_val,
                calc_weighted_avg=avg_val,
                declared_gpa=declared_gpa if declared_gpa > 0 else None,
                notes=notes,
            )
            st.success("✅ 数据已保存! 感谢你的测试反馈!")
            st.session_state.pop("calc_result", None)  # 清除结果,防重复提交


# ============================================================
# 页面 2: AI 助手 (聊天问答)
# ============================================================
if page == "🤖 AI助手":

    from ai_assistant import get_api_key, chat_completion, build_system_prompt, MODEL

    st.title("🤖 AI 绩点助手")
    st.markdown(
        "可以问我任何绩点相关的问题，比如：**“哪门课拖了我的GPA”**、"
        "**“大二要考多少分才能把GPA刷到3.8”**、**“什么叫加权平均分”**。"
        "如果你刚在「计算GPA」页面算过，我会自动看到你的成绩数据，回答更有针对性。"
    )

    # ---- 获取 API Key: Secrets > 环境变量 > 临时输入 ----
    api_key = get_api_key(st.secrets)

    if not api_key:
        temp_key = st.text_input(
            "临时输入 API Key（仅本次会话有效，不会保存）",
            type="password",
            placeholder="粘贴智谱 AI 的 API Key",
        )
        if temp_key.strip():
            st.session_state["temp_api_key"] = temp_key.strip()
            st.rerun()
        api_key = st.session_state.get("temp_api_key")

    if not api_key:
        st.warning(
            "⚠️ 还没有配置 AI API Key。**开发者**请按以下步骤配置：\n\n"
            "1. 打开 [open.bigmodel.cn](https://open.bigmodel.cn)，手机号免费注册\n"
            "2. 控制台右上角「API Keys」→ 创建并复制 Key\n"
            "3. Streamlit Cloud → 本应用 → Settings → Secrets，添加一行：\n"
            "   `AI_API_KEY = \"你的Key\"`，然后 Reboot\n\n"
            "使用的是智谱免费模型 glm-4-flash，**不会产生任何费用**。\n\n"
            "普通人测试也可以直接在上面输入框里临时粘贴 Key 使用。"
        )
        st.stop()

    # ---- 构建成绩数据上下文(如果刚算过 GPA) ----
    gpa_context = None
    if "calc_result" in st.session_state:
        res = st.session_state["calc_result"]
        rdf = res["df"]
        courses_text = "\n".join(
            f"{r['学期']} | {r['课程名']} | {r['学分']:g} | {r['成绩']:g} | {r['绩点']:g}"
            for _, r in rdf.iterrows()
        )
        gpa_context = {
            "rule_name": res["ruleset"].name,
            "scale": res["ruleset"].scale,
            "gpa": f"{res['gpa']:.3f}",
            "avg": f"{res['avg']:.2f}",
            "courses_text": courses_text,
        }
        st.success(f"✅ 已加载你的成绩数据（GPA {gpa_context['gpa']}，共 {len(rdf)} 门课），AI 回答将基于这些数据")
    else:
        st.info("💡 你还没有计算 GPA。先去「🏠 计算GPA」页面输入成绩再回来，AI 就能看到你的具体数据。")

    # ---- 聊天界面 ----
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    # 渲染历史对话
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("输入你的问题，例如：怎么把GPA提到3.8？")

    if user_input:
        # 追加用户消息
        st.session_state["chat_messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 调用 AI(系统提示词 + 历史对话,历史过长时只保留最近 20 条)
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                try:
                    messages = (
                        [{"role": "system", "content": build_system_prompt(gpa_context)}]
                        + st.session_state["chat_messages"][-20:]
                    )
                    reply = chat_completion(messages, api_key)
                    st.markdown(reply)
                    st.session_state["chat_messages"].append(
                        {"role": "assistant", "content": reply}
                    )
                except Exception as e:
                    st.error(f"AI 调用失败：{e}\n\n请稍后重试；如果反复出现，请检查 API Key 是否有效。")

    # 清空对话按钮
    if st.session_state["chat_messages"]:
        if st.button("🗑️ 清空对话"):
            st.session_state["chat_messages"] = []
            st.rerun()


# ============================================================
# 页面 3: 管理面板 (你用的,查看所有提交数据)
# ============================================================
if page == "📊 管理面板":

    st.title("📊 管理面板")

    # 密码验证(用 session_state 记住登录状态)
    if "admin_auth" not in st.session_state:
        pwd = st.text_input("请输入管理员密码", type="password")
        if st.button("登录"):
            from db import ADMIN_PASSWORD
            if pwd == ADMIN_PASSWORD:
                st.session_state["admin_auth"] = True
                st.rerun()
            else:
                st.error("密码错误")
        st.stop()
    else:
        st.sidebar.success("✅ 已登录")
        if st.sidebar.button("退出登录"):
            del st.session_state["admin_auth"]
            st.rerun()

    # ---- 统计概览 ----
    from db import get_stats, get_submissions_df, get_submission_courses

    stats = get_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总提交数", stats["总提交数"])
    col2.metric("含对比数", stats["含对比GPA数"])
    col3.metric("平均偏差", f"{stats['平均绝对偏差']}" if stats["平均绝对偏差"] else "暂无")
    col4.metric("完全匹配", stats["完全匹配数"])

    # ---- 提交列表 ----
    st.subheader("📋 所有提交记录")

    df_subs = get_submissions_df()
    if len(df_subs) == 0:
        st.info("暂无提交记录")
    else:
        # 展示列格式化
        display_cols = {
            "id": "ID",
            "submitted_at": "提交时间",
            "nickname": "昵称",
            "rule_name": "绩点规则",
            "calc_gpa": "计算GPA",
            "declared_gpa": "学校GPA",
            "gpa_diff": "差值",
            "total_courses": "课程数",
            "total_credits": "总学分",
            "notes": "备注",
        }
        df_display = df_subs[list(display_cols.keys())].rename(columns=display_cols)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # 查看某次提交的课程明细
        st.subheader("🔍 查看课程明细")
        selected_id = st.selectbox(
            "选择提交 ID",
            df_subs["id"].tolist(),
            format_func=lambda x: f"#{x} - {df_subs[df_subs['id']==x].iloc[0]['submitted_at']} ({df_subs[df_subs['id']==x].iloc[0]['nickname'] or '匿名'})",
        )
        courses = get_submission_courses(selected_id)
        if courses:
            pd.DataFrame(courses)[["semester", "course_name", "credits", "score", "gpa_point"]].rename(
                columns={"semester": "学期", "course_name": "课程名", "credits": "学分", "score": "成绩", "gpa_point": "绩点"}
            )
            st.dataframe(
                pd.DataFrame(courses)[["semester", "course_name", "credits", "score", "gpa_point"]].rename(
                    columns={"semester": "学期", "course_name": "课程名", "credits": "学分", "score": "成绩", "gpa_point": "绩点"}
                ),
                use_container_width=True, hide_index=True,
            )

        # 导出
        st.subheader("📥 导出数据")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            csv_sub = df_display.to_csv(index=False).encode("utf-8-sig")
            st.download_button("导出提交汇总 CSV", csv_sub, "submissions.csv", "text/csv")
        with col_e2:
            all_courses = []
            for _, sub in df_subs.iterrows():
                cs = get_submission_courses(sub["id"])
                for c in cs:
                    c["submission_id"] = sub["id"]
                    c["nickname"] = sub["nickname"]
                    all_courses.append(c)
            if all_courses:
                csv_courses = pd.DataFrame(all_courses).to_csv(index=False).encode("utf-8-sig")
                st.download_button("导出全部课程明细 CSV", csv_courses, "all_courses.csv", "text/csv")
