import tushare as ts
import pandas as pd
import streamlit as st

# 从 secrets.toml 里取
token = st.secrets["tushare"]["token"]
ts.set_token(token)
pro = ts.pro_api()

# @st.cache_data
# def lookup_ts_codes(name: str) -> list[str]:
#     """用 pro.stock_basic 按公司名模糊搜索，返回 ts_code 列表"""
#     df = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name")
#     # 简单模糊匹配
#     df2 = df[df["name"].str.contains(name, na=False)]
#     return df2["ts_code"].tolist()

# def fetch_financials(ts_code: str, start: int, end: int) -> pd.DataFrame:
#     return pro.fina_indicator(
#         ts_code=ts_code,
#         start_date=f"{start}0101",
#         end_date=f"{end}1231"
#     ).sort_values("end_date") 

# def compute_indicators(df: pd.DataFrame) -> pd.Series:
#     df = df.sort_values("end_date").reset_index(drop=True)
#     latest = df.iloc[-1]

#     return pd.Series({
#         "ROE (%)":            latest.get("roe",    0),
#         "毛利率 (%)":         latest.get("grossprofit_margin", 0),
#         "净利率 (%)":         latest.get("netprofit_margin",   0),
#         "流动比率":           latest.get("current_ratio",      None),
#         "速动比率":           latest.get("quick_ratio",        None),
#         # 直接用接口提供的同比增长率字段
#         "营业收入同比增长率 (%)": latest.get("or_yoy", None)
#     })

# def dupont(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     DuPont: ROE = 净利率 * 总资产周转率 * 权益乘数
#     """
#     df = df.copy().sort_values("end_date")

#     # 1）安全取列
#     netprofit = df.get("netprofit_margin")     # 净利率
#     asset_turn = df.get("assets_turn")         # 总资产周转率
#     equity_mul = df.get("assets_to_eqt")       # 权益乘数

#     # 2）生成拆解列
#     df["净利率"]     = netprofit
#     df["资产周转率"] = asset_turn
#     df["权益乘数"]   = equity_mul
#     df["ROE_拆解"]   = netprofit * asset_turn * equity_mul

#     # 3）只返回我们要画图的几列
#     return df[["end_date", "ROE_拆解", "净利率", "资产周转率", "权益乘数"]]

# def lookup_stock_basic() -> pd.DataFrame:
#     """
#     返回所有在市上市公司的基础表，包含 ts_code 和 name 两列。
#     """
#     df = pro.stock_basic(
#         exchange="",
#         list_status="L",
#         fields="ts_code,name"
#     )
#     return df

@st.cache_data(show_spinner=False)
def lookup_stock_basic() -> pd.DataFrame:
    """
    返回所有在市上市公司的基础表，包含 ts_code 和 name 两列。
    """
    df = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,name"
    )
    return df

# @st.cache_data(show_spinner=False)
# def fetch_all_data(ts_code: str, start: int, end: int) -> pd.DataFrame:
#     """
#     一次性拉取指定 ts_code 在 [start,end] 年度的 fina_indicator 数据，
#     转成日期，并 drop 重复报告期。
#     """
#     df = pro.fina_indicator(
#         ts_code=ts_code,
#         start_date=f"{start}0101",
#         end_date=f"{end}1231"
#     ).sort_values("end_date")
#     df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d")
#     return df.drop_duplicates(subset="end_date", keep="last").reset_index(drop=True)

# def fetch_all_data(ts_code: str, start: int, end: int) -> pd.DataFrame:
#     """
#     一次性拉取 fina_indicator，包含：
#     - current_ratio, quick_ratio, interst_income, ebit
#     - 以及我们后续要画各类趋势的所有字段
#     """
#     df = pro.fina_indicator(
#         ts_code=ts_code,
#         start_date=f"{start}0101",
#         end_date=f"{end}1231",
#         # 多拉几个常用的字段
#         fields="ts_code, end_date, current_ratio, quick_ratio, interst_income, ebit, "
#                "grossprofit_margin, netprofit_margin, roe, or_yoy, netprofit_yoy, basic_eps_yoy, "
#                "inv_turn, ar_turn, assets_turn, fcff, fcfe"
#     ).sort_values("end_date")
#     df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d")
#     return df.drop_duplicates("end_date", keep="last").reset_index(drop=True)

@st.cache_data(show_spinner=False)
def fetch_all_data(ts_code: str, start: int, end: int) -> pd.DataFrame:
    """
    一次性拉取所需的所有字段，包括 interst_income（财务费用）和后续要画趋势的常用指标。
    """
    fields = ",".join([
        "ts_code",
        "end_date",
        "current_ratio",
        "quick_ratio",
        "interst_income",    # <-- 把它加进来
        "ebit",
        "grossprofit_margin",
        "netprofit_margin",
        "roe",
        "or_yoy",
        "netprofit_yoy",
        "basic_eps_yoy",
        "inv_turn",
        "ar_turn",
        "assets_turn",
        "fcff",
        "fcfe"
    ])

    df = pro.fina_indicator(
        ts_code=ts_code,
        start_date=f"{start}0101",
        end_date=f"{end}1231",
        fields=fields
    ).sort_values("end_date")

    df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d")
    return df.drop_duplicates("end_date", keep="last").reset_index(drop=True)

