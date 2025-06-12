import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from collections import defaultdict
# from finance_utils import (
#     lookup_stock_basic,
#     fetch_all_data,
#     fetch_cash_flow,
#     fetch_price,
#     compute_indicators,
#     dupont,
#     calc_profitability,
#     calc_solvency,
#     calc_growth,
#     calc_operating,
#     calc_cashflow
#     #fetch_industry_metrics
# )
from finance_utils import (
    lookup_stock_basic,
    fetch_all_data,
    fetch_price,
    # compute_indicators,
    fetch_full_industry_data,
    # calc_profitability,
    # calc_solvency,
    # calc_growth,
    # calc_operating,
    # calc_cashflow,
    get_ai_analysis,
    get_ai_price_chart_analysis,
    fetch_accounting_data,
    get_ai_response
)

st.set_page_config(layout="wide")
st.title("📊 财务指标一键分析")

st.sidebar.header("参数设置")
basic_df = lookup_stock_basic()

# --- 状态管理初始化 ---
# 1. 初始化 session_state，确保变量存在
if 'selected_stocks' not in st.session_state:
    st.session_state.selected_stocks = []
if 'analysis_started' not in st.session_state:
    st.session_state.analysis_started = False

code_to_name_map = pd.Series(basic_df.name.values, index=basic_df.ts_code).to_dict()

if 'ai_accounting_reports' not in st.session_state:
    st.session_state.ai_accounting_reports = {} # 初始化为一个空字典
if 'ai_strategy_reports' not in st.session_state:
    st.session_state.ai_strategy_reports = {} # 初始化为空字典，按行业存储报告
st.sidebar.markdown("#### 搜索并添加公司")
# 2. 搜索与添加逻辑
name_filter = st.sidebar.text_input("输入公司名称或代码进行搜索：")

if name_filter:
    # 搜索匹配的公司
    name_mask = basic_df["name"].str.contains(name_filter, na=False, case=False)
    code_mask = basic_df["ts_code"].str.contains(name_filter, na=False, case=False)
    combined_mask = name_mask | code_mask
    search_results_df = basic_df[combined_mask]
    
    # 创建给 selectbox 用的选项
    search_options = {f"{r['name']} ({r.ts_code})": r.ts_code for _, r in search_results_df.iterrows()}
    
    if not search_options:
        st.sidebar.info("没有找到匹配的公司。")
    else:
        # 使用 selectbox 展示搜索结果
        stock_to_add_display = st.sidebar.selectbox(
            "选择一家公司添加到下方列表：",
            options=list(search_options.keys())
        )
        
        # “添加”按钮
        if st.sidebar.button("➕ 添加选中公司"):
            stock_to_add_code = search_options[stock_to_add_display]
            if stock_to_add_code not in st.session_state.selected_stocks:
                st.session_state.selected_stocks.append(stock_to_add_code)
                # 触发一次重跑来更新UI
                st.rerun()
            else:
                st.sidebar.warning(f"{stock_to_add_display} 已在列表中。")

# 3. 展示与移除逻辑
st.sidebar.markdown("---")
st.sidebar.markdown("#### 已选公司列表")

if not st.session_state.selected_stocks:
    st.sidebar.info("请从上方搜索并添加公司进行分析。")
else:
    # 遍历已选列表，展示并提供移除按钮
    for ts_code in st.session_state.selected_stocks:
        col1, col2 = st.sidebar.columns([4, 1])
        stock_name = code_to_name_map.get(ts_code, ts_code)
        col1.markdown(f"- {stock_name}")
        # 为每个移除按钮设置一个唯一的 key
        if col2.button("移除", key=f"remove_{ts_code}"):
            st.session_state.selected_stocks.remove(ts_code)
            # 触发一次重跑来更新UI
            st.rerun()

# 添加一个“清空”按钮，方便一次性移除所有
if st.session_state.selected_stocks:
    if st.sidebar.button("清空所有选择", use_container_width=True):
        st.session_state.selected_stocks = []
        st.session_state.analysis_started = False
        st.rerun()


# 将最终的用户选择赋值给 stocks 变量，供后续代码使用
stocks_to_analyze = st.session_state.selected_stocks


current_year = pd.Timestamp.now().year
year_range   = st.sidebar.slider("最新期年份范围", 2000, current_year, (current_year-1,current_year))
hist_year_range   = st.sidebar.slider("历史年份范围", 2000, current_year, (year_range[0]-5,year_range[1]))

if 'ai_price_report' not in st.session_state:
    st.session_state.ai_price_report = ""
if 'ai_profit_report' not in st.session_state:
    st.session_state.ai_profit_report = ""
if 'ai_solvency_report' not in st.session_state:
    st.session_state.ai_solvency_report = ""
if 'ai_growth_report' not in st.session_state:
    st.session_state.ai_growth_report = ""
if 'ai_operating_report' not in st.session_state:
    st.session_state.ai_operating_report = ""
if 'ai_cashflow_report' not in st.session_state:
    st.session_state.ai_cashflow_report = ""


# app.py

def generate_ai_summary_for_capability(
    capability_name, metrics_dict, company_code, company_name, industry_name, 
    combined_historical_df, full_industry_df, final_period_used
):
    """为单个能力板块生成AI分析报告"""
    
    st.info(f"正在生成关于 **{company_name}** 的 **{capability_name}** 智能分析报告...")

    # 1. 准备数据摘要
    summary_lines = [
        f"公司名称: {company_name} ({company_code})",
        f"所属行业: {industry_name}",
        f"分析报告期: {final_period_used}",
        "\n核心指标表现:"
    ]

    latest_data = combined_historical_df[combined_historical_df['ts_code'] == company_code].iloc[-1]

    for metric_code, metric_label in metrics_dict.items():
        if metric_code in full_industry_df.columns:
            # 即时计算排名和百分位
            sorted_df = full_industry_df.sort_values(by=metric_code, ascending=False).reset_index(drop=True)
            rank_info = sorted_df[sorted_df['ts_code'] == company_code]
            rank = rank_info.index[0] + 1 if not rank_info.empty else 'N/A'
            
            company_value = latest_data.get(metric_code, 'N/A')
            industry_avg = full_industry_df[metric_code].mean()

            line = f"- {metric_label}: {company_value:.2f} (行业均值: {industry_avg:.2f}, 行业排名: {rank}/{len(full_industry_df)})"
            summary_lines.append(line)

    data_summary = "\n".join(summary_lines)

    # 2. 构建针对性的提示词
    prompt = f"""
    请你扮演一位专业的金融分析师。我将为你提供上市公司“{company_name}”在“{capability_name}”方面的核心数据，请你基于这些数据，给出一份简明扼要、有洞察力的分析报告。

    你的分析需要包含以下几个方面，并以清晰的要点形式呈现：
    1.  **总体评价**: 对该公司在“{capability_name}”方面的整体表现给出一个定性评价（例如：优秀、良好、一般、有待改善等）。
    2.  **亮点分析**: 指出其在该方面最突出的1个优点，并结合具体数据说明。
    3.  **风险提示**: 指出其在该方面最值得关注的1个潜在风险或弱点，并结合具体数据说明。

    以下是需要你分析的原始数据：
    ---
    {data_summary}
    ---
    请严格基于以上数据进行分析，不要编造数据之外的信息。
    """

    # 3. 调用AI并显示结果
    # 注意：这里的 get_ai_analysis 是我们定义在 finance_utils.py 中的函数
    ai_report = get_ai_analysis(company_name, prompt)
    st.markdown(ai_report)

# def display_metric_comparison(metric_name, metric_label, selected_codes_data, industry_df, ascending=False, format_str='{:.2f}'):
#     """
#     最终版：包含所有功能和美化效果，包括分栏、仪表盘和彩色柱状图。
#     """
#     st.markdown(f"#### 指标: {metric_label}")

