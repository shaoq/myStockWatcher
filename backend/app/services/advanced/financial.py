"""
财报数据服务

提供财报数据获取、缓存等功能。
"""

import logging
from typing import Optional, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

from ...providers import get_coordinator
from ...schemas.advanced import (
    FinancialReportResponse,
    FinancialReportData,
    AdvancedDataErrorResponse,
)

logger = logging.getLogger(__name__)


def get_financial_report(
    symbol: str,
    normalized_code: str,
    market: str,
    name: Optional[str],
    report_type: str = "balance_sheet",
    period: str = "quarterly",
    use_cache: bool = True
) -> Dict:
    """
    获取财报数据

    Args:
        symbol: 原始股票代码
        normalized_code: 规范化后的代码
        market: 市场类型
        name: 股票名称
        report_type: 报告类型 (balance_sheet, income, cash_flow)
        period: 周期 (annual, quarterly)
        use_cache: 是否使用缓存

    Returns:
        Dict: 财报数据响应或错误响应
    """
    from .. import financial_report_cache

    # 检查缓存
    cache_key = f"{symbol}:{report_type}:{period}"
    if use_cache and cache_key in financial_report_cache:
        logger.info(f"[财报服务] 缓存命中 | 股票: {symbol} | 类型: {report_type}")
        cached = financial_report_cache[cache_key]
        cached["is_cached"] = True
        return cached

    # 获取数据
    coordinator = get_coordinator()
    data, provider_name = coordinator.get_financial_report(
        symbol, normalized_code, market, report_type, period
    )

    if data is None:
        return {
            "error": "financial_data_unavailable",
            "message": "财报数据获取失败，请稍后重试",
            "symbol": symbol,
            "details": {
                "report_type": report_type,
                "period": period,
            }
        }

    # 构建响应
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    report_date = data.get("report_date")

    # 提取财务数据
    financial_data = FinancialReportData(
        total_assets=data.get("total_assets"),
        total_liabilities=data.get("total_liabilities"),
        total_equity=data.get("total_equity"),
        current_assets=data.get("current_assets"),
        current_liabilities=data.get("current_liabilities"),
        revenue=data.get("revenue"),
        net_income=data.get("net_income"),
        earnings_per_share=data.get("earnings_per_share"),
        operating_cash_flow=data.get("operating_cash_flow"),
        investing_cash_flow=data.get("investing_cash_flow"),
        financing_cash_flow=data.get("financing_cash_flow"),
        gross_profit=data.get("gross_profit"),
        operating_income=data.get("operating_income"),
        raw_data=data.get("raw_data"),
    )

    response = {
        "symbol": symbol,
        "name": name,
        "report_type": report_type,
        "period": period,
        "report_date": report_date,
        "data": financial_data.model_dump(),
        "source": provider_name,
        "fetched_at": now.isoformat(),
        "is_cached": False,
    }

    # 存入缓存
    financial_report_cache[cache_key] = response
    logger.info(f"[财报服务] 数据获取成功 | 股票: {symbol} | 类型: {report_type} | 数据源: {provider_name}")

    return response
