import tushare as ts
import pandas as pd
import streamlit as st
from functools import reduce
import google.generativeai as genai

# 从 secrets.toml 里取
token = st.secrets["tushare"]["token"]
ts.set_token(token)
pro = ts.pro_api()


@st.cache_data(show_spinner=False)
def lookup_stock_basic() -> pd.DataFrame:
    """
    返回所有在市上市公司的基础表，包含 ts_code, name, industry列。
    """
    df = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,name,industry"
    )
    return df



@st.cache_data(show_spinner="正在拉取行业所有公司数据...")
def fetch_full_industry_data(industry: str, period: str) -> pd.DataFrame:
    """
    获取指定行业在特定报告期的所有公司的完整财务和估值指标。(超详细日志版)
    """
    try:
        print("\n" + "="*80)
        print(f"--- [LOG] 进入 fetch_full_industry_data: 行业='{industry}', 报告期='{period}' ---")

        # 1. 获取行业所有股票代码
        print("--- [LOG] 步骤1: 调用 pro.stock_basic 获取行业股票列表...")
        basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name,industry")
        industry_stocks = basic[basic["industry"] == industry]
        if industry_stocks.empty:
            print("--- [LOG] 结果: 失败！在此行业中找不到任何股票。函数提前返回。")
            print("="*80 + "\n")
            return pd.DataFrame()
        codes_str = ",".join(industry_stocks["ts_code"])
        print(f"--- [LOG] 结果: 成功找到 {len(industry_stocks)} 只股票。")

        # 2. 一次性获取所有财务指标
        fina_fields = ("ts_code,netprofit_margin,grossprofit_margin,roe,current_ratio,quick_ratio,"
                       "debt_to_assets,inv_turn,ar_turn,assets_turn,or_yoy,netprofit_yoy,fcff,fcfe")
        print(f"--- [LOG] 步骤2: 调用 pro.fina_indicator, 报告期='{period}'...")
        industry_fina_df = pro.fina_indicator(ts_code=codes_str, period=period, fields=fina_fields)
        if industry_fina_df.empty:
            print(f"--- [LOG] 结果: 失败！pro.fina_indicator 为报告期 '{period}' 返回了空的数据集。")
            # 即使这里失败，我们仍然尝试返回空DF，让上层逻辑继续
        else:
            print(f"--- [LOG] 结果: 成功获取到 {len(industry_fina_df)} 条财务指标数据。")

        # 如果核心的财务数据为空，直接返回，不再继续
        if industry_fina_df.empty:
            print("--- [LOG] 核心财务数据为空，函数提前返回。")
            print("="*80 + "\n")
            return pd.DataFrame()

        # 3. 一次性获取所有估值指标
        trade_date = period
        print(f"--- [LOG] 步骤3: 调用 pro.daily_basic, 交易日(同报告期)='{trade_date}'...")
        industry_pe_df = pro.daily_basic(trade_date=trade_date, ts_code=codes_str, fields="ts_code,pe,pb")
        if industry_pe_df.empty:
            print("--- [LOG] 结果: 注意，pro.daily_basic 返回了空的估值数据集。")
        else:
            print(f"--- [LOG] 结果: 成功获取到 {len(industry_pe_df)} 条估值数据。")

        # 4. 合并数据
        print("--- [LOG] 步骤4: 合并数据...")
        merged = pd.merge(industry_stocks, industry_fina_df, on="ts_code", how="inner")
        print(f"--- [LOG] ...合并财务数据后，大小: {merged.shape}")
        if not industry_pe_df.empty:
            merged = pd.merge(merged, industry_pe_df, on="ts_code", how="left")
            print(f"--- [LOG] ...合并估值数据后，大小: {merged.shape}")

        print("--- [LOG] 函数执行完毕，返回最终数据。")
        print("="*80 + "\n")
        return merged.reset_index(drop=True)

    except Exception as e:
        print(f"\n!!!!!! [FATAL ERROR] 在 fetch_full_industry_data 中发生未知异常 !!!!!!")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        return pd.DataFrame()

    # --- BUG修复：动态检查列是否存在 ---
    cols_to_check = ['roe', 'netprofit_margin']
    existing_cols = [col for col in cols_to_check if col in merged.columns]

    # 如果要检查的关键列一个都不存在，就没法做有效清理，直接返回原始合并数据
    if not existing_cols:
        print(f"[调试 finance_utils] 警告：关键列 {cols_to_check} 均不存在，无法进行有效清理，将返回原始合并数据。")
        return merged

    # 只在存在的关键列上进行dropna操作
    print(f"[调试 finance_utils] 将在存在的关键列 {existing_cols} 上进行dropna操作。")
    final_df = merged.dropna(subset=existing_cols).reset_index(drop=True)
    
    print(f"[调试 finance_utils] 清理空值后，最终返回的数据表大小: {final_df.shape}")
    print("[调试 finance_utils] 数据获取流程结束。\n")
    return final_df


