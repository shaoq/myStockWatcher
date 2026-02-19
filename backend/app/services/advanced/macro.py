"""
宏观经济指标服务

提供宏观经济指标获取、缓存等功能。
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from zoneinfo import ZoneInfo

from ...providers import get_coordinator
from ...schemas.advanced import (
    MacroIndicatorsResponse,
    MacroIndicatorValue,
)

logger = logging.getLogger(__name__)


def get_macro_indicators(
    market: str = "cn",
    indicators: Optional[List[str]] = None,
    use_cache: bool = True
) -> Dict:
    """
    获取宏观经济指标

    Args:
        market: 市场类型 (cn, us)
        indicators: 指标列表
        use_cache: 是否使用缓存

    Returns:
        Dict: 宏观指标响应或错误响应
    """
    from .. import macro_cache

    if indicators is None:
        indicators = ["gdp", "cpi", "interest_rate"]

    # 检查缓存
    cache_key = f"{market}:{','.join(sorted(indicators))}"
    if use_cache and cache_key in macro_cache:
        logger.info(f"[宏观服务] 缓存命中 | 市场: {market}")
        cached = macro_cache[cache_key]
        cached["is_cached"] = True
        return cached

    # 获取数据
    coordinator = get_coordinator()
    data, provider_name = coordinator.get_macro_indicators(market, indicators)

    if data is None:
        return {
            "error": "macro_data_unavailable",
            "message": "宏观指标获取失败，请稍后重试",
            "market": market,
            "supported_indicators": ["gdp", "cpi", "interest_rate"],
        }

    # 构建响应
    now = datetime.now(ZoneInfo("Asia/Shanghai"))

    # 转换指标列表
    indicator_list = []
    for ind_name, ind_data in data.items():
        if isinstance(ind_data, dict) and "error" not in ind_data:
            indicator_list.append({
                "name": ind_name,
                "value": ind_data.get("value"),
                "unit": ind_data.get("unit"),
                "change": ind_data.get("change"),
                "period": ind_data.get("period"),
                "last_updated": ind_data.get("period"),  # 使用 period 作为更新时间
            })
        elif isinstance(ind_data, dict) and "error" in ind_data:
            indicator_list.append({
                "name": ind_name,
                "value": None,
                "unit": None,
                "error": ind_data.get("error"),
            })

    response = {
        "market": market,
        "indicators": indicator_list,
        "source": provider_name,
        "fetched_at": now.isoformat(),
        "is_cached": False,
    }

    # 存入缓存
    macro_cache[cache_key] = response
    logger.info(f"[宏观服务] 数据获取成功 | 市场: {market} | 数据源: {provider_name}")

    return response