@st.cache_data
# def fetch_cash_flow(ts_code, start, end):
#     df = pro.cashflow(
#         ts_code=ts_code,
#         start_date=f"{start}0101",
#         end_date=f"{end}1231",
#         fields="ts_code,end_date,interest_paid,ebit"
#     )
#     df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d")
#     return df.drop_duplicates("end_date", keep="last")
def fetch_cash_flow(ts_code: str, start: int, end: int) -> pd.DataFrame:
    """抓取现金流表，获取 interest_paid，用于利息保障倍数"""
    df = pro.cashflow(
        ts_code=ts_code,
        start_date=f"{start}0101",
        end_date=f"{end}1231",
        fields="ts_code,end_date,interest_paid"
    ).sort_values("end_date")
    df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d")
    return df.drop_duplicates("end_date", keep="last").reset_index(drop=True)

@st.cache_data
def fetch_price(ts_code: str, start: int, end: int) -> pd.DataFrame:
    """抓取日线收盘价，用于股价时序图"""
    df = pro.daily(
        ts_code=ts_code,
        start_date=f"{start}0101",
        end_date=f"{end}1231",
        fields="trade_date,close"
    ).sort_values("trade_date")
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    return df.drop_duplicates("trade_date", keep="last").reset_index(drop=True)

def compute_indicators(df: pd.DataFrame) -> pd.Series:
    """
    提取最新一期的常用财务指标：ROE、毛利率、净利率、流动比率、速动比率、营收同比
    """
    latest = df.iloc[-1]
    return pd.Series({
        "ROE (%)":               latest.get("roe"),
        "毛利率 (%)":            latest.get("grossprofit_margin"),
        "净利率 (%)":            latest.get("netprofit_margin"),
        "流动比率":              latest.get("current_ratio"),
        "速动比率":              latest.get("quick_ratio"),
        "营业收入同比增长率 (%)": latest.get("or_yoy")
    })

def dupont(df: pd.DataFrame) -> pd.DataFrame:
    """
    DuPont: ROE = 净利率 * 总资产周转率 * 权益乘数
    """
    df2 = df.copy().sort_values("end_date")
    netprofit  = df2.get("netprofit_margin")
    asset_turn = df2.get("assets_turn")
    equity_mul = df2.get("assets_to_eqt")
    df2["净利率"]     = netprofit
    df2["资产周转率"] = asset_turn
    df2["权益乘数"]   = equity_mul
    df2["ROE_拆解"]   = netprofit * asset_turn * equity_mul
    return df2[["end_date", "ROE_拆解", "净利率", "资产周转率", "权益乘数"]]

def calc_profitability(df: pd.DataFrame) -> pd.Series:
    """盈利能力：毛利率、净利率、ROE"""
    latest = df.iloc[-1]
    return pd.Series({
        "毛利率 (%)": latest.get("grossprofit_margin"),
        "净利率 (%)": latest.get("netprofit_margin"),
        "ROE (%)":     latest.get("roe")
    })


# def calc_solvency(df: pd.DataFrame, cf_df: pd.DataFrame) -> pd.Series:
#     """
#     偿债能力：流动比率、速动比率、利息保障倍数(EBIT/interest_paid)
#     """
#     latest = df.iloc[-1]
#     cf_latest = cf_df.iloc[-1]
#     ebit = latest.get("ebit", None)
#     ipaid = cf_latest.get("interest_paid", None)
#     ib = None
#     if ipaid not in (None, 0) and ebit is not None:
#         ib = ebit / ipaid
#     return pd.Series({
#         "流动比率":     latest.get("current_ratio"),
#         "速动比率":     latest.get("quick_ratio"),
#         "利息保障倍数": ib
#     })

def calc_solvency(df: pd.DataFrame) -> pd.Series:
    """
    偿债能力：直接从同一份 df 里取：
    - 流动比率 current_ratio
    - 速动比率 quick_ratio
    - 利息保障倍数 = EBIT / 利息费用(interst_income)
    """
    latest = df.iloc[-1]
    ebit = latest.get("ebit")
    interest = latest.get("interst_income")  # 注意是 interst_income 而不是 interest_paid
    ib = None
    if ebit is not None and interest not in (None, 0):
        ib = ebit / abs(interest)  # 取绝对值保证正负合规
    return pd.Series({
        "流动比率":     latest.get("current_ratio"),
        "速动比率":     latest.get("quick_ratio"),
        "利息保障倍数": ib
    })

def calc_growth(df: pd.DataFrame) -> pd.Series:
    """成长性：营业收入同比、净利润同比、每股收益同比"""
    latest = df.iloc[-1]
    return pd.Series({
        "营收同比 (%)": latest.get("or_yoy"),
        "净利同比 (%)": latest.get("netprofit_yoy"),
        "EPS 同比 (%)": latest.get("basic_eps_yoy")
    })

def calc_operating(df: pd.DataFrame) -> pd.Series:
    """运营能力：存货周转率、应收账款周转率、总资产周转率"""
    latest = df.iloc[-1]
    return pd.Series({
        "存货周转率":     latest.get("inv_turn"),
        "应收账款周转率": latest.get("ar_turn"),
        "总资产周转率":   latest.get("assets_turn")
    })

def calc_cashflow(df: pd.DataFrame) -> pd.Series:
    """造血能力：企业自由现金流FCFF、股权自由现金流FCFE"""
    latest = df.iloc[-1]
    return pd.Series({
        "FCFF": latest.get("fcff"),
        "FCFE": latest.get("fcfe")
    })

