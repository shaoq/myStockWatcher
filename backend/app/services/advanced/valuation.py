"""
估值指标服务

提供估值指标获取、缓存等功能。
"""

import logging
from typing import Optional, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

from ...providers import get_coordinator
from ...schemas.advanced import (
    ValuationMetricsResponse,
    ValuationMetricsData,
)

logger = logging.getLogger(__name__)


def get_valuation_metrics(
    symbol: str,
    normalized_code: str,
    market: str,
    name: Optional[str],
    current_price: Optional[float] = None,
    use_cache: bool = True
) -> Dict:
    """
    获取估值指标

    Args:
        symbol: 原始股票代码
        normalized_code: 规范化后的代码
        market: 市场类型
        name: 股票名称
        current_price: 当前价格（可选）
        use_cache: 是否使用缓存

    Returns:
        Dict: 估值指标响应或错误响应
    """
    from .. import valuation_cache

    # 检查缓存
    cache_key = f"{symbol}:valuation"
    if use_cache and cache_key in valuation_cache:
        logger.info(f"[估值服务] 缓存命中 | 股票: {symbol}")
        cached = valuation_cache[cache_key]
        cached["is_cached"] = True
        return cached

    # 获取数据
    coordinator = get_coordinator()
    data, provider_name = coordinator.get_valuation_metrics(
        symbol, normalized_code, market
    )

    if data is None:
        return {
            "error": "valuation_data_unavailable",
            "message": "估值指标获取失败，请稍后重试",
            "symbol": symbol,
        }

    # 构建响应
    now = datetime.now(ZoneInfo("Asia/Shanghai"))

    # 提取估值指标
    metrics_data = ValuationMetricsData(
        pe_ratio=data.get("pe_ratio"),
        pb_ratio=data.get("pb_ratio"),
        ps_ratio=data.get("ps_ratio"),
        roe=data.get("roe"),
        roa=data.get("roa"),
        revenue_growth=data.get("revenue_growth"),
        profit_margin=data.get("profit_margin"),
        gross_margin=data.get("gross_margin"),
        debt_to_equity=data.get("debt_to_equity"),
        current_ratio=data.get("current_ratio"),
        dividend_yield=data.get("dividend_yield"),
        eps=data.get("eps"),
        book_value_per_share=data.get("book_value_per_share"),
    )

    response = {
        "symbol": symbol,
        "name": name,
        "current_price": current_price,
        "metrics": metrics_data.model_dump(),
        "industry_avg": None,  # 暂不支持行业均值
        "source": provider_name,
        "fetched_at": now.isoformat(),
        "is_cached": False,
    }

    # 存入缓存
    valuation_cache[cache_key] = response
    logger.info(f"[估值服务] 数据获取成功 | 股票: {symbol} | 数据源: {provider_name}")

    return response