#     # 1. 准备数据
#     if metric_name not in industry_df.columns:
#         st.warning(f"行业数据中缺少指标: '{metric_label}'，无法进行对标分析。")
#         return
#     industry_df[metric_name] = pd.to_numeric(industry_df[metric_name], errors='coerce').fillna(0)
#     industry_df = industry_df.sort_values(by=metric_name, ascending=ascending).reset_index(drop=True)
#     industry_df['rank'] = industry_df.index + 1
#     total_companies = len(industry_df)

#     # 2. 左右布局
#     col1, col2 = st.columns([1, 1])

#     with col1: # 左侧：排名文字 + 仪表盘
#         st.markdown("**公司在行业中的位置**")
#         for _, row in selected_codes_data.iterrows():
#             if metric_name not in row or pd.isna(row[metric_name]):
#                 st.write(f"**{row['name']}**: 缺少 '{metric_label}' 数据。")
#                 continue
#             company_name = row['name']
#             company_value = row[metric_name]
#             company_rank_info = industry_df[industry_df['ts_code'] == row['ts_code']]
#             if company_rank_info.empty: continue
#             rank = company_rank_info['rank'].iloc[0]
#             percentile = (1 - (rank - 1) / total_companies) * 100
            
#             with st.expander(f"**{company_name}** (当前值: {format_str.format(company_value)})", expanded=True):
#                 st.info(f"在 {total_companies} 家公司中排名第 **{rank}**，优于 **{percentile:.1f}%** 的同业公司。")
#                 source = pd.DataFrame({"value": [percentile]})
#                 background = alt.Chart(source).mark_arc(innerRadius=50, outerRadius=70).encode(
#                     theta=alt.value(1.5708), theta2=alt.value(-1.5708), color=alt.value('#e6e6e6')
#                 )
#                 gauge_color_condition = {'condition': [{'test': 'datum.value > 80', 'value': 'green'}, {'test': 'datum.value > 50', 'value': 'orange'}], 'value': 'red' }
#                 angle_range = [-1.5708, 1.5708] 
#                 foreground = alt.Chart(source).mark_arc(innerRadius=50, outerRadius=70).encode(
#                     theta=alt.Theta("value:Q", scale=alt.Scale(domain=[0, 100], range=angle_range), title=None),
#                     theta2=alt.value(angle_range[0]), color=gauge_color_condition
#                 )
#                 gauge_chart = (background + foreground).properties(
#                     width=250, height=180, title=alt.TitleParams(f"{company_name} 行业百分位", anchor='middle', orient='bottom', dy=10)
#                 )
#                 st.altair_chart(gauge_chart, use_container_width=True)

    # with col2: # 右侧：带颜色和数值的龙头对比图
    #     st.markdown("**与行业第一的对比**")
    #     top_2 = industry_df.head(2)
    #     comparison_df = pd.concat([top_2, selected_codes_data]).drop_duplicates(subset=['ts_code']).reset_index(drop=True)
    #     comparison_df = comparison_df.dropna(subset=[metric_name])
    #     if comparison_df.empty:
    #         st.warning("无足够数据进行龙头对比。")
    #         return
            
    #     selected_codes_list = selected_codes_data['ts_code'].tolist()
    #     comparison_df['category'] = comparison_df['ts_code'].apply(
    #         lambda x: '您选择的公司' if x in selected_codes_list else '行业龙头'
    #     )
        
    #     bars = alt.Chart(comparison_df).mark_bar().encode(
    #         # --- 核心修改：增加 labelPadding 来调整标签距离 ---
    #         x=alt.X('name:N', sort=None, title="公司", axis=alt.Axis(labelAngle=-45, labelPadding=5)),
    #         y=alt.Y(f'{metric_name}:Q', title=metric_label),
    #         color=alt.Color('category:N', title='类别', scale=alt.Scale(domain=['您选择的公司', '行业龙头'], range=['steelblue', 'lightgray']))
    #     )
    #     text = bars.mark_text(align='center', baseline='bottom', dy=-5).encode(
    #         text=alt.Text(f'{metric_name}:Q', format=format_str)
    #     )
    #     bar_chart = (bars + text).properties(title="与行业第一对比", width=400, height=300)
    #     st.altair_chart(bar_chart)
# app.py
# app.py (最终修复版)

def display_metric_comparison(metric_name, metric_label, selected_codes_data, industry_df, ascending=False, format_str='{:.2f}'):
    """
    一个完整的函数，用于显示单个指标的行业对标，包含排名文字、仪表盘和龙头对比图。
    """
    st.markdown(f"#### 指标: {metric_label}")

    # 1. 准备数据 (不变)
    if metric_name not in industry_df.columns:
        st.warning(f"行业数据中缺少指标: '{metric_label}'，无法进行对标分析。")
        return
    industry_df[metric_name] = pd.to_numeric(industry_df[metric_name], errors='coerce').fillna(0)
    industry_df = industry_df.sort_values(by=metric_name, ascending=ascending).reset_index(drop=True)
    industry_df['rank'] = industry_df.index + 1
    total_companies = len(industry_df)

    # 2. 左右布局
    col1, col2 = st.columns([1, 1])

    with col1: # 左侧：排名文字 + 仪表盘
        st.markdown("**您的公司在行业中的位置**")
        
        # --- 核心修复：在循环前，对传入的数据进行去重 ---
        unique_selected_data = selected_codes_data.drop_duplicates(subset=['ts_code'])
        
        # 现在我们遍历这个干净、唯一的数据集
        for _, row in unique_selected_data.iterrows():
            if metric_name not in row or pd.isna(row[metric_name]):
                st.write(f"**{row['name']}**: 缺少 '{metric_label}' 数据。")
                continue

            company_name = row['name']
            company_value = row[metric_name]
            company_rank_info = industry_df[industry_df['ts_code'] == row['ts_code']]
            if company_rank_info.empty: continue
            
            rank = company_rank_info['rank'].iloc[0]
            percentile = (1 - (rank - 1) / total_companies) * 100
            
            with st.expander(f"**{company_name}** (当前值: {format_str.format(company_value)})", expanded=True):
                st.info(f"在 {total_companies} 家公司中排名第 **{rank}**，优于 **{percentile:.1f}%** 的同业公司。")
                # (仪表盘图表代码不变)
                source = pd.DataFrame({"value": [percentile]})
                background = alt.Chart(source).mark_arc(innerRadius=50, outerRadius=70).encode(
                    theta=alt.value(1.5708), theta2=alt.value(-1.5708), color=alt.value('#e6e6e6')
                )
                gauge_color_condition = {'condition': [{'test': 'datum.value > 80', 'value': 'green'}, {'test': 'datum.value > 50', 'value': 'orange'}], 'value': 'red' }
                angle_range = [-1.5708, 1.5708] 
                foreground = alt.Chart(source).mark_arc(innerRadius=50, outerRadius=70).encode(
                    theta=alt.Theta("value:Q", scale=alt.Scale(domain=[0, 100], range=angle_range), title=None),
                    theta2=alt.value(angle_range[0]), color=gauge_color_condition
                )
                gauge_chart = (background + foreground).properties(
                    width=250, height=180, title=alt.TitleParams(f"{company_name} 行业百分位", anchor='middle', orient='bottom', dy=10)
                )
                st.altair_chart(gauge_chart, use_container_width=True)

    with col2: # 右侧：带颜色和数值的龙头对比图
        # (这部分代码本身就是正确的，因为它有自己的去重逻辑，无需修改)
        st.markdown("**与行业龙头的对比**")
        top_2 = industry_df.head(2)
        comparison_df = pd.concat([top_2, selected_codes_data]).drop_duplicates(subset=['ts_code']).reset_index(drop=True)
        comparison_df = comparison_df.dropna(subset=[metric_name])
        if comparison_df.empty:
            st.warning("无足够数据进行龙头对比。")
            return
            
        selected_codes_list = selected_codes_data['ts_code'].tolist()
        comparison_df['category'] = comparison_df['ts_code'].apply(
            lambda x: '您选择的公司' if x in selected_codes_list else '行业龙头'
        )
        
        bars = alt.Chart(comparison_df).mark_bar().encode(
            # --- 核心修改：增加 labelPadding 来调整标签距离 ---
            x=alt.X('name:N', sort=None, title="公司", axis=alt.Axis(labelAngle=-45, labelPadding=5)),
            y=alt.Y(f'{metric_name}:Q', title=metric_label),
            color=alt.Color('category:N', title='类别', scale=alt.Scale(domain=['您选择的公司', '行业龙头'], range=['steelblue', 'lightgray']))
        )
        text = bars.mark_text(align='center', baseline='bottom', dy=-5).encode(
            text=alt.Text(f'{metric_name}:Q', format=format_str)
        )
        bar_chart = (bars + text).properties(title="与行业第一对比", width=400, height=300)
        st.altair_chart(bar_chart)

