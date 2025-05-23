import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
# from finance_utils import fetch_financials, compute_indicators, lookup_ts_codes, dupont, lookup_stock_basic
from finance_utils import (
    lookup_stock_basic,
    fetch_all_data,
    fetch_cash_flow,
    fetch_price,
    compute_indicators,
    dupont,
    calc_profitability,
    calc_solvency,
    calc_growth,
    calc_operating,
    calc_cashflow
)
st.set_page_config(layout="wide")
st.title("📊 财务指标一键分析")


# # —— 侧边栏：参数设置
# st.sidebar.header("参数设置")

# # 1) 公司名称模糊搜索
# basic_df = lookup_stock_basic()
# name_filter = st.sidebar.text_input(
#     "输入公司名称（逗号分隔多关键词）",
#     value=""
# )
# if name_filter:
#     keywords = [kw.strip() for kw in name_filter.split(",") if kw.strip()]
#     mask = pd.Series(False, index=basic_df.index)
#     for kw in keywords:
#         mask |= basic_df["name"].str.contains(kw, na=False)
#     df2 = basic_df[mask]
#     options = {
#         f"{row.ts_code} ({row['name']})": row.ts_code
#         for _, row in df2.iterrows()
#     }
#     selected = st.sidebar.multiselect(
#         "从匹配结果中选择公司",
#         options=list(options.keys()),
#         default=[]
#     )
#     stocks = [options[k] for k in selected]
# else:
#     codes_input = st.sidebar.text_input(
#         "或直接输入 TS 股票代码（逗号分隔）",
#         value=""
#     )
#     stocks = [c.strip() for c in codes_input.split(",") if c.strip()]

# # 2) 时间区间 & 历史对比设置
# current_year = pd.Timestamp.now().year
# year_range = st.sidebar.slider(
#     "选择最新期年份范围",
#     min_value=2000, max_value=current_year,
#     value=(current_year-1, current_year)
# )
# metrics_list = [
#     "roe", "netprofit_margin", "assets_turn",
#     "debt_to_assets", "grossprofit_margin"
# ]
# selected_metrics = st.sidebar.multiselect(
#     "选择历史对比指标",
#     options=metrics_list,
#     default=["roe", "netprofit_margin"]
# )
# hist_year_range = st.sidebar.slider(
#    "历史对比年份范围",
#     min_value=2000, max_value=current_year,
#     value=(year_range[0]-5, year_range[1])
# )

# # ——————————————————————————————

# if st.sidebar.button("开始分析") and stocks:

#     # — ① 最新期指标
#     df_latest = []
#     for code in stocks:
#         df_all = fetch_all_data(code, year_range[0], year_range[1])
#         inds   = compute_indicators(df_all)
#         inds["ts_code"] = code
#         df_latest.append(inds)
#     df_latest = pd.DataFrame(df_latest)

#     st.subheader("最新一期财务指标")
#     st.dataframe(df_latest.set_index("ts_code"))

#     # 并排柱状图
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

#     # — ② 历史趋势 & DuPont & 分类展示
#     for code in stocks:
#         st.markdown(f"### {code} 历史趋势 & 分类指标")
#         df_all = fetch_all_data(code, hist_year_range[0], hist_year_range[1])
#         cf_df = fetch_cash_flow(code, hist_year_range[0], hist_year_range[1])

#         # 历史折线
#         df_hist = df_all.copy()
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
#         st.markdown("**DuPont 拆解 (ROE = 净利率×资产周转率×权益乘数)**")
#         df_dup = dupont(df_hist)
#         st.dataframe(df_dup.set_index("end_date"))
#         dup_plot = (
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
#                 x="end_date:T", y="数值:Q", color="成分:N"
#             )
#         )
#         st.altair_chart(dup_plot, use_container_width=True)
#         prof   = calc_profitability(df_hist)
#         solv   = calc_solvency(df_all, cf_df)
#         growth = calc_growth(df_hist)
#         oper   = calc_operating(df_hist)
#         cash   = calc_cashflow(df_hist)