@st.cache_data(show_spinner=False)
def fetch_all_data(ts_code: str, start: int, end: int) -> pd.DataFrame:
    """
    一次性拉取所需的所有字段...
    """
    fields = ",".join([
        "ts_code","end_date","current_ratio","quick_ratio",
        "debt_to_assets",  # <--- 确认这一项存在！
        "interst_income", 
        "ebit","grossprofit_margin","netprofit_margin","roe","or_yoy",
        "netprofit_yoy","basic_eps_yoy","inv_turn","ar_turn","assets_turn",
        "fcff","fcfe"
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

@st.cache_data(show_spinner="AI正在分析，请稍候...")
def get_ai_analysis(company_name: str, data_summary: str) -> str:
    """
    调用Gemini模型，对输入的公司数据摘要进行分析。
    """
    # 从secrets.toml中安全地获取API密钥
    try:
        api_key = st.secrets["google_ai"]["api_key"]
        genai.configure(api_key=api_key)
    except (KeyError, FileNotFoundError):
        return "错误：未找到Google AI的API密钥。请在.streamlit/secrets.toml中配置。"

    # 创建模型实例
    model = genai.GenerativeModel('gemini-2.0-flash') # 使用最新、速度最快的Flash模型

    # --- 这是最关键的部分：构建高质量的提示词 (Prompt) ---
    prompt = f"""
    请你扮演一位专业的金融分析师。我将为你提供一家上市公司“{company_name}”的核心财务数据和行业对标情况，请你基于这些数据，给出一份简明扼要、有洞察力的分析报告。

    你的分析需要包含以下几个方面，并以清晰的要点形式呈现：
    1.  **总体评价**: 基于所有数据，对该公司的整体财务状况给出一个总体的定性评价（例如：财务状况健康、盈利能力强劲但成长性放缓、高风险高成长型等）。
    2.  **亮点分析**: 指出该公司最突出的1-2个优点。请结合具体数据进行说明（例如：其ROE高达25%，远超行业平均水平，显示出卓越的股东回报能力）。
    3.  **风险提示**: 指出该公司最值得关注的1-2个潜在风险或弱点。请结合具体数据进行说明（例如：其资产负债率达到75%，显著高于行业均值，偿债压力较大）。
    4.  **总结与展望**: 对公司的未来发展给出一个简短的总结和展望。

    以下是需要你分析的原始数据：
    ---
    {data_summary}
    ---
    请严格基于以上数据进行分析，不要编造数据之外的信息。
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"调用AI模型时发生错误: {e}"

@st.cache_data(show_spinner="AI正在分析股价走势，请稍候...")
def get_ai_price_chart_analysis(chart_data_summary: str) -> str:
    """
    调用Gemini模型，对输入的一段或多段股价时间序列数据进行分析解读。
    """
    try:
        api_key = st.secrets["google_ai"]["api_key"]
        genai.configure(api_key=api_key)
    except (KeyError, FileNotFoundError):
        return "错误：未找到Google AI的API密钥。请在.streamlit/secrets.toml中配置。"

    model = genai.GenerativeModel('gemini-2.0-flash')

    # --- 专为图表分析设计的提示词 ---
    prompt = f"""
    请你扮演一位专业的图表分析师和市场评论员。我将为你提供一只或多只股票在一段时间内的价格走势数据。请你分析这些数据并给出一份简明的趋势解读报告。

    你的分析应包括：
    1.  **总体趋势**: 描述每只股票在整个时间段内的主要趋势（例如：震荡上行、长期盘整后突破、稳定下跌等）。
    2.  **波动性**: 评价股价的波动程度（例如：波动剧烈，换手率高，或走势相对平稳）。
    3.  **关键节点**: 如果有的话，指出明显的波峰或波谷，并描述其发生的大致时间（例如：“股价在2023年底达到阶段性高点后开始回调”）。
    4.  **对比分析 (如果有多只股票)**: 这是分析的重点。请比较不同股票的表现。谁的涨幅更大？谁更稳定？它们之间是否存在相关性（比如走势趋同或背离）？

    以下是需要你分析的股价数据（已按月度采样，格式为“月份: 月末收盘价”）：
    ---
    {chart_data_summary}
    ---
    请基于以上数据进行解读，语言风格要像专业的财经评论员，分析需客观、有条理。
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"调用AI模型时发生错误: {e}"

@st.cache_data(show_spinner="正在获取三大报表数据...")
def fetch_accounting_data(ts_code: str, start_year: int, end_year: int) -> pd.DataFrame:
    """
    获取指定公司在给定年份范围内的三大报表关键数据，并合并成一张宽表。
    """
    start_date = f"{start_year}0101"
    end_date = f"{end_year}1231"
    
    try:
        # 1. 获取利润表关键字段
        income_fields = "ts_code,end_date,revenue,oper_exp,ebit,n_income"
        income_df = pro.income(ts_code=ts_code, start_date=start_date, end_date=end_date, fields=income_fields)

        # 2. 获取资产负债表关键字段
        balance_fields = "ts_code,end_date,total_assets,total_liab,accounts_receiv,inventories"
        balance_df = pro.balancesheet(ts_code=ts_code, start_date=start_date, end_date=end_date, fields=balance_fields)

        # 3. 获取现金流量表关键字段
        cashflow_fields = "ts_code,end_date,n_cashflow_act"
        cashflow_df = pro.cashflow(ts_code=ts_code, start_date=start_date, end_date=end_date, fields=cashflow_fields)

        # 将所有数据表放入一个列表
        data_frames = [income_df, balance_df, cashflow_df]
        
        # 过滤掉空的DataFrame
        data_frames = [df for df in data_frames if not df.empty]
        
        if not data_frames:
            return pd.DataFrame()

        # 4. 使用reduce和merge将所有表基于ts_code和end_date合并
        # on-=['ts_code', 'end_date'] 确保基于股票代码和报告日期精确匹配
        # how='outer' 确保即使某个报告期在某张表中缺失，也不会丢失其他表的数据
        df_merged = reduce(lambda left, right: pd.merge(left, right, on=['ts_code', 'end_date'], how='outer'), data_frames)
        
        # 按日期排序并处理重复值
        df_merged['end_date'] = pd.to_datetime(df_merged['end_date'], format="%Y%m%d")
        df_merged = df_merged.sort_values("end_date").drop_duplicates("end_date", keep="last").reset_index(drop=True)
        
        return df_merged
        
    except Exception as e:
        st.error(f"获取三大报表数据时发生错误: {e}")
        return pd.DataFrame()
@st.cache_data(show_spinner="AI正在分析，请稍候...")
def get_ai_response(prompt: str) -> str:
    """
    一个通用的函数，接收一个完整的prompt，并调用Gemini模型返回结果。
    """
    # 从secrets.toml中安全地获取API密钥
    try:
        api_key = st.secrets["google_ai"]["api_key"]
        genai.configure(api_key=api_key)
    except (KeyError, FileNotFoundError):
        return "错误：未找到Google AI的API密钥。请在.streamlit/secrets.toml中配置。"

    # 创建模型实例 (gemini-1.5-flash 是一个真实存在的、速度很快的模型)
    model = genai.GenerativeModel('gemini-2.0-flash')

    try:
        response = model.generate_content(prompt)
        # 增加对安全设置导致返回内容为空的处理
        if not response.parts:
            return "AI模型因为安全设置阻止了本次回复。这通常是因为Prompt或返回内容中可能包含了敏感信息。请尝试调整问题或检查数据。"
        return response.text
    except Exception as e:
        return f"调用AI模型时发生错误: {e}"