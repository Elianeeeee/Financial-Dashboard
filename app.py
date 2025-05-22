import streamlit as st
import pandas as pd
import altair as alt
# from finance_utils import fetch_financials, compute_indicators, lookup_ts_codes, dupont, lookup_stock_basic
from finance_utils import (
    lookup_stock_basic,
    fetch_all_data,
    compute_indicators,
    dupont,
    calc_profitability,
    calc_solvency,
    calc_growth,
    calc_operating,
    calc_cashflow,
    fetch_cash_flow,
    calc_solvency
)
st.set_page_config(layout="wide")
st.title("📊 财务指标一键分析")

# # —— 侧边栏：参数设置
# st.sidebar.header("参数设置")

# # 1) 按公司名称模糊搜索（支持逗号分隔多关键词）
# name_filter = st.sidebar.text_input(
#     "输入公司名称（支持逗号分隔多关键词）进行模糊搜索",
#     value=""
# )

# # 从 stock_basic 缓存里拿出所有 ts_code 和 name
# basic_df = lookup_stock_basic()

# if name_filter:
#     # 支持多关键词
#     keywords = [kw.strip() for kw in name_filter.split(",") if kw.strip()]
#     mask = pd.Series(False, index=basic_df.index)
#     for kw in keywords:
#         mask |= basic_df["name"].str.contains(kw, na=False)
#     df2 = basic_df[mask]

#     # 构造“TS代码 (公司名称)”的选项
#     options = {
#         f"{row.ts_code} ({row['name']})": row.ts_code
#         for _, row in df2.iterrows()
#     }

#     selected = st.sidebar.multiselect(
#         "从匹配结果中选择公司",
#         options=list(options.keys()),
#         default=[]
#     )
#     # 拆回真正的 ts_code 列表
#     stocks = [options[k] for k in selected]
# else:
#     # 如果没输入名称，就允许手动输入 TS 代码
#     codes_input = st.sidebar.text_input(
#         "或直接输入 TS 股票代码（逗号分隔）",
#         value=""
#     )
#     stocks = [c.strip() for c in codes_input.split(",") if c.strip()]

# # 2) 年份区间（用于最新期计算）：
# year_range = st.sidebar.slider(
#     "选择年份区间",
#     min_value=2000, max_value=pd.Timestamp.now().year,
#     value=(2019, pd.Timestamp.now().year)
# )

# # 3) 历史趋势：可选指标 & 历史对比区间
# metrics_list = [
#     "roe", "netprofit_margin", "assets_turn", "debt_to_assets", "grossprofit_margin"
# ]
# selected_metrics = st.sidebar.multiselect(
#     "选择要查看的历史指标",
#     options=metrics_list,
#     default=["roe", "netprofit_margin"]
# )
# hist_year_range = st.sidebar.slider(
#     "历史对比年份范围",
#     min_value=2000, max_value=pd.Timestamp.now().year,
#     value=(year_range[0] - 5, year_range[1])
# )

# ——————————————————————————————
# 当点击“开始分析”时，执行所有逻辑
# if st.sidebar.button("开始分析"):

#     # 1) 最新期指标
#     df_latest = []
#     for code in stocks:
#         df = fetch_financials(code, year_range[0], year_range[1])
#         inds = compute_indicators(df)
#         inds["ts_code"] = code
#         df_latest.append(inds)
#     df_latest = pd.DataFrame(df_latest)

#     st.subheader("最新一期财务指标")
#     st.dataframe(df_latest.set_index("ts_code"))

#     # 最新期并排柱状图
#     df_plot = df_latest.melt(
#         id_vars="ts_code",
#         value_vars=["ROE (%)", "净利率 (%)"],
#         var_name="指标",
#         value_name="数值"
#     )
#     bar = (
#         alt.Chart(df_plot)
#         .mark_bar()
#         .encode(
#             x=alt.X("ts_code:N", title="股票代码"),
#             y=alt.Y("数值:Q", title="数值"),
#             color="指标:N",
#             xOffset="指标:N"
#         )
#     )
#     st.altair_chart(bar, use_container_width=True)

