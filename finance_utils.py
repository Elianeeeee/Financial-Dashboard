import tushare as ts
import pandas as pd
import streamlit as st

# 从 secrets.toml 里取
token = st.secrets["tushare"]["token"]
ts.set_token(token)
pro = ts.pro_api()

def fetch_financials(ts_code: str, start_year: int, end_year: int) -> pd.DataFrame:
    df = pro.fina_indicator(
        ts_code=ts_code,
        start_date=f"{start_year}0101",
        end_date=f"{end_year}1231"
    )
    return df

def compute_indicators(df: pd.DataFrame) -> pd.Series:
    df = df.sort_values("end_date").reset_index(drop=True)
    latest = df.iloc[-1]

    return pd.Series({
        "ROE (%)":            latest.get("roe",    0) * 100,
        "毛利率 (%)":         latest.get("grossprofit_margin", 0) * 100,
        "净利率 (%)":         latest.get("netprofit_margin",   0) * 100,
        "流动比率":           latest.get("current_ratio",      None),
        "速动比率":           latest.get("quick_ratio",        None),
        # 直接用接口提供的同比增长率字段
        "营业收入同比增长率 (%)": latest.get("or_yoy", None)
    })