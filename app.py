import streamlit as st
import pandas as pd
from finance_utils import fetch_financials, compute_indicators
import altair as alt

st.title("📊 财务指标一键分析")

# —— 侧边栏控件，用户可以选股票和年份
st.sidebar.header("参数设置")
stocks = st.sidebar.multiselect("选择股票代码", 
                                options=["000001.SZ","600519.SH","000651.SZ"],
                                default=["600519.SH"])
year_range = st.sidebar.slider("年份区间", 2018, 2024, (2022, 2023))

# —— 缓存抓数和计算，避免重复请求
@st.cache_data(show_spinner=False)
def load_and_compute(ts_codes, start, end):
    results = []
    for code in ts_codes:
        df = fetch_financials(code, start, end)
        inds = compute_indicators(df)
        inds["ts_code"] = code
        results.append(inds)
    return pd.DataFrame(results)

# —— 主区：当用户点击按钮时才运行
if st.sidebar.button("开始分析"):
    with st.spinner("正在抓数据并计算指标..."):
        df_res = load_and_compute(stocks, year_range[0], year_range[1])
    st.success("完成！")
    st.dataframe(df_res.set_index("ts_code"))

    # 简单画个柱状图
    df_plot = df_res.melt(
    id_vars="ts_code",
    value_vars=["ROE (%)", "净利率 (%)"],
    var_name="指标",
    value_name="数值"
    )

    chart = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("ts_code:N", title="股票代码"),
            y=alt.Y("数值:Q", title="百分比 (%)"),
            color="指标:N",
            xOffset="指标:N"   # 关键：并排分组
        )
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("在左侧设定参数后，点击“开始分析”")