#     # 2) 历史趋势 & DuPont 拆解
#     st.subheader("历史趋势及 DuPont 拆解")
#     for code in stocks:
#         st.markdown(f"### {code} 历史趋势")
#         df_hist = fetch_financials(code, hist_year_range[0], hist_year_range[1])
#         # 转成 datetime
#         df_hist["end_date"] = pd.to_datetime(df_hist["end_date"], format="%Y%m%d")
#         df_hist_plot = df_hist.melt(
#             id_vars=["end_date"],
#             value_vars=selected_metrics,
#             var_name="指标",
#             value_name="数值"
#         )
#         line = (
#             alt.Chart(df_hist_plot)
#             .mark_line(point=True)
#             .encode(
#                 x=alt.X("end_date:T", title="报告期"),
#                 y=alt.Y("数值:Q", title="数值"),
#                 color="指标:N"
#             )
#         )
#         st.altair_chart(line, use_container_width=True)

#         # DuPont 拆解
#         st.markdown(f"**{code} DuPont 拆解 (ROE = 净利率×资产周转率×权益乘数)**")
#         df_dup = dupont(df_hist).drop_duplicates(subset="end_date", keep="last")
#         df_dup["end_date"] = pd.to_datetime(df_dup["end_date"], format="%Y-%m-%d")
#         st.dataframe(df_dup.set_index("end_date"))
#         dup_line = (
#             alt.Chart(
#                 df_dup.melt(
#                     id_vars="end_date",
#                     value_vars=["ROE_拆解", "净利率", "资产周转率", "权益乘数"],
#                     var_name="成分",
#                     value_name="数值"
#                 )
#             )
#             .mark_line(point=True)
#             .encode(
#                 x=alt.X("end_date:T", title="报告期"),
#                 y=alt.Y("数值:Q", title="数值"),
#                 color=alt.Color("成分:N", title="成分")
#             )
#         )
#         st.altair_chart(dup_line, use_container_width=True)

# else:
#     st.info("请在左侧设置参数后，点击“开始分析”")

# —— 侧边栏：参数设置
st.sidebar.header("参数设置")

# 1) 公司名称模糊搜索
basic_df = lookup_stock_basic()
name_filter = st.sidebar.text_input(
    "输入公司名称（逗号分隔多关键词）",
    value=""
)
if name_filter:
    keywords = [kw.strip() for kw in name_filter.split(",") if kw.strip()]
    mask = pd.Series(False, index=basic_df.index)
    for kw in keywords:
        mask |= basic_df["name"].str.contains(kw, na=False)
    df2 = basic_df[mask]
    options = {
        f"{row.ts_code} ({row['name']})": row.ts_code
        for _, row in df2.iterrows()
    }
    selected = st.sidebar.multiselect(
        "从匹配结果中选择公司",
        options=list(options.keys()),
        default=[]
    )
    stocks = [options[k] for k in selected]
else:
    codes_input = st.sidebar.text_input(
        "或直接输入 TS 股票代码（逗号分隔）",
        value=""
    )
    stocks = [c.strip() for c in codes_input.split(",") if c.strip()]

# 2) 时间区间 & 历史对比设置
current_year = pd.Timestamp.now().year
year_range = st.sidebar.slider(
    "选择最新期年份范围",
    min_value=2000, max_value=current_year,
    value=(current_year-1, current_year)
)
metrics_list = [
    "roe", "netprofit_margin", "assets_turn",
    "debt_to_assets", "grossprofit_margin"
]
selected_metrics = st.sidebar.multiselect(
    "选择历史对比指标",
    options=metrics_list,
    default=["roe", "netprofit_margin"]
)
hist_year_range = st.sidebar.slider(
    "历史对比年份范围",
    min_value=2000, max_value=current_year,
    value=(year_range[0]-5, year_range[1])
)

# ——————————————————————————————