if st.sidebar.button("🚀 开始分析", use_container_width=True):
    if stocks_to_analyze:
        st.session_state.analysis_started = True # <-- 核心修改：设置状态为True
        st.rerun() # 立即重跑以应用新状态
    else:
        st.sidebar.warning("请先选择至少一家公司。")

if st.session_state.analysis_started and stocks_to_analyze:
    # --- 第一部分：所有选中公司的概览 (股价与最新指标) ---
    st.header("股价概览：")
    col1, col2 = st.columns([1, 3])

    # with col1:
    #     st.markdown("**关键指标最新值**")
    #     latest_indicators_list = []
    #     # 使用 industry_year_end 来获取最新一期的数据进行对比
    #     industry_year_end = year_range[1]
    #     for code in stocks_to_analyze:
    #         df_latest = fetch_all_data(code, industry_year_end, industry_year_end)
    #         if not df_latest.empty:
    #             latest_series = df_latest.iloc[-1]
    #             indicators = pd.Series({
    #                 "ROE (%)": latest_series.get("roe"), "净利率 (%)": latest_series.get("netprofit_margin"),
    #                 "资产负债率 (%)": latest_series.get("debt_to_assets"), "营收同比 (%)": latest_series.get("or_yoy")
    #             }, name=code_to_name_map.get(code, code))
    #             latest_indicators_list.append(indicators)
    #     if latest_indicators_list:
    #         df_latest_compare = pd.concat(latest_indicators_list, axis=1)
    #         st.dataframe(df_latest_compare.style.format("{:.2f}"))
            
    # with col2:
    # st.markdown("**股价历史走势**")
    price_list = []
    # 使用 hist_year_range 来决定股价图的时间跨度
    for code in stocks_to_analyze:
        pf = fetch_price(code, hist_year_range[0], hist_year_range[1])
        pf["name"] = code_to_name_map.get(code, code)
        price_list.append(pf)
    if price_list:
        df_price = pd.concat(price_list, ignore_index=True)
        price_chart = alt.Chart(df_price.dropna()).mark_line().encode(
            x=alt.X("trade_date:T", title="交易日"), y=alt.Y("close:Q", title="收盘价", scale=alt.Scale(zero=False)),
            color=alt.Color("name:N", title="公司"), tooltip=["name", "trade_date", "close"]
        ).interactive()
        st.altair_chart(price_chart, use_container_width=True)
    if not df_price.empty:
        st.markdown("---") # 添加一条漂亮的分割线
        
        if st.button("生成股价走势AI分析", key="ai_price_chart_btn_full_width"):
            st.info("正在基于上图数据进行分析...")
            
            # (这部分AI调用逻辑与上一版完全相同)
            df_price['trade_date'] = pd.to_datetime(df_price['trade_date'])
            df_price_resampled = (df_price.set_index('trade_date')
                                  .groupby('name')
                                  .resample('M')
                                  .last()
                                  .drop(columns='name')
                                  .reset_index())
            df_price_resampled['month'] = df_price_resampled['trade_date'].dt.to_period('M')

            summary_lines = []
            for name, group in df_price_resampled.groupby('name'):
                summary_lines.append(f"\n公司: {name}")
                price_points = [f"{row.month}: {row.close:.2f}" for _, row in group.iterrows()]
                summary_lines.append("月度收盘价序列: " + ", ".join(price_points))
            
            chart_data_summary = "\n".join(summary_lines)
            st.session_state.ai_price_report = get_ai_price_chart_analysis(chart_data_summary)
        if st.session_state.ai_price_report:
            st.markdown("#### 📈 AI趋势解读")
            st.info(st.session_state.ai_price_report)

    # --- 第二部分：按行业进行深度对标分析 ---
    st.markdown("---")
    st.header("行业深度分析")
    
    # 1. 按行业对选择的公司进行分组
    grouped_stocks = defaultdict(list)
    for code in stocks_to_analyze:
        industry = basic_df.loc[basic_df.ts_code == code, 'industry'].iloc[0]
        grouped_stocks[industry].append(code)

    for industry, codes_in_industry in grouped_stocks.items():
        # st.subheader(f"分析对象: {industry} 行业")
        st.subheader(f"分析对象: {industry} 行业 - {', '.join([code_to_name_map.get(c, c) for c in codes_in_industry])}")

        harvard_tabs = st.tabs(["① 战略分析", "② 会计分析", "③ 财务分析", "④ 前景分析"])
        


        # with harvard_tabs[0]:
        #     st.info("AI将利用其知识库，结合公司和行业背景，使用PEST、波特五力、SWOT等经典模型为您生成战略分析报告。")
        #     company_name_for_prompt = code_to_name_map.get(codes_in_industry[0], codes_in_industry[0])

        #     if st.button("生成AI战略分析报告", key=f"ai_strategy_{industry}"):
        #     # 这个分析是针对整个行业的，所以我们只取第一个公司名作为代表
        #         prompt = f"""
        #         请你扮演一位顶级的战略顾问（如麦肯锡、波士顿咨询）。我将为你提供一家公司及其所属行业，你的任务是为“{company_name_for_prompt}”（所属行业：{industry}）生成一份全面的外部战略环境和内部竞争优势分析报告。

        #         请严格按照以下经典框架来构建你的报告，并为每个部分提供2-3个最关键的要点：
        #         1.  **PEST分析**: 分析影响该行业的宏观政治(Political)、经济(Economic)、社会(Social)和技术(Technological)因素。
        #         2.  **波特五力模型**: 分析该行业的五种竞争力，包括：供应商的议价能力、购买者的议价能力、新进入者的威胁、替代品的威胁以及现有竞争者之间的竞争。
        #         3.  **SWOT分析**: 结合以上分析，总结该公司（或该行业龙头企业）的优势(Strengths)、劣势(Weaknesses)、机会(Opportunities)和威胁(Threats)。

        #         请确保你的分析是结构化、有逻辑的，并直接输出报告。
        #         """
        #         with st.spinner("AI正在进行宏观和行业战略分析..."):
        #             ai_report = get_ai_response(prompt)
        #             st.markdown(ai_report)
        with harvard_tabs[0]:
            st.info("AI将利用其知识库，对您选择的所有公司进行独立的战略分析（PEST, 波特五力, SWOT），并在此基础上生成一份横向对比报告。")
            
            # 准备要分析的公司名称列表
            company_names_list = [code_to_name_map.get(c, c) for c in codes_in_industry]
            company_names_str = "、".join(company_names_list)

            # 只需一个按钮，触发对所有选中公司的全面分析
            if st.button(f"生成对【{company_names_str}】的AI战略对比分析报告", key=f"ai_strategy_compare_{industry}"):
                
                # 构建一个更强大的、要求进行独立分析+对比分析的Prompt
                prompt = f"""
                请你扮演一位顶级的战略顾问（如麦肯锡、波士顿咨询）。我将为你提供【{industry}】行业中的几家公司，你的任务是为它们生成一份全面的战略对比分析报告。

                请严格按照以下**两个部分**来构建你的报告：

                **第一部分：各公司独立深度分析**
                请对以下每一家公司，都独立进行完整的分析。使用清晰的三级标题（###）来分隔每家公司。在每家公司的分析中，都应包含：
                1.  **PEST分析**: 影响该行业的宏观政治(Political)、经济(Economic)、社会(Social)和技术(Technological)因素。
                2.  **波特五力模型**: 该行业的五种竞争力分析。
                3.  **SWOT分析**: 总结该公司自身的优势(Strengths)、劣势(Weaknesses)、机会(Opportunities)和威胁(Threats)。

                **第二部分：横向对比与战略总结**
                在完成所有公司的独立分析后，请撰写一个总结性的对比部分。使用清晰的二级标题（##）来标识。在这个部分，请回答以下核心问题：
                1.  **战略定位差异**: 这几家公司的核心战略定位有何不同？（例如：一家聚焦高端市场，另一家主打性价比？）
                2.  **竞争优势对比**: 谁拥有更强的竞争护城河？它们的优势分别体现在哪里（品牌、成本、技术、渠道）？
                3.  **前景展望**: 结合宏观（PEST）和行业（五力）环境，哪家公司处于更有利的竞争地位，未来发展潜力更大？

                需要分析的公司列表如下：
                - {company_names_str}

                请确保你的报告结构清晰、逻辑严谨，直接输出最终的分析报告。
                """
                
                with st.spinner("AI正在进行多公司战略对比分析，这可能需要一些时间..."):
                    ai_report = get_ai_response(prompt)
                    # 将生成的完整报告存入session state
                    st.session_state.ai_strategy_reports[industry] = ai_report
                    st.rerun()

            # 在每次页面加载时，都检查并显示已存储的报告
            if industry in st.session_state.ai_strategy_reports:
                st.markdown(st.session_state.ai_strategy_reports[industry])
        # --- Tab 2: 会计分析 ---

        with harvard_tabs[1]:
            st.info("AI将扮演“资深审计师”，从商业模式出发，评估公司会计政策的稳健性与潜在风险。")
            
            for code in codes_in_industry:
                company_name = code_to_name_map.get(code, code)
                with st.expander(f"点击生成对 **{company_name}** 的AI会计质量分析报告"):
                    
                    if st.button("开始会计分析", key=f"ai_accounting_{code}"):
                        with st.spinner(f"正在为 {company_name} 获取并分析会计数据..."):
                            accounting_df = fetch_accounting_data(code, hist_year_range[0], hist_year_range[1])
                            
                            if accounting_df.empty:
                                st.session_state.ai_accounting_reports[code] = "错误：未能获取到足够的会计数据进行分析。"
                                st.rerun()

                            accounting_df['quarter'] = pd.to_datetime(accounting_df['end_date']).dt.to_period('Q')
                            summary_lines = [f"公司: {company_name} ({code})", "\n三大报表核心数据 (近8个季度，单位：元):"]
                            
                            metrics_to_check = {
                                'n_income': '净利润',
                                'n_cashflow_act': '经营活动现金流净额',
                                'accounts_receiv': '应收账款',
                                'inventories': '存货',
                                'revenue': '营业收入' # 新增营收，为AI提供更直接的对比基准
                            }

                            for metric, label in metrics_to_check.items():
                                if metric in accounting_df.columns and not accounting_df[metric].isnull().all():
                                    series_str = ", ".join([f"{row.quarter}:{row[metric]:,.0f}" for _, row in accounting_df[['quarter', metric]].tail(8).iterrows() if pd.notna(row[metric])])
                                    summary_lines.append(f"- {label}: {series_str}")
                                else:
                                    summary_lines.append(f"- {label}: (数据缺失)")

                            full_summary = "\n".join(summary_lines)

                            # --- 核心升级：采用你的例子启发的新Prompt ---
                            prompt = f"""
                            你是一位经验丰富的四大会计师事务所资深审计合伙人，擅长通过财务数据洞察企业真实的经营状况和会计质量。你的任务是为“{company_name}”撰写一份专业的会计质量评估报告。

                            请严格按照以下三步进行分析，就像在准备审计委员会的汇报材料一样：
                            1.  **商业模式与关键会计估计的识别**: 
                                -   根据“营业收入”、“应收账款”和“存货”等数据的相对关系和变化趋势，推断该公司的核心商业模式是什么？(例如：是重资产的制造业，还是轻资产的服务业？是快速周转的零售业，还是项目周期长的工程业？)
                                -   对于这种商业模式，其最重要的会计估计是什么？(例如，对于游戏公司是虚拟道具收入的确认周期；对于制造业是存货跌价准备的计提；对于软件公司是收入确认的时点)。

                            2.  **会计政策稳健性与风险评估**:
                                -   **收入确认质量**: 对比“净利润”与“经营活动现金流”。是否存在“增收不增利”或“有利润没现金”的情况？这是否暗示了过于激进的收入确认政策？
                                -   **资产质量风险**: “应收账款”和“存货”的增长速度是否显著超过了“营业收入”的增速？这是否可能预示着回款困难或产品积压的风险？
                                -   结合以上分析，你认为该公司的会计政策是偏向“稳健保守”还是“激进冒险”？请说明理由。

                            3.  **综合结论**:
                                -   综合上述分析，对该公司的整体会计质量给出一个明确的结论。其财务报表是否能够“真实、准确地反映企业的经营现实”？财务数据是否具有可靠的可比性？

                            以下是你需要分析的核心数据：
                            ---
                            {full_summary}
                            ---
                            请直接输出你的专业评估报告，语言要严谨、客观，直指核心。
                            """
                            
                            ai_report = get_ai_analysis(company_name, prompt)
                            st.session_state.ai_accounting_reports[code] = ai_report
                            st.rerun() 

                    if code in st.session_state.ai_accounting_reports:
                        st.markdown(st.session_state.ai_accounting_reports[code])
        with harvard_tabs[2]:

            # --- 核心修正：使用 year_range[1] 作为行业对标的起始年份 ---
            st.info(f"正在基于年份 `{year_range[1]}` 回溯查找最新的有效行业数据报告期...")
            end_year_for_industry = year_range[1]
            
            full_industry_df = pd.DataFrame()
            final_period_used = None
            for year in range(end_year_for_industry, end_year_for_industry - 5, -1):
                for month_day in ["1231", "0930", "0630", "0331"]:
                    period_to_try = f"{year}{month_day}"
                    if pd.to_datetime(period_to_try) > pd.Timestamp.now(): continue
                    full_industry_df = fetch_full_industry_data(industry, period_to_try)
                    if not full_industry_df.empty:
                        final_period_used = period_to_try
                        break
                if final_period_used: break
            
            if final_period_used:
                st.success(f"成功！已自动采用最新的有效报告期 '{final_period_used}' 进行行业对标分析。")
            else:
                st.error("错误：在最近5年的所有报告期内均未找到有效的行业数据。")

            historical_data_list = []
            line_styles = ['solid', 'dashed', 'dotted', 'dotdash']
            
            for i, code in enumerate(codes_in_industry):
                # 使用正确的历史年份范围滑块来获取数据
                df = fetch_all_data(code, hist_year_range[0], hist_year_range[1])
                
                if not df.empty:
                    df['name'] = code_to_name_map.get(code, code)
                    # --- 关键代码：在这里为每家公司的数据添加 'style' 列 ---
                    df['style'] = line_styles[i % len(line_styles)] 
                    historical_data_list.append(df)
            
            # 如果一家公司的历史数据都没取到，就跳过这个行业的分析
            if not historical_data_list: 
                st.warning(f"未能获取到 {industry} 行业所选公司的任何历史数据。")
                continue
                
            combined_historical_df = pd.concat(historical_data_list, ignore_index=True)



            selected_data = pd.DataFrame()
            if not full_industry_df.empty:
                selected_data = full_industry_df[full_industry_df['ts_code'].isin(codes_in_industry)]
            # --- 初始化 selected_data ---
            selected_data = pd.DataFrame()
            if not full_industry_df.empty:
                selected_data = full_industry_df[full_industry_df['ts_code'].isin(codes_in_industry)]

            # # --- 添加一个内容更详细的调试面板 ---
            # with st.expander("👉 点击查看【终极调试面板】"):
            #     st.markdown("#### 1. `full_industry_df` 状态")
            #     st.write(f"`full_industry_df` 是否为空? `{full_industry_df.empty}`")
            #     if not full_industry_df.empty:
            #         st.write("数据类型信息 (`.info()`):")
            #         # Streamlit无法直接渲染.info()，我们用st.text来模拟
            #         import io
            #         buffer = io.StringIO()
            #         full_industry_df.info(buf=buffer)
            #         st.text(buffer.getvalue())
            #         st.dataframe(full_industry_df)

            #     st.markdown("---")
            #     st.markdown("#### 2. `selected_data` 状态")
            #     st.write(f"`selected_data` 是否为空? `{selected_data.empty}`. 这是决定行业对比是否显示的关键！")
            #     st.write(f"用于筛选的代码列表 `codes_in_industry`: `{codes_in_industry}`")
            #     if not selected_data.empty:
            #         st.dataframe(selected_data)
            #     else:
            #         st.warning("`selected_data` 为空，因此下方的行业对比模块不会显示。请检查为何没能从 `full_industry_df` 中筛选出数据。")

            #     st.markdown("---")
            #     st.markdown("#### 3. 条件判断 `if not selected_data.empty:` 的结果")
            #     if not selected_data.empty:
            #         st.success("结果为 `True`，应该显示行业对比。")
            #     else:
            #         st.error("结果为 `False`，不会显示行业对比。") 
            # 4. 创建Tabs进行分类展示
            tab_profit, tab_solvency, tab_growth, tab_operating, tab_cashflow = st.tabs(["盈利能力", "偿债能力", "成长能力", "运营能力", "现金流"])

            with tab_profit:
                st.subheader("盈利能力历史趋势")
                # --- 图表升级：使用Melt和Facet来展示多个指标 ---
                profit_metrics_to_plot = {
                    'roe': 'ROE',
                    'netprofit_margin': '净利率',
                    'grossprofit_margin': '毛利率'
                }
                df_p = combined_historical_df[['end_date', 'name', 'style'] + list(profit_metrics_to_plot.keys())].rename(columns=profit_metrics_to_plot)
                df_p_melted = df_p.melt(id_vars=['end_date', 'name', 'style'], var_name='指标名称', value_name='指标值')
                
                # profit_history_chart = alt.Chart(df_p_melted).mark_line().encode(
                #     x=alt.X('end_date:T', title='报告期'),
                #     y=alt.Y('指标值:Q', title='数值'),
                #     color=alt.Color('name:N', title='公司'),
                #     strokeDash=alt.StrokeDash('style:N', title='线型', legend=None)
                # ).properties(
                #     width=250, height=180
                # ).facet(
                #     column=alt.Column('指标名称:N', title=None) # 按指标名称分面
                # ).resolve_scale(
                #     y='independent' # 每个子图使用独立的Y轴刻度
                # )

                profit_history_chart = alt.Chart(df_p_melted).mark_line(point=True).encode(
                    x=alt.X('end_date:T', title='报告期'),
                    y=alt.Y('指标值:Q', title='数值 (%)'),
                    color=alt.Color('name:N', title='公司'),
                    strokeDash=alt.StrokeDash('style:N', title='线型', legend=None),
                    # --- 核心修改 1: 添加 tooltip ---
                    tooltip=[
                        alt.Tooltip('name', title='公司'),
                        alt.Tooltip('指标名称', title='指标'),
                        alt.Tooltip('end_date', title='报告期', format='%Y-%m-%d'),
                        alt.Tooltip('指标值', title='数值', format='.2f')
                    ]
                ).properties(
                    width=250, height=180
                ).facet(
                    column=alt.Column('指标名称:N', title=None)
                ).resolve_scale(
                    y='independent'
                ).interactive()

                st.altair_chart(profit_history_chart, use_container_width=True)
                # --- 第二部分：新增“指标对标”区域，并采用Tabs切换 ---
                st.markdown("---")
                st.subheader("盈利能力指标对标")
                
                if not selected_data.empty:
                    # 使用内部Tabs切换不同的指标对标
                    metric_tabs = st.tabs(["ROE 对标", "净利率 对标", "毛利率 对标"])

                    with metric_tabs[0]:
                        display_metric_comparison('roe', 'ROE', selected_data, full_industry_df, format_str='{:.2f}%')
                    
                    with metric_tabs[1]:
                        display_metric_comparison('netprofit_margin', '净利率', selected_data, full_industry_df, format_str='{:.2f}%')

                    with metric_tabs[2]:
                        display_metric_comparison('grossprofit_margin', '毛利率', selected_data, full_industry_df, format_str='{:.2f}%')
                else:
                    st.warning("无有效的行业数据，无法进行指标对标分析。")
                # --- 全新升级：盈利能力AI对比分析模块 ---
                st.markdown("---")
                st.subheader("🤖 盈利能力AI对比分析")
                
                # 只有一个按钮，用于分析本行业内所有选中的公司
                if st.button(f"生成对所选公司的盈利能力对比报告", key=f"ai_profit_compare"):
                    
                    # 1. 为选中的每家公司收集数据，并拼接成一个大的数据摘要
                    all_summaries = []
                    for code in codes_in_industry:
                        company_name = code_to_name_map.get(code, code)
                        
                        # a. 历史数据摘要
                        history_df = combined_historical_df[combined_historical_df['ts_code'] == code]
                        history_summary_lines = [f"\n--- 公司: {company_name} ({code}) ---", "历史趋势:"]
                        for metric, label in profit_metrics_to_plot.items():
                            # series_str = " -> ".join([f"{x:.2f}" for x in history_df[metric].tail(5)])
                            history_df['quarter'] = pd.to_datetime(history_df['end_date']).dt.to_period('Q')
                            series_str = ", ".join([f"{row.quarter}: {row[metric]:.2f}" for _, row in history_df[['quarter', metric]].tail(8).iterrows()])
                            history_summary_lines.append(f"- {label} (近5期): {series_str}")
                        
                        # b. 行业对标数据摘要
                        comparison_summary_lines = ["\n行业对标 (报告期 " + final_period_used + "):"]
                        if not selected_data.empty:
                            company_industry_data = selected_data[selected_data['ts_code'] == code].iloc[0]
                            for metric, label in profit_metrics_to_plot.items():
                                if metric in full_industry_df.columns:
                                    sorted_df = full_industry_df.sort_values(by=metric, ascending=False).reset_index()
                                    rank_info = sorted_df[sorted_df['ts_code'] == code]
                                    rank = rank_info.index[0] + 1 if not rank_info.empty else 'N/A'
                                    value = company_industry_data.get(metric, 0)
                                    comparison_summary_lines.append(f"- {label}: {value:.2f}%, 行业排名: {rank}/{len(full_industry_df)}")
                        
                        all_summaries.extend(history_summary_lines + comparison_summary_lines)
                    
                    full_summary = "\n".join(all_summaries)

                    # 2. 构建一个要求进行“对比分析”的全新提示词
                    prompt = f"""
                    你是一位顶尖的金融分析师，对商业的季节性（Seasonality）有深刻理解。我将为你提供【{industry}】行业中几家公司的盈利能力数据。

                    你的任务是生成一份专业的**对比分析报告**。分析时必须注意：这些数据有强烈的季节性特征，因此简单的环比（如Q1对比前一年的Q4）可能具有误导性。请你重点进行**同比增长**的对比分析。

                    报告需包含以下要点：
                    1.  **综合诊断**: 结合行业排名和历史数据，谁的综合盈利能力最强？它们的盈利能力是否表现出相似的季节性规律？
                    2.  **趋势解读**: 在剔除季节性因素后（比如观察同比数据），哪家公司的盈利能力是在真实地改善？谁的行业地位在逐年巩固？
                    3.  **投资观点**: 基于以上分析，从盈利能力和其稳定性的角度看，你会更青睐哪家公司？

                    以下是需要你分析的原始数据（格式为 YYYY-QQ: 值）:
                    ---
                    {full_summary}
                    ---
                    请确保你的分析是基于公司之间的横向对比，而不仅仅是罗列各家公司的情况。
                    """
                    
                    # 3. 调用通用AI函数并显示结果
                    with st.spinner("AI正在深度对比分析中，请稍候..."):
                        st.session_state.ai_profit_report = get_ai_analysis("对比报告", prompt)
                if st.session_state.ai_profit_report:
                    st.markdown(st.session_state.ai_profit_report)

            with tab_solvency:
                st.subheader("偿债能力历史趋势")
                solvency_metrics_to_plot = {
                    'debt_to_assets': '资产负债率 (%)',
                    'current_ratio': '流动比率',
                    'quick_ratio': '速动比率'
                }
                df_s = combined_historical_df[['end_date', 'name', 'style'] + list(solvency_metrics_to_plot.keys())].rename(columns=solvency_metrics_to_plot)
                df_s_melted = df_s.melt(id_vars=['end_date', 'name', 'style'], var_name='指标名称', value_name='指标值')

                # solvency_history_chart = alt.Chart(df_s_melted).mark_line().encode(
                #     x=alt.X('end_date:T', title='报告期'), y=alt.Y('指标值:Q', title='数值'),
                #     color=alt.Color('name:N', title='公司'), strokeDash=alt.StrokeDash('style:N', legend=None)
                # ).properties(width=250, height=180).facet(column=alt.Column('指标名称:N', title=None)).resolve_scale(y='independent')
                solvency_history_chart = alt.Chart(df_s_melted).mark_line(point=True).encode(
                    x=alt.X('end_date:T', title='报告期'), y=alt.Y('指标值:Q', title='数值'),
                    color=alt.Color('name:N', title='公司'), strokeDash=alt.StrokeDash('style:N', legend=None),
                    tooltip=[
                        alt.Tooltip('name', title='公司'),
                        alt.Tooltip('指标名称', title='指标'),
                        alt.Tooltip('end_date', title='报告期', format='%Y-%m-%d'),
                        alt.Tooltip('指标值', title='数值', format='.2f')
                    ]
                ).properties(width=250, height=180).facet(column=alt.Column('指标名称:N', title=None)).resolve_scale(y='independent').interactive()

                st.altair_chart(solvency_history_chart, use_container_width=True)
                st.markdown("---"); st.subheader("偿债能力指标对标")
                if not selected_data.empty:
                    metric_tabs = st.tabs(["资产负债率 对标", "流动比率 对标", "速动比率 对标"])
                    with metric_tabs[0]: display_metric_comparison('debt_to_assets', '资产负债率', selected_data, full_industry_df, ascending=True, format_str='{:.2f}%')
                    with metric_tabs[1]: display_metric_comparison('current_ratio', '流动比率', selected_data, full_industry_df)
                    with metric_tabs[2]: display_metric_comparison('quick_ratio', '速动比率', selected_data, full_industry_df)
                st.markdown("---")
                st.subheader("🤖 偿债能力AI对比分析")

                if st.button(f"生成对所选公司的偿债能力对比报告", key=f"ai_solvency_compare"):
                    
                    # 1. 收集所有偿债能力相关的数据
                    all_summaries = []
                    for code in codes_in_industry:
                        company_name = code_to_name_map.get(code, code)
                        
                        history_df = combined_historical_df[combined_historical_df['ts_code'] == code]
                        history_summary_lines = [f"\n--- 公司: {company_name} ({code}) ---", "历史趋势:"]
                        for metric, label in solvency_metrics_to_plot.items():
                            series_str = " -> ".join([f"{x:.2f}" for x in history_df[metric].tail(5)])
                            history_summary_lines.append(f"- {label} (近5期): {series_str}")
                        
                        comparison_summary_lines = ["\n行业对标 (报告期 " + final_period_used + "):"]
                        if not selected_data.empty:
                            company_industry_data = selected_data[selected_data['ts_code'] == code].iloc[0]
                            for metric, label in solvency_metrics_to_plot.items():
                                if metric in full_industry_df.columns:
                                    # 注意：资产负债率是升序排名（越小越好）
                                    asc = True if metric == 'debt_to_assets' else False
                                    sorted_df = full_industry_df.sort_values(by=metric, ascending=asc).reset_index()
                                    rank_info = sorted_df[sorted_df['ts_code'] == code]
                                    rank = rank_info.index[0] + 1 if not rank_info.empty else 'N/A'
                                    value = company_industry_data.get(metric, 0)
                                    comparison_summary_lines.append(f"- {label}: {value:.2f}, 行业排名: {rank}/{len(full_industry_df)}")
                        
                        all_summaries.extend(history_summary_lines + comparison_summary_lines)
                    
                    full_summary = "\n".join(all_summaries)

                    # 2. 构建一个要求进行“偿债能力对比分析”的全新提示词
                    prompt = f"""
                    你是一位顶尖的金融风控专家，擅长评估公司的财务健康状况和偿债风险。我将为你提供【{industry}】行业中几家公司的偿债能力数据。

                    你的任务是生成一份专业的**偿债能力对比分析报告**。请务必使用**“行业排名”**来衡量它们的相对风险水平。
                    1.  **风险评级**: 谁的财务杠杆最合理，偿债风险最低？谁的风险最高？请结合**资产负债率的行业排名**进行评级。
                    2.  **长短期风险分析**: 对比它们的短期流动性（流动比率）和长期债务负担（资产负债率），是否存在风险错配？
                    3.  **战略推断**: 从财务杠杆的使用和排名看，可以看出这几家公司的经营战略有何不同吗？（例如：一家是利用高杠杆获取高排名的激进派，另一家是低杠杆稳健派）
                    4.  **贷方视角**: 如果你是银行审批官，谁的**行业排名和财务数据**更能让你放心批复贷款？

                    以下是需要你分析的几家公司的原始数据：
                    ---
                    {full_summary}
                    ---
                    请确保你的分析紧扣“偿债能力”这个主题，并充分利用所给的全部数据进行对比。
                    """
                    
                    # 3. 调用通用AI函数并显示结果
                    with st.spinner("AI正在深度对比分析中，请稍候..."):
                        # ai_report = get_ai_analysis("对比报告", prompt)
                        # st.markdown(ai_report)
                        st.session_state.ai_solvency_report = get_ai_analysis("对比报告", prompt)
                if st.session_state.ai_solvency_report:
                    st.markdown(st.session_state.ai_solvency_report)

            with tab_growth:
                st.subheader("成长能力历史趋势")
                growth_metrics_to_plot = {'or_yoy': '营收同比 (%)', 'netprofit_yoy': '净利同比 (%)'}
                df_g = combined_historical_df[['end_date', 'name', 'style'] + list(growth_metrics_to_plot.keys())].rename(columns=growth_metrics_to_plot)
                df_g_melted = df_g.melt(id_vars=['end_date', 'name', 'style'], var_name='指标名称', value_name='指标值')

                # growth_history_chart = alt.Chart(df_g_melted).mark_line().encode(
                #     x=alt.X('end_date:T', title='报告期'), y=alt.Y('指标值:Q', title='数值 (%)'),
                #     color=alt.Color('name:N', title='公司'), strokeDash=alt.StrokeDash('style:N', legend=None)
                # ).properties(width=250, height=180).facet(column=alt.Column('指标名称:N', title=None)).resolve_scale(y='independent')
                growth_history_chart = alt.Chart(df_g_melted).mark_line(point=True).encode(
                    x=alt.X('end_date:T', title='报告期'), y=alt.Y('指标值:Q', title='数值'),
                    color=alt.Color('name:N', title='公司'), strokeDash=alt.StrokeDash('style:N', legend=None),
                    tooltip=[
                        alt.Tooltip('name', title='公司'),
                        alt.Tooltip('指标名称', title='指标'),
                        alt.Tooltip('end_date', title='报告期', format='%Y-%m-%d'),
                        alt.Tooltip('指标值', title='数值', format='.2f')
                    ]
                ).properties(width=250, height=180).facet(column=alt.Column('指标名称:N', title=None)).resolve_scale(y='independent').interactive()


                st.altair_chart(growth_history_chart, use_container_width=True)
                st.markdown("---"); st.subheader("成长能力指标对标")
                if not selected_data.empty:
                    metric_tabs = st.tabs(["营收同比 对标", "净利同比 对标"])
                    with metric_tabs[0]: display_metric_comparison('or_yoy', '营收同比', selected_data, full_industry_df, format_str='{:.2f}%')
                    with metric_tabs[1]: display_metric_comparison('netprofit_yoy', '净利同比', selected_data, full_industry_df, format_str='{:.2f}%')
                st.markdown("---")
                st.subheader("🤖 成长能力AI对比分析")
                if st.button(f"生成成长能力对比报告", key=f"ai_growth_compare"):
                    all_summaries = []
                    for code in codes_in_industry:
                        company_name = code_to_name_map.get(code, code)
                        history_df = combined_historical_df[combined_historical_df['ts_code'] == code]
                        history_summary_lines = [f"\n--- 公司: {company_name} ({code}) ---", "历史趋势:"]
                        for metric, label in growth_metrics_to_plot.items():
                            series_str = " -> ".join([f"{x:.2f}" for x in history_df[metric].tail(5)])
                            history_summary_lines.append(f"- {label} (近5期): {series_str}")
                        comparison_summary_lines = ["\n行业对标 (报告期 " + final_period_used + "):"]
                        if not selected_data.empty:
                            company_industry_data = selected_data[selected_data['ts_code'] == code].iloc[0]
                            for metric, label in growth_metrics_to_plot.items():
                                if metric in full_industry_df.columns:
                                    sorted_df = full_industry_df.sort_values(by=metric, ascending=False).reset_index()
                                    rank_info = sorted_df[sorted_df['ts_code'] == code]
                                    rank = rank_info.index[0] + 1 if not rank_info.empty else 'N/A'
                                    value = company_industry_data.get(metric, 0)
                                    comparison_summary_lines.append(f"- {label}: {value:.2f}%, 行业排名: {rank}/{len(full_industry_df)}")
                        all_summaries.extend(history_summary_lines + comparison_summary_lines)
                    full_summary = "\n".join(all_summaries)
                    prompt = f"""
                        你是一位顶尖的成长股投资分析师。我将为你提供【{industry}】行业中几家公司的成长能力数据。

                    你的任务是生成一份专业的**成长能力对比分析报告**。
                    1.  **成长质量评估**: 谁是真正的成长领袖？请结合**营收增速和净利增速的绝对值与行业排名**进行判断。是否存在“增收不增利”的伪成长？
                    2.  **趋势与持续性**: 结合历史数据，谁的增长趋势更稳定、更具持续性？谁的行业领先地位是新晋获得的？
                    3.  **未来潜力**: 基于当前的增长态势和行业排名，你认为哪家公司未来的增长潜力更大？

                        以下是需要你分析的几家公司的原始数据：
                        ---
                        {full_summary}
                        ---
                        请围绕“成长性”这个核心进行深入对比分析。
                        """
                    with st.spinner("AI正在深度对比分析中，请稍候..."):
                        # ai_report = get_ai_analysis("对比报告", prompt)
                        # st.markdown(ai_report)
                        st.session_state.ai_growth_report = get_ai_analysis("对比报告", prompt)
                if st.session_state.ai_growth_report:
                    st.markdown(st.session_state.ai_growth_report)

            with tab_operating:
                st.subheader("运营能力历史趋势")
                op_metrics_to_plot = {'assets_turn': '总资产周转率', 'inv_turn': '存货周转率', 'ar_turn': '应收账款周转率'}
                df_o = combined_historical_df[['end_date', 'name', 'style'] + list(op_metrics_to_plot.keys())].rename(columns=op_metrics_to_plot)
                df_o_melted = df_o.melt(id_vars=['end_date', 'name', 'style'], var_name='指标名称', value_name='指标值')
                
                # op_history_chart = alt.Chart(df_o_melted).mark_line().encode(
                #     x=alt.X('end_date:T', title='报告期'), y=alt.Y('指标值:Q', title='周转次数'),
                #     color=alt.Color('name:N', title='公司'), strokeDash=alt.StrokeDash('style:N', legend=None)
                # ).properties(width=250, height=180).facet(column=alt.Column('指标名称:N', title=None)).resolve_scale(y='independent')

                op_history_chart = alt.Chart(df_o_melted).mark_line(point=True).encode(
                    x=alt.X('end_date:T', title='报告期'), y=alt.Y('指标值:Q', title='数值 (%)'),
                    color=alt.Color('name:N', title='公司'), strokeDash=alt.StrokeDash('style:N', legend=None),
                    tooltip=[
                        alt.Tooltip('name', title='公司'),
                        alt.Tooltip('指标名称', title='指标'),
                        alt.Tooltip('end_date', title='报告期', format='%Y-%m-%d'),
                        alt.Tooltip('指标值', title='数值', format='.2f')
                    ]
                ).properties(width=250, height=180).facet(column=alt.Column('指标名称:N', title=None)).resolve_scale(y='independent').interactive()
 
                st.altair_chart(op_history_chart, use_container_width=True)
                st.markdown("---")
                if not selected_data.empty:
                    display_metric_comparison('assets_turn', '总资产周转率', selected_data, full_industry_df)
                st.markdown("---")
                st.subheader("🤖 运营能力AI对比分析")
                if st.button(f"生成运营能力对比报告", key=f"ai_operating_compare"):
                    all_summaries = []
                    for code in codes_in_industry:
                        company_name = code_to_name_map.get(code, code)
                        history_df = combined_historical_df[combined_historical_df['ts_code'] == code]
                        history_summary_lines = [f"\n--- 公司: {company_name} ({code}) ---", "历史趋势:"]
                        for metric, label in op_metrics_to_plot.items():
                            # series_str = " -> ".join([f"{x:.2f}" for x in history_df[metric].tail(5)])
                            history_df['quarter'] = pd.to_datetime(history_df['end_date']).dt.to_period('Q')
                            series_str = ", ".join([f"{row.quarter}: {row[metric]:.2f}" for _, row in history_df[['quarter', metric]].tail(8).iterrows()])                        
                            history_summary_lines.append(f"- {label} (近5期): {series_str}")
                        comparison_summary_lines = ["\n行业对标 (报告期 " + final_period_used + "):"]
                        if not selected_data.empty:
                            company_industry_data = selected_data[selected_data['ts_code'] == code].iloc[0]
                            for metric, label in op_metrics_to_plot.items():
                                if metric in full_industry_df.columns:
                                    sorted_df = full_industry_df.sort_values(by=metric, ascending=False).reset_index()
                                    rank_info = sorted_df[sorted_df['ts_code'] == code]
                                    rank = rank_info.index[0] + 1 if not rank_info.empty else 'N/A'
                                    value = company_industry_data.get(metric, 0)
                                    comparison_summary_lines.append(f"- {label}: {value:.2f}, 行业排名: {rank}/{len(full_industry_df)}")
                        all_summaries.extend(history_summary_lines + comparison_summary_lines)
                    full_summary = "\n".join(all_summaries)
                    prompt = f"""
                    你是一位顶尖的企业运营管理顾问，非常清楚运营效率会受季节性需求波动的影响。我将为你提供【{industry}】行业中几家公司的运营效率数据。

                    你的任务是生成一份专业的**运营能力对比分析报告**。分析时请务必考虑季节性因素。
                    1.  **效率评级**: 谁是最高效的运营者？请对其运营效率进行排序。
                    2.  **季节性管理**: 从各项周转率的季度变化中，能否看出哪家公司对季节性波动的管理能力更强（例如，在旺季能快速清空库存）？
                    3.  **真实效率趋势**: 剔除季节性影响后，谁的运营效率在持续、真实地提升？

                    以下是需要你分析的原始数据（格式为 YYYY-QQ: 值）:
                    ---
                    {full_summary}
                    ---
                    请围绕“运营效率”这个核心进行深入对比分析。
                    """
                    with st.spinner("AI正在深度对比分析中，请稍候..."):
                        st.session_state.ai_operating_report = get_ai_analysis("对比报告", prompt)
                if st.session_state.ai_operating_report:
                    st.markdown(st.session_state.ai_operating_report)

            with tab_cashflow:
                st.subheader("现金流历史趋势")
                cash_metrics_to_plot = {'fcff': '企业自由现金流', 'fcfe': '股权自由现金流'}
                df_c = combined_historical_df[['end_date', 'name', 'style'] + list(cash_metrics_to_plot.keys())].rename(columns=cash_metrics_to_plot)
                df_c_melted = df_c.melt(id_vars=['end_date', 'name', 'style'], var_name='指标名称', value_name='金额 (元)')
                
                # cash_history_chart = alt.Chart(df_c_melted).mark_line().encode(
                #     x=alt.X('end_date:T', title='报告期'), y=alt.Y('金额 (元):Q', title='金额 (元)'),
                #     color=alt.Color('name:N', title='公司'), strokeDash=alt.StrokeDash('style:N', legend=None)
                # ).properties(width=250, height=180).facet(column=alt.Column('指标名称:N', title=None)).resolve_scale(y='independent')

                cash_history_chart = alt.Chart(df_c_melted).mark_line(point=True).encode(
                    x=alt.X('end_date:T', title='报告期'), y=alt.Y('金额 (元):Q', title='金额 (元)'),
                    color=alt.Color('name:N', title='公司'), strokeDash=alt.StrokeDash('style:N', legend=None),
                    tooltip=[
                        alt.Tooltip('name', title='公司'),
                        alt.Tooltip('指标名称', title='指标'),
                        alt.Tooltip('end_date', title='报告期', format='%Y-%m-%d'),
                        alt.Tooltip('金额 (元)', title='金额', format=',.0f') # 使用千分位格式化
                    ]
                ).properties(width=250, height=180).facet(column=alt.Column('指标名称:N', title=None)).resolve_scale(y='independent').interactive()

                st.altair_chart(cash_history_chart, use_container_width=True)
                st.markdown("---")
                st.subheader("🤖 现金流AI独立分析")
                st.info("由于现金流绝对值受公司规模影响巨大，此处的AI分析将对每家公司进行独立的纵向历史分析，而非横向对比。")

                # 为每家公司提供一个单独的分析按钮
                for code in codes_in_industry:
                    company_name = code_to_name_map.get(code, code)
                    
                    with st.expander(f"点击生成对 **{company_name}** 的现金流分析报告"):
                        if st.button("开始独立分析", key=f"ai_cashflow_single_{code}"):
                            
                            # 1. 只收集这家公司的历史数据
                            history_df = combined_historical_df[combined_historical_df['ts_code'] == code]
                            summary_lines = [f"公司: {company_name} ({code})", "\n历史现金流数据 (近5期):"]
                            
                            # --- 核心修改：采用新的、带季度标签的格式 ---
                            history_df['quarter'] = pd.to_datetime(history_df['end_date']).dt.to_period('Q')
                            for metric, label in cash_metrics_to_plot.items():
                                # 使用{:,.0f}来格式化大的现金流数值，并保留季度标签
                                series_str = ", ".join([f"{row.quarter}: {row[metric]:,.0f}" for _, row in history_df[['quarter', metric]].tail(8).iterrows() if pd.notna(row[metric])])
                                summary_lines.append(f"- {label}: {series_str}")
                            
                            single_company_summary = "\n".join(summary_lines)

                            # 2. 调用已为季节性优化的Prompt (无需修改)
                            prompt = f"""
                            你是一位顶尖的价值投资分析师，将“现金流”视为企业价值的基石，并深知其季节性波动规律。我将为你提供“{company_name}”这家公司的历史现金流数据。

                            你的任务是生成一份专业的**单公司现金流深度分析报告**。请务必在分析中考虑季节性。
                            1.  **“造血”能力评估**: 综合来看，这家公司的现金流状况如何？是否存在明显的季节性流入（如年末回款）和流出（如年初采购）？
                            2.  **趋势解读**: 在剔除季节性因素后（例如进行同比增长对比），它的核心“造血”能力（特别是FCFF）是在增长、稳定还是萎缩？这可能反映出公司正处于哪个发展阶段？
                            3.  **财务健康度总结**: 基于以上分析，对该公司的现金流健康度给出一个总结性评价。

                            以下是需要你分析的原始数据（格式为YYYY-QQ: 值）:
                            ---
                            {single_company_summary}
                            ---
                            请仅围绕这家公司的历史现金流数据进行深入分析。
                            """
                            
                            # 3. 调用通用AI函数并显示结果
                            with st.spinner(f"AI正在对 {company_name} 的现金流进行深度分析..."):
                                # ai_report = get_ai_analysis(company_name, prompt)
                                # st.markdown(ai_report)
                                st.session_state.ai_cashflow_report = get_ai_analysis(company_name, prompt)
                if st.session_state.ai_cashflow_report:
                    st.markdown(st.session_state.ai_cashflow_report)
        with harvard_tabs[3]:
            st.info("AI将扮演“首席分析师”，结合我们提供的公司最新财务快照和它自身的宏观知识库，对公司的未来发展前景进行预测和评级。")

            # 这个分析是面向所有选中公司的对比分析
            if st.button("生成AI前景对比分析报告", key=f"ai_prospect_compare_{industry}"):
                
                # 1. 为选中的每家公司，准备一份“财务快照”
                all_summaries = []
                if not selected_data.empty:
                    for code in codes_in_industry:
                        company_name = code_to_name_map.get(code, code)
                        company_snapshot = selected_data[selected_data['ts_code'] == code].iloc[0]
                        
                        # 即时计算ROE排名
                        sorted_roe = full_industry_df.sort_values(by='roe', ascending=False).reset_index()
                        rank_info = sorted_roe[sorted_roe['ts_code'] == code]
                        rank = rank_info.index[0] + 1 if not rank_info.empty else 'N/A'

                        summary_lines = [
                            f"\n--- 公司: {company_name} ({code}) ---",
                            f"- 最新ROE: {company_snapshot.get('roe', 0):.2f}% (行业排名: {rank}/{len(full_industry_df)})",
                            f"- 最新资产负债率: {company_snapshot.get('debt_to_assets', 0):.2f}%",
                            f"- 最新营收同比: {company_snapshot.get('or_yoy', 0):.2f}%"
                        ]
                        all_summaries.append("\n".join(summary_lines))
                
                data_summary = "\n".join(all_summaries)

                # 2. 构建新的、更清晰的Prompt
                prompt = f"""
                你是一位经验丰富的基金经理和行业首席分析师。你的任务是结合我提供的【公司最新财务快照】和你自己知识库中的【宏观及行业趋势】，为选中的公司撰写一份**前景对比分析报告**。

                你的报告需要包含：
                1.  **短期展望 (1-2年)**: 基于公司最新的财务表现（如增长率、利润率），分析并对比它们近期的机遇和挑战。
                2.  **长期展望 (3-5年)**: 结合它们的行业地位（可参考ROE排名）和你对行业变革、技术趋势的知识，分析并对比它们的长期增长潜力和护城河。
                3.  **关键驱动与风险**: 对比指出各公司未来发展的核心驱动力及主要风险点。
                4.  **综合投资评级**: 为每家公司给出一个明确的投资评级（例如：强烈看好、谨慎看好、中性、看淡），并附上一句核心的投资逻辑总结。

                以下是【公司最新财务快照】：
                ---
                {data_summary}
                ---
                请基于这些数据锚点，并结合你的专业知识，开始你的分析。
                """
                with st.spinner("AI正在进行前景分析与展望..."):
                    ai_report = get_ai_response(prompt)
                    st.markdown(ai_report)
   
else:
    st.info("👈 请在左侧边栏选择公司并点击“开始分析”按钮。")