#         def show_metrics(title: str, series: pd.Series):
#             st.markdown(f"#### {title}")
#             d = series.to_dict()
#             cols = st.columns(len(d))
#             for (name, val), col in zip(d.items(), cols):
#                 # 格式化显示
#                 if isinstance(val, (int, float)):
#                     disp = f"{val:.2f}"
#                     if name.endswith("%"):
#                         disp += "%"
#                 else:
#                     disp = val
#                 col.metric(label=name, value=disp)

#         # 两列布局
#         col1, col2 = st.columns(2)
#         with col1:
#             show_metrics("盈利能力", prof)
#             show_metrics("偿债能力", solv)
#             show_metrics("成长性", growth)
#         with col2:
#             show_metrics("运营能力", oper)
#             st.markdown("#### 造血能力")
#             cash_display = cash / 1e8
#             cash_display = cash_display.round(2)
#             cf_cols = st.columns(len(cash_display))
#             for (name, val), cf_col in zip(cash_display.items(), cf_cols):
#                 cf_col.metric(label=name, value=f"{val:.2f} 亿元")

# —— 侧边栏
st.sidebar.header("参数设置")
basic_df   = lookup_stock_basic()
name_filter= st.sidebar.text_input("输入公司名称（多关键词逗号分隔）")
if name_filter:
    kws = [kw.strip() for kw in name_filter.split(",") if kw.strip()]
    mask= pd.Series(False, index=basic_df.index)
    for kw in kws:
        mask |= basic_df["name"].str.contains(kw, na=False)
    df2 = basic_df[mask]
    options = {f"{r.ts_code} ({r['name']})": r.ts_code for _,r in df2.iterrows()}
    sel = st.sidebar.multiselect("匹配列表", options=list(options.keys()))
    stocks = [options[k] for k in sel]
else:
    codes = st.sidebar.text_input("或输入 TS 代码（逗号分隔）")
    stocks= [c.strip() for c in codes.split(",") if c.strip()]

current_year = pd.Timestamp.now().year
year_range   = st.sidebar.slider("最新期年份范围", 2000, current_year, (current_year-1,current_year))
# metrics_list = ["roe","netprofit_margin","assets_turn","debt_to_assets","grossprofit_margin"]
# hist_metrics = st.sidebar.multiselect("历史趋势指标", options=metrics_list, default=["roe","netprofit_margin"])
hist_year    = st.sidebar.slider("历史年份范围", 2000, current_year, (year_range[0]-5,year_range[1]))