if st.sidebar.button("开始分析") and stocks:

    # — ① 最新期指标
    df_latest = []
    for code in stocks:
        df_all = fetch_all_data(code, year_range[0], year_range[1])
        inds   = compute_indicators(df_all)
        inds["ts_code"] = code
        df_latest.append(inds)
    df_latest = pd.DataFrame(df_latest)

    st.subheader("最新一期财务指标")
    st.dataframe(df_latest.set_index("ts_code"))

    # 并排柱状图
    df_plot = df_latest.melt(
        id_vars="ts_code",
        value_vars=["ROE (%)", "净利率 (%)"],
        var_name="指标",
        value_name="数值"
    )
    bar = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("ts_code:N", title="股票代码"),
            y=alt.Y("数值:Q", title="数值"),
            color="指标:N",
            xOffset="指标:N"
        )
    )
    st.altair_chart(bar, use_container_width=True)

    # — ② 历史趋势 & DuPont & 分类展示
    for code in stocks:
        st.markdown(f"### {code} 历史趋势 & 分类指标")
        df_all = fetch_all_data(code, hist_year_range[0], hist_year_range[1])
        cf_df = fetch_cash_flow(code, hist_year_range[0], hist_year_range[1])

        # 历史折线
        df_hist = df_all.copy()
        df_hist_plot = df_hist.melt(
            id_vars=["end_date"],
            value_vars=selected_metrics,
            var_name="指标",
            value_name="数值"
        )
        line = (
            alt.Chart(df_hist_plot)
            .mark_line(point=True)
            .encode(
                x=alt.X("end_date:T", title="报告期"),
                y=alt.Y("数值:Q", title="数值"),
                color="指标:N"
            )
        )
        st.altair_chart(line, use_container_width=True)

        # DuPont 拆解
        st.markdown("**DuPont 拆解 (ROE = 净利率×资产周转率×权益乘数)**")
        df_dup = dupont(df_hist)
        st.dataframe(df_dup.set_index("end_date"))
        dup_plot = (
            alt.Chart(
                df_dup.melt(
                    id_vars="end_date",
                    value_vars=["ROE_拆解", "净利率", "资产周转率", "权益乘数"],
                    var_name="成分",
                    value_name="数值"
                )
            )
            .mark_line(point=True)
            .encode(
                x="end_date:T", y="数值:Q", color="成分:N"
            )
        )
        st.altair_chart(dup_plot, use_container_width=True)

        # # 分类指标展示
        # prof   = calc_profitability(df_hist)
        # solv   = calc_solvency(df_hist)
        # growth = calc_growth(df_hist)
        # oper   = calc_operating(df_hist)
        # cash   = calc_cashflow(df_hist)

        # col1, col2 = st.columns(2)
        # with col1:
        #     # 盈利能力：改用 columns + metric
        #     st.markdown("#### 盈利能力")
        #     prof_dict = prof.to_dict()
        #     cols = st.columns(len(prof_dict))
        #     for (name, val), col in zip(prof_dict.items(), cols):
        #         display = f"{val:.2f}" if isinstance(val, (int, float)) else val
        #         if name.endswith("%"):
        #             display = f"{display}%"
        #         col.metric(label=name, value=display)
        #     st.markdown("#### 偿债能力")
        #     st.bar_chart(pd.DataFrame(solv, index=[0]).T, use_container_width=True)
        #     st.markdown("#### 成长性")
        #     st.line_chart(pd.DataFrame(growth, index=[0]).T, use_container_width=True)
        # with col2:
        #     st.markdown("#### 运营能力")
        #     df_op = oper / oper.sum()
        #     pie = alt.Chart(df_op.reset_index().melt(
        #         id_vars="index", value_vars=[0], var_name="dummy", value_name="占比"
        #     )).mark_arc().encode(
        #         theta="占比:Q",
        #         color=alt.Color("index:N", title="指标")
        #     )
        #     st.altair_chart(pie, use_container_width=True)

        #     st.markdown("#### 造血能力")
        #     st.table(pd.DataFrame(cash, index=[0]).T)
          # —— 分类指标展示：全部用 metric 并列展示
        prof   = calc_profitability(df_hist)
        solv   = calc_solvency(df_all, cf_df)
        growth = calc_growth(df_hist)
        oper   = calc_operating(df_hist)
        cash   = calc_cashflow(df_hist)

        def show_metrics(title: str, series: pd.Series):
            st.markdown(f"#### {title}")
            d = series.to_dict()
            cols = st.columns(len(d))
            for (name, val), col in zip(d.items(), cols):
                # 格式化显示
                if isinstance(val, (int, float)):
                    disp = f"{val:.2f}"
                    if name.endswith("%"):
                        disp += "%"
                else:
                    disp = val
                col.metric(label=name, value=disp)

        # 两列布局
        col1, col2 = st.columns(2)
        with col1:
            show_metrics("盈利能力", prof)
            show_metrics("偿债能力", solv)
            show_metrics("成长性", growth)
        with col2:
            show_metrics("运营能力", oper)
            st.markdown("#### 造血能力")
            cash_display = cash / 1e8
            cash_display = cash_display.round(2)
            cf_cols = st.columns(len(cash_display))
            for (name, val), cf_col in zip(cash_display.items(), cf_cols):
                cf_col.metric(label=name, value=f"{val:.2f} 亿元")