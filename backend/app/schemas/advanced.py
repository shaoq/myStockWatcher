"""
高级数据 Schema 定义

包含财报、估值指标、宏观经济等高级数据的请求和响应模型。
"""

from typing import Optional, Dict, List, Any
from datetime import date, datetime
from pydantic import BaseModel, Field


# ============ 财报数据 Schema ============

class FinancialReportRequest(BaseModel):
    """财报数据请求参数"""
    report_type: str = Field(
        default="balance_sheet",
        description="报告类型: balance_sheet, income, cash_flow"
    )
    period: str = Field(
        default="quarterly",
        description="周期: annual (年度), quarterly (季度)"
    )


class FinancialReportData(BaseModel):
    """财报数据"""
    total_assets: Optional[float] = Field(None, description="总资产")
    total_liabilities: Optional[float] = Field(None, description="总负债")
    total_equity: Optional[float] = Field(None, description="股东权益")
    current_assets: Optional[float] = Field(None, description="流动资产")
    current_liabilities: Optional[float] = Field(None, description="流动负债")
    revenue: Optional[float] = Field(None, description="营业收入")
    net_income: Optional[float] = Field(None, description="净利润")
    earnings_per_share: Optional[float] = Field(None, description="每股收益")
    operating_cash_flow: Optional[float] = Field(None, description="经营活动现金流")
    investing_cash_flow: Optional[float] = Field(None, description="投资活动现金流")
    financing_cash_flow: Optional[float] = Field(None, description="筹资活动现金流")
    gross_profit: Optional[float] = Field(None, description="毛利润")
    operating_income: Optional[float] = Field(None, description="营业利润")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class FinancialReportResponse(BaseModel):
    """财报数据响应"""
    symbol: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    report_type: str = Field(..., description="报告类型")
    period: str = Field(..., description="报告周期")
    report_date: Optional[date] = Field(None, description="报告日期")
    data: FinancialReportData = Field(..., description="财报数据")
    source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(..., description="数据获取时间")
    is_cached: bool = Field(default=False, description="是否来自缓存")


# ============ 估值指标 Schema ============

class ValuationMetricsRequest(BaseModel):
    """估值指标请求参数"""
    include_industry_avg: bool = Field(
        default=False,
        description="是否包含行业均值"
    )


class ValuationMetricsData(BaseModel):
    """估值指标数据"""
    pe_ratio: Optional[float] = Field(None, description="市盈率 (P/E)")
    pb_ratio: Optional[float] = Field(None, description="市净率 (P/B)")
    ps_ratio: Optional[float] = Field(None, description="市销率 (P/S)")
    roe: Optional[float] = Field(None, description="净资产收益率 (ROE)")
    roa: Optional[float] = Field(None, description="总资产收益率 (ROA)")
    revenue_growth: Optional[float] = Field(None, description="营收增长率 (YoY)")
    profit_margin: Optional[float] = Field(None, description="净利润率")
    gross_margin: Optional[float] = Field(None, description="毛利率")
    debt_to_equity: Optional[float] = Field(None, description="负债权益比")
    current_ratio: Optional[float] = Field(None, description="流动比率")
    dividend_yield: Optional[float] = Field(None, description="股息率")
    eps: Optional[float] = Field(None, description="每股收益 (EPS)")
    book_value_per_share: Optional[float] = Field(None, description="每股净资产")


class IndustryAverages(BaseModel):
    """行业均值数据"""
    pe_ratio: Optional[float] = Field(None, description="行业平均市盈率")
    pb_ratio: Optional[float] = Field(None, description="行业平均市净率")
    roe: Optional[float] = Field(None, description="行业平均ROE")
    profit_margin: Optional[float] = Field(None, description="行业平均利润率")


class ValuationMetricsResponse(BaseModel):
    """估值指标响应"""
    symbol: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    current_price: Optional[float] = Field(None, description="当前股价")
    metrics: ValuationMetricsData = Field(..., description="估值指标")
    industry_avg: Optional[IndustryAverages] = Field(None, description="行业均值")
    source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(..., description="数据获取时间")
    is_cached: bool = Field(default=False, description="是否来自缓存")


# ============ 宏观指标 Schema ============

class MacroIndicatorsRequest(BaseModel):
    """宏观指标请求参数"""
    market: str = Field(default="cn", description="市场: cn (中国), us (美国)")
    indicators: List[str] = Field(
        default=["gdp", "cpi", "interest_rate"],
        description="指标列表: gdp, cpi, interest_rate, unemployment, etc."
    )


class MacroIndicatorValue(BaseModel):
    """单个宏观指标值"""
    name: str = Field(..., description="指标名称")
    value: Optional[float] = Field(None, description="指标值")
    unit: Optional[str] = Field(None, description="单位")
    change: Optional[float] = Field(None, description="变化率")
    period: Optional[str] = Field(None, description="数据周期")
    last_updated: Optional[date] = Field(None, description="最后更新日期")


class MacroIndicatorsResponse(BaseModel):
    """宏观指标响应"""
    market: str = Field(..., description="市场")
    indicators: List[MacroIndicatorValue] = Field(..., description="指标列表")
    source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(..., description="数据获取时间")
    is_cached: bool = Field(default=False, description="是否来自缓存")


# ============ 错误响应 Schema ============

class AdvancedDataErrorResponse(BaseModel):
    """高级数据错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    symbol: Optional[str] = Field(None, description="相关股票代码")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")
    supported_capabilities: Optional[List[str]] = Field(
        None,
        description="支持的能力列表（当能力不可用时返回）"
    )