# —— 分析
if st.sidebar.button("开始分析") and stocks:
    # 1) 最新指标表 & 并排柱状
    lst = []
    for code in stocks:
        df_all = fetch_all_data(code, year_range[0], year_range[1])
        lst.append(compute_indicators(df_all).rename("指标值").to_frame().T.assign(ts_code=code))
    df_latest = pd.concat(lst, ignore_index=True)
    st.subheader("最新一期指标")
    st.dataframe(df_latest.set_index("ts_code"))

    df_bar = df_latest.melt("ts_code", ["ROE (%)","净利率 (%)"], "指标","数值")
    st.altair_chart(
        alt.Chart(df_bar).mark_bar().encode(
            x="ts_code:N", y="数值:Q", color="指标:N", xOffset="指标:N"
        ), use_container_width=True
    )

    # 2) 股价时序
    # 2) 股价时序（用 Altair 画长表）
    price_list = []
    for code in stocks:
        pf = fetch_price(code, hist_year[0], hist_year[1])
        pf["ts_code"] = code
        price_list.append(pf[["trade_date","ts_code","close"]])
    df_price = pd.concat(price_list, ignore_index=True)

    # 转数值
    df_price["close"] = pd.to_numeric(df_price["close"], errors="coerce")

    # 画图
    st.subheader("股价走势")
    chart = (
        alt.Chart(df_price)
        .mark_line()
        .encode(
            x=alt.X("trade_date:T", title="交易日"),
            y=alt.Y("close:Q", title="收盘价"),
            color=alt.Color("ts_code:N", title="股票代码")
        )
)
    st.altair_chart(chart, use_container_width=True)

    

    # 3) 各分类能力：metric + 历史折线
    for code in stocks:
        st.markdown(f"### {code} —— 分类能力")
        df_all = fetch_all_data(code, hist_year[0], hist_year[1])
        # cf_df  = fetch_cash_flow(code, hist_year[0], hist_year[1])

        # 盈利能力
        prof = calc_profitability(df_all)
        cols = st.columns(len(prof))
        for (n,v),col in zip(prof.items(), cols):
            col.metric(n, f"{v:.2f}%", delta=None)
        st.markdown("**盈利能力历史趋势**")
        df_p = df_all[["end_date","grossprofit_margin","netprofit_margin","roe"]]
        df_p = df_p.rename(columns={
            "grossprofit_margin":"毛利率 (%)",
            "netprofit_margin":"净利率 (%)",
            "roe":"ROE (%)"
        }).set_index("end_date")
        st.line_chart(df_p)
        
        # 偿债能力
        # 新写法，直接用 df_all
        solv = calc_solvency(df_all)

        cols = st.columns(len(solv))
        for (n,v),col in zip(solv.items(), cols):
            col.metric(n, f"{v:.2f}" if v is not None else "N/A", delta=None)
        st.markdown("**偿债能力历史趋势**")
        df_s = df_all[["end_date", "current_ratio", "quick_ratio", "interst_income", "ebit"]].copy()
        df_s["利息保障倍数"] = df_s["ebit"] / df_s["interst_income"].abs().replace(0, pd.NA)
        df_s = df_s.rename(columns={
            "current_ratio": "流动比率",
            "quick_ratio": "速动比率",
            "interst_income": "利息费用"
        }).set_index("end_date")[["流动比率", "速动比率", "利息保障倍数"]]
        st.line_chart(df_s)

        # 成长性
        gr = calc_growth(df_all)
        cols = st.columns(len(gr))
        for (n,v),col in zip(gr.items(), cols):
            col.metric(n, f"{v:.2f}%", delta=None)
        st.markdown("**成长性历史趋势**")
        df_g = df_all[["end_date","or_yoy","netprofit_yoy","basic_eps_yoy"]]
        df_g = df_g.rename(columns={
            "or_yoy":"营收同比 (%)",
            "netprofit_yoy":"净利同比 (%)",
            "basic_eps_yoy":"EPS 同比 (%)"
        }).set_index("end_date")
        st.line_chart(df_g)

        # 运营能力
        op = calc_operating(df_all)
        cols = st.columns(len(op))
        for (n,v),col in zip(op.items(), cols):
            col.metric(n, f"{v:.2f}", delta=None)
        st.markdown("**运营能力历史趋势**")
        df_o = df_all[["end_date","inv_turn","ar_turn","assets_turn"]]
        df_o = df_o.rename(columns={
            "inv_turn":"存货周转率",
            "ar_turn":"应收账款周转率",
            "assets_turn":"总资产周转率"
        }).set_index("end_date")
        st.line_chart(df_o)

        # 造血能力
        cf = calc_cashflow(df_all) / 1e8
        cols = st.columns(len(cf))
        for (n,v),col in zip(cf.items(), cols):
            col.metric(n, f"{v:.2f} 亿元", delta=None)
        st.markdown("**造血能力历史趋势**")
        df_cf = df_all[["end_date","fcff","fcfe"]]
        df_cf = df_cf.rename(columns={"fcff":"FCFF (元)","fcfe":"FCFE (元)"}).set_index("end_date")
        st.line_chart(df_cf/1e8)