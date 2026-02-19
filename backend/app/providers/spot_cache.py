"""
全量股票数据缓存管理器

提供 A 股全量实时数据的共享缓存，供 EastMoney 和 AKShare Provider 共同使用。
支持智能缓存时效控制：
- 交易时间内：缓存 5 分钟有效
- 非交易时间：缓存到下一交易日开盘
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, time
from threading import Lock
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = ZoneInfo("Asia/Shanghai")

# 缓存有效期配置（交易时间内，单位：秒）
CACHE_TTL_TRADING = 300  # 5 分钟

# 全局缓存结构
_spot_cache: Dict[str, Any] = {
    "data": None,        # DataFrame
    "fetched_at": None,  # datetime
    "source": None,      # str
}
_cache_lock = Lock()


def is_trading_time(now: Optional[datetime] = None) -> bool:
    """
    判断当前是否处于 A 股交易时间

    A 股交易时间：
    - 上午: 9:30 - 11:30
    - 下午: 13:00 - 15:00

    Args:
        now: 当前时间，默认使用北京时间

    Returns:
        bool: 是否处于交易时间
    """
    if now is None:
        now = datetime.now(BEIJING_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=BEIJING_TZ)

    # 周末不交易
    if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False

    current_time = now.time()

    # 上午交易时间 9:30 - 11:30
    morning_start = time(9, 30)
    morning_end = time(11, 30)

    # 下午交易时间 13:00 - 15:00
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)

    if morning_start <= current_time <= morning_end:
        return True
    if afternoon_start <= current_time <= afternoon_end:
        return True

    return False


def get_next_trading_open(now: Optional[datetime] = None) -> datetime:
    """
    获取下一个交易日开盘时间

    Args:
        now: 当前时间，默认使用北京时间

    Returns:
        datetime: 下一个交易日开盘时间 (9:30)
    """
    if now is None:
        now = datetime.now(BEIJING_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=BEIJING_TZ)

    current_time = now.time()
    afternoon_end = time(15, 0)

    # 如果当前时间在 15:00 之前，下一个开盘就是今天或明天
    if current_time < afternoon_end and now.weekday() < 5:
        # 工作日且在收盘前，返回今天或下一个交易时段
        return now.replace(hour=9, minute=30, second=0, microsecond=0)

    # 否则找下一个工作日
    next_day = now
    for _ in range(7):  # 最多找 7 天
        next_day = next_day.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day = datetime(
            next_day.year, next_day.month, next_day.day,
            tzinfo=BEIJING_TZ
        ) + __import__('datetime').timedelta(days=1)
        if next_day.weekday() < 5:  # 工作日
            return next_day.replace(hour=9, minute=30, second=0, microsecond=0)

    # 兜底返回明天
    return (now + __import__('datetime').timedelta(days=1)).replace(
        hour=9, minute=30, second=0, microsecond=0
    )


def is_cache_valid(fetched_at: Optional[datetime], now: Optional[datetime] = None) -> bool:
    """
    判断缓存是否有效

    时效规则：
    - 交易时间内：缓存 5 分钟有效
    - 非交易时间：缓存到下一交易日开盘

    Args:
        fetched_at: 缓存获取时间
        now: 当前时间，默认使用北京时间

    Returns:
        bool: 缓存是否有效
    """
    if fetched_at is None:
        return False

    if now is None:
        now = datetime.now(BEIJING_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=BEIJING_TZ)

    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=BEIJING_TZ)

    age = (now - fetched_at).total_seconds()

    if is_trading_time(now):
        # 交易时间内：5 分钟有效期
        return age < CACHE_TTL_TRADING
    else:
        # 非交易时间：缓存到下一交易日开盘
        next_open = get_next_trading_open(now)

        # 如果缓存是在当日收盘后获取的，且当前时间在下一开盘前
        if fetched_at.date() == now.date() or fetched_at < next_open:
            return now < next_open

        return False


def get_cached_spot_data() -> Optional[Any]:
    """
    获取缓存的全量数据

    Returns:
        DataFrame 或 None
    """
    with _cache_lock:
        if _spot_cache["data"] is None:
            return None

        if is_cache_valid(_spot_cache["fetched_at"]):
            logger.debug(f"[缓存] 命中 | 获取时间: {_spot_cache['fetched_at']}")
            return _spot_cache["data"]

        logger.debug(f"[缓存] 过期 | 获取时间: {_spot_cache['fetched_at']}")
        return None


def set_cached_spot_data(data: Any, source: str = "eastmoney") -> None:
    """
    设置缓存的全量数据

    Args:
        data: 全量股票 DataFrame
        source: 数据来源
    """
    with _cache_lock:
        _spot_cache["data"] = data
        _spot_cache["fetched_at"] = datetime.now(BEIJING_TZ)
        _spot_cache["source"] = source
        logger.info(f"[缓存] 更新 | 来源: {source} | 时间: {_spot_cache['fetched_at']}")


def get_spot_data_with_cache(fetch_func, source: str = "eastmoney") -> Optional[Any]:
    """
    获取全量数据（带缓存）

    优先使用缓存，缓存无效时调用 fetch_func 获取新数据

    Args:
        fetch_func: 获取数据的函数，返回 DataFrame
        source: 数据来源标识

    Returns:
        DataFrame 或 None
    """
    # 尝试从缓存获取
    cached = get_cached_spot_data()
    if cached is not None:
        return cached

    # 缓存无效，调用 fetch_func 获取新数据
    logger.info(f"[缓存] 重新获取 | 来源: {source}")
    try:
        data = fetch_func()
        if data is not None and not data.empty:
            set_cached_spot_data(data, source)
            return data
        return None
    except Exception as e:
        logger.error(f"[缓存] 获取失败 | 错误: {e}")
        return None


def clear_cache() -> None:
    """清空缓存"""
    with _cache_lock:
        _spot_cache["data"] = None
        _spot_cache["fetched_at"] = None
        _spot_cache["source"] = None
        logger.info("[缓存] 已清空")


def get_cache_status() -> Dict[str, Any]:
    """
    获取缓存状态

    Returns:
        Dict: 缓存状态信息
    """
    with _cache_lock:
        return {
            "has_cache": _spot_cache["data"] is not None,
            "fetched_at": _spot_cache["fetched_at"].isoformat() if _spot_cache["fetched_at"] else None,
            "source": _spot_cache["source"],
            "is_valid": is_cache_valid(_spot_cache["fetched_at"]) if _spot_cache["fetched_at"] else False,
        }
