"""业务逻辑服务层 - 多数据源支持 + 智能缓存 + 交易时间判断"""
import json
import re
import logging
import time
import threading
from typing import Optional, Dict, Tuple, List, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..schemas import StockWithStatus
from ..models import Stock
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo
from cachetools import TTLCache

# 导入数据源协调器
from ..providers import get_coordinator

# 导入信号生成服务
from .signals import generate_signal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ============ 缓存配置 ============
# K线数据缓存：10分钟有效，最多缓存 100 只股票
kline_cache = TTLCache(maxsize=100, ttl=600)

# 实时价格缓存：5秒有效，最多缓存 100 只股票
price_cache = TTLCache(maxsize=100, ttl=5)

# 股票名称缓存：24小时有效
name_cache = TTLCache(maxsize=500, ttl=86400)

# ============ 高级数据缓存 ============
# 财报数据缓存：24小时有效，最多缓存 100 只股票
financial_report_cache = TTLCache(maxsize=100, ttl=86400)

# 估值指标缓存：1小时有效，最多缓存 100 只股票
valuation_cache = TTLCache(maxsize=100, ttl=3600)

# 宏观指标缓存：24小时有效
macro_cache = TTLCache(maxsize=50, ttl=86400)

# ============ 线程锁 ============
# 交易日历刷新锁，防止并发刷新
_trading_calendar_lock = threading.Lock()
# 正在刷新的年份集合
_refreshing_years = set()


def clear_all_caches() -> Dict[str, int]:
    """
    清理所有内存缓存

    Returns:
        Dict[str, int]: 各缓存的清理数量
    """
    kline_count = len(kline_cache)
    price_count = len(price_cache)
    name_count = len(name_cache)
    financial_count = len(financial_report_cache)
    valuation_count = len(valuation_cache)
    macro_count = len(macro_cache)

    kline_cache.clear()
    price_cache.clear()
    name_cache.clear()
    financial_report_cache.clear()
    valuation_cache.clear()
    macro_cache.clear()

    logger.info(f"[缓存清理] 已清理 K线: {kline_count}, 价格: {price_count}, 名称: {name_count}, 财报: {financial_count}, 估值: {valuation_count}, 宏观: {macro_count}")

    return {
        "kline_cache": kline_count,
        "price_cache": price_count,
        "name_cache": name_count,
        "financial_report_cache": financial_count,
        "valuation_cache": valuation_count,
        "macro_cache": macro_count
    }


# ============ 交易时间判断 ============
def is_cn_trading_time() -> bool:
    """
    判断当前是否为A股交易时间（北京时间）
    A股交易时间：工作日 9:30-11:30, 13:00-15:00
    """
    beijing_tz = ZoneInfo("Asia/Shanghai")
    now_beijing = datetime.now(beijing_tz)

    # 周末不交易（0=周一, 6=周日）
    if now_beijing.weekday() >= 5:
        return False

    current_time = now_beijing.time()
    from datetime import time as t

    # 上午：9:30-11:30
    morning_start = t(9, 30)
    morning_end = t(11, 30)
    # 下午：13:00-15:00
    afternoon_start = t(13, 0)
    afternoon_end = t(15, 0)

    is_morning = morning_start <= current_time <= morning_end
    is_afternoon = afternoon_start <= current_time <= afternoon_end

    return is_morning or is_afternoon


def is_us_trading_time() -> bool:
    """
    判断当前是否为美股交易时间（美东时间）
    美股交易时间：美东时间 9:30-16:00
    """
    eastern_tz = ZoneInfo("America/New_York")
    now_eastern = datetime.now(eastern_tz)

    # 周末不交易
    if now_eastern.weekday() >= 5:
        return False

    current_time = now_eastern.time()
    from datetime import time as t

    trading_start = t(9, 30)
    trading_end = t(16, 0)

    return trading_start <= current_time <= trading_end


def is_real_trading_time(market: str, db=None) -> bool:
    """
    判断当前是否为真正的交易时间（交易日 + 交易时间段）

    Args:
        market: "cn" 表示A股，"us" 表示美股
        db: 数据库会话（用于交易日判断）

    Returns:
        bool: 是否在真正的交易时间内
    """
    # 首先判断是否在交易时间段内
    if not is_trading_time(market):
        return False

    # 对于A股，还需要判断是否为交易日
    if market == "cn" and db is not None:
        is_trading, _ = is_trading_day(db)
        return is_trading

    # 美股或其他情况，暂时只判断交易时间
    return True


def is_trading_time(market: str) -> bool:
    """
    根据市场类型判断是否为交易时间

    Args:
        market: "cn" 表示A股，"us" 表示美股

    Returns:
        bool: 是否在交易时间内
    """
    if market == "cn":
        return is_cn_trading_time()
    elif market == "us":
        return is_us_trading_time()
    return False


# ============ 交易日历服务 ============

def parse_date_flexible(date_str) -> Optional[date]:
    """
    灵活的日期解析函数，支持多种格式

    支持格式:
    - "2026-01-05" (带横线)
    - "20260105" (无分隔符)
    - "2026/01/05" (带斜杠)

    Args:
        date_str: 日期字符串或数字

    Returns:
        Optional[date]: 解析成功的日期对象，失败返回 None
    """
    date_str = str(date_str).strip()

    # 支持的日期格式列表
    formats = ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    logger.warning(f"[日期解析] 无法解析日期格式: {date_str}")
    return None


def fetch_trading_calendar_from_akshare(year: int) -> List[date]:
    """
    从 AkShare 获取指定年份的交易日历（第1层：主数据源）

    Args:
        year: 年份

    Returns:
        List[date]: 交易日列表
    """
    try:
        import akshare as ak
        logger.info(f"[交易日历-L1] AkShare 开始获取 {year} 年交易日历...")

        # 获取交易日历数据
        df = ak.tool_trade_date_hist_sina()
        logger.info(f"[交易日历-L1] AkShare 返回数据条数: {len(df) if df is not None else 0}")

        if df is None or df.empty:
            logger.warning(f"[交易日历-L1] AkShare 返回空数据")
            return []

        # 筛选指定年份
        year_str = str(year)
        trading_dates = []

        for date_value in df['trade_date'].tolist():
            date_str = str(date_value)
            # 检查年份匹配（支持多种格式）
            if date_str.startswith(year_str) or year_str in date_str:
                # 使用灵活的日期解析
                date_obj = parse_date_flexible(date_str)
                if date_obj and date_obj.year == year:
                    trading_dates.append(date_obj)

        logger.info(f"[交易日历-L1] AkShare 获取 {year} 年交易日历成功，共 {len(trading_dates)} 个交易日")
        return trading_dates

    except ImportError as e:
        logger.error(f"[交易日历-L1] AkShare 库未安装: {e}")
        return []
    except Exception as e:
        logger.error(f"[交易日历-L1] AkShare 获取失败: {type(e).__name__}: {e}")
        return []


def fetch_trading_calendar_from_exchange_calendars(year: int) -> List[date]:
    """
    从 exchange_calendars 库获取指定年份的交易日历（第2层：备用数据源）

    使用上海证券交易所(XSHG)日历作为中国A股交易日历

    Args:
        year: 年份

    Returns:
        List[date]: 交易日列表
    """
    try:
        import exchange_calendars as xcals
        logger.info(f"[交易日历-L2] exchange_calendars 开始获取 {year} 年交易日历...")

        # 获取上海证券交易所日历
        xshg = xcals.get_calendar("XSHG")

        # 获取指定年份的所有交易日
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        schedule = xshg.schedule.loc[start_date:end_date]
        trading_dates = [idx.date() for idx in schedule.index]

        logger.info(f"[交易日历-L2] exchange_calendars 获取 {year} 年交易日历成功，共 {len(trading_dates)} 个交易日")
        return trading_dates

    except ImportError as e:
        logger.warning(f"[交易日历-L2] exchange_calendars 库未安装: {e}")
        return []
    except Exception as e:
        logger.error(f"[交易日历-L2] exchange_calendars 获取失败: {type(e).__name__}: {e}")
        return []


def get_trading_dates_with_fallback(year: int) -> List[date]:
    """
    使用多层数据源获取交易日历（带 fallback 机制）

    优先级：
    1. AkShare（主数据源，节假日最准确）
    2. exchange_calendars（备用数据源，纯本地计算）

    Args:
        year: 年份

    Returns:
        List[date]: 交易日列表
    """
    # 第1层：AkShare
    trading_dates = fetch_trading_calendar_from_akshare(year)
    if trading_dates:
        return trading_dates

    logger.warning(f"[交易日历] AkShare 获取失败，尝试备用数据源...")

    # 第2层：exchange_calendars
    trading_dates = fetch_trading_calendar_from_exchange_calendars(year)
    if trading_dates:
        return trading_dates

    logger.error(f"[交易日历] 所有数据源均获取失败，{year} 年交易日历将为空")
    return []


def refresh_trading_calendar(db, year: int = None) -> Tuple[int, str]:
    """
    刷新交易日历缓存

    Args:
        db: 数据库会话
        year: 年份，默认为当前年份

    Returns:
        Tuple[int, str]: (新增记录数, 消息)
    """
    from .. import crud

    if year is None:
        year = date.today().year

    # 删除旧缓存
    deleted = crud.delete_trading_calendar_by_year(db, year)
    logger.info(f"[交易日历] 删除 {year} 年旧缓存: {deleted} 条")

    # 使用多层数据源获取交易日历
    trading_dates = get_trading_dates_with_fallback(year)

    if not trading_dates:
        return 0, f"获取 {year} 年交易日历失败"

    # 生成全年日历数据（标记交易日和非交易日）
    from datetime import date as date_type

    start_date = date_type(year, 1, 1)
    end_date = date_type(year, 12, 31)

    calendar_data = []
    current_date = start_date

    while current_date <= end_date:
        is_trading = current_date in trading_dates
        calendar_data.append({
            "trade_date": current_date,
            "is_trading_day": 1 if is_trading else 0
        })
        current_date += timedelta(days=1)

    # 批量保存
    created = crud.batch_create_trading_calendar(db, calendar_data)

    trading_count = len(trading_dates)
    message = f"已刷新 {year} 年交易日历，共 {len(calendar_data)} 天，其中 {trading_count} 个交易日"
    logger.info(f"[交易日历] {message}")

    return created, message


def is_trading_day(db=None, target_date: date = None) -> Tuple[bool, str]:
    """
    判断指定日期是否为交易日（多层数据源 + 3层兜底）

    数据源优先级：
    1. 数据库缓存（最准确，已同步）
    2. exchange_calendars 快速判断（备用）
    3. 周末判断（基础兜底）

    Args:
        db: 数据库会话（可选，如不传入则创建独立会话）
        target_date: 目标日期，默认为今天

    Returns:
        Tuple[bool, str]: (是否为交易日, 原因说明)
    """
    from .. import crud
    from ..database import SessionLocal

    if target_date is None:
        target_date = date.today()

    year = target_date.year

    # 【修复】使用独立的数据库会话，避免并发问题
    use_local_session = db is None
    if use_local_session:
        db = SessionLocal()

    try:
        # 第1层：检查数据库缓存（使用锁保护，防止并发刷新）
        if not crud.is_year_cached(db, year):
            # 使用锁保护刷新操作，防止多个线程同时刷新
            with _trading_calendar_lock:
                # 双重检查：获取锁后再次确认是否已被其他线程刷新
                if not crud.is_year_cached(db, year) and year not in _refreshing_years:
                    _refreshing_years.add(year)
                    try:
                        logger.info(f"[交易日历] {year} 年缓存不存在，开始获取")
                        refresh_trading_calendar(db, year)
                    finally:
                        _refreshing_years.discard(year)

    # 查询数据库
        calendar = crud.get_trading_calendar_by_date(db, target_date)

        if calendar is not None:
            # 数据库有数据，直接返回
            if calendar.is_trading_day == 1:
                return True, "交易日"
            else:
                if target_date.weekday() >= 5:
                    return False, "周末"
                return False, "节假日"

        # 第2层：使用 exchange_calendars 快速判断
        try:
            import exchange_calendars as xcals
            xshg = xcals.get_calendar("XSHG")
            date_str = target_date.strftime("%Y-%m-%d")
            is_session = xshg.is_session(date_str)
            logger.info(f"[交易日历-L2兜底] exchange_calendars 判断 {date_str}: {'交易日' if is_session else '非交易日'}")
            if is_session:
                return True, "交易日（备用数据源）"
            else:
                if target_date.weekday() >= 5:
                    return False, "周末"
                return False, "非交易日（备用数据源）"
        except Exception as e:
            logger.warning(f"[交易日历-L2兜底] exchange_calendars 判断失败: {e}")

        # 第3层：基础周末判断（最终兜底）
        if target_date.weekday() >= 5:
            return False, "周末"
        return True, "工作日（基础判断）"
    finally:
        # 【修复】关闭独立创建的会话
        if use_local_session:
            db.close()


def fetch_historical_kline_data(symbol: str, target_date: date, ma_types: List[str] = None) -> Tuple[Optional[float], Optional[Dict]]:
    """
    获取历史 K 线数据，用于生成历史快照（使用多数据源协调器）

    Args:
        symbol: 股票代码
        target_date: 目标日期
        ma_types: MA 类型列表，如 ["MA5", "MA20"]

    Returns:
        Tuple[Optional[float], Optional[Dict]]: (收盘价, MA结果字典)
    """
    import re

    if ma_types is None:
        ma_types = ["MA5"]

    normalized_code, market = normalize_symbol_for_sina(symbol)

    # 计算 K 线数据长度（取最大 MA 周期 + 额外天数以确保覆盖目标日期）
    max_ma_period = 5  # 默认值
    for ma in ma_types:
        match = re.search(r'\d+', ma)
        if match:
            max_ma_period = max(max_ma_period, int(match.group()))

    # 获取足够的 K 线数据（目标日期前后各取一些）
    datalen = max_ma_period + 30  # 多取一些确保有目标日期的数据

    # 使用数据源协调器获取 K 线数据
    coordinator = get_coordinator()
    kline_data, provider_name, tried_providers = coordinator.get_kline_data(
        symbol, normalized_code, market, datalen
    )

    if kline_data is None:
        logger.warning(f"[历史K线数据] 获取失败 | 股票: {symbol} | 日期: {target_date} | 尝试过: {tried_providers}")
        return None, None

    try:
        if not kline_data or not isinstance(kline_data, list):
            logger.warning(f"[历史K线数据] 数据为空 | 股票: {symbol}")
            return None, None

        # 查找目标日期的 K 线数据
        target_date_str = target_date.strftime("%Y-%m-%d")
        target_kline = None
        target_index = -1

        for i, item in enumerate(kline_data):
            kline_date = item.get('day', '').split(' ')[0]
            if kline_date == target_date_str:
                target_kline = item
                target_index = i
                break

        if target_kline is None:
            logger.warning(f"[历史K线数据] 未找到目标日期数据 | 股票: {symbol} | 日期: {target_date}")
            return None, None

        # 获取收盘价
        close_price = float(target_kline.get('close', 0))
        if close_price <= 0:
            logger.warning(f"[历史K线数据] 收盘价无效 | 股票: {symbol} | 日期: {target_date}")
            return None, None

        # 计算各 MA 值
        ma_results = {}
        for ma_type in ma_types:
            match = re.search(r'\d+', ma_type)
            if not match:
                continue
            ma_period = int(match.group())

            # 计算该日期的 MA（使用目标日期及之前的收盘价）
            closes = []
            for j in range(max(0, target_index - ma_period + 1), target_index + 1):
                closes.append(float(kline_data[j].get('close', 0)))

            if len(closes) >= ma_period and all(c > 0 for c in closes):
                ma_val = round(sum(closes) / ma_period, 2)
                diff = close_price - ma_val
                ma_results[ma_type] = {
                    "ma_price": ma_val,
                    "reached_target": close_price >= ma_val,
                    "price_difference": round(diff, 2),
                    "price_difference_percent": round((diff / ma_val) * 100, 2) if ma_val > 0 else 0
                }
                logger.debug(f"[历史K线数据] {ma_type}: {ma_val} | 收盘价: {close_price} | 股票: {symbol}")

        logger.info(f"[历史K线数据] 获取成功 | 股票: {symbol} | 日期: {target_date} | 数据源: {provider_name} | 收盘价: {close_price} | MA数量: {len(ma_results)}")

        return close_price, ma_results

    except Exception as e:
        logger.error(f"[历史K线数据] 解析异常 | 股票: {symbol} | 日期: {target_date} | 错误: {e}")
        return None, None


def get_last_trading_day_close() -> datetime:
    """
    获取最近一个交易日的收盘时间（北京时间）
    用于判断缓存数据是否已经是最新的收盘数据
    """
    beijing_tz = ZoneInfo("Asia/Shanghai")
    now_beijing = datetime.now(beijing_tz)

    # 当前时间在15:00之前，最近收盘日是昨天或更早
    from datetime import time as t
    if now_beijing.time() < t(15, 0):
        # 回退到前一天
        now_beijing = now_beijing - timedelta(days=1)

    # 跳过周末
    while now_beijing.weekday() >= 5:  # 周六或周日
        now_beijing = now_beijing - timedelta(days=1)

    # 返回当天15:00（收盘时间）
    return now_beijing.replace(hour=15, minute=0, second=0, microsecond=0)


def should_refresh_price(stock: Stock, market: str, db = None, need_calc: bool = False) -> Tuple[bool, str]:
    """
    判断是否需要刷新价格数据

    Args:
        stock: 股票对象
        market: 市场类型 ("cn" 或 "us")
        db: 数据库会话（用于交易日判断）
        need_calc: 是否需要计算（新增股票/指标时为True）

    Returns:
        Tuple[bool, str]: (是否需要刷新, 原因说明)
    """
    # 1. 如果需要计算（新增股票/指标），直接获取数据
    if need_calc:
        return True, "新增股票或指标变更，获取最近交易日数据"

    # 2. 判断是否为交易日（如果有 db 参数）
    if db is not None and market == "cn":
        is_trading, reason = is_trading_day(db)
        if not is_trading:
            # 非交易日，不刷新，使用缓存
            return False, f"非交易日（{reason}），使用缓存数据"

    # 3. 如果在交易时间内，刷新获取实时数据
    if is_trading_time(market):
        return True, "交易时间内，实时获取最新价格"

    # 4. 非交易时间，检查是否需要更新收盘数据
    # 如果当前价格为空，需要获取
    if stock.current_price is None:
        return True, "当前价格为空，需要获取"

    # 检查数据是否已是最新的收盘数据
    if stock.updated_at is None:
        return True, "更新时间为空，需要获取"

    # 确保 stock.updated_at 是 timezone-aware
    beijing_tz = ZoneInfo("Asia/Shanghai")
    if stock.updated_at.tzinfo is None:
        # 假设数据库存储的是 UTC 时间
        last_update = stock.updated_at.replace(tzinfo=timezone.utc)
    else:
        last_update = stock.updated_at

    # 获取最近交易日收盘时间
    last_close_time = get_last_trading_day_close()

    # 如果更新时间早于最近收盘时间，需要刷新
    if last_update.astimezone(beijing_tz) < last_close_time:
        return True, f"数据过期，上次更新: {last_update.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M')}"

    return False, f"数据已是最新收盘数据，更新于: {last_update.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M')}"


def normalize_symbol_for_sina(symbol: str) -> Tuple[str, str]:
    """为新浪接口规范化代码并识别市场类型 (cn/us)"""
    symbol = symbol.strip().upper()
    if not symbol.isdigit() and "." not in symbol:
        return symbol, "us"
    if "." in symbol:
        parts = symbol.split(".")
        code, market = parts[0], parts[1].lower()
        if market in ["ss", "sh"]: return f"sh{code}", "cn"
        if market == "sz": return f"sz{code}", "cn"
        if market == "bj": return f"bj{code}", "cn"
        return symbol, "us"
    if len(symbol) == 6:
        # 北交所：4/8/92 开头（92开头需优先于其他9开头判断）
        if symbol.startswith(('4', '8')): return f"bj{symbol}", "cn"
        if symbol.startswith('92'): return f"bj{symbol}", "cn"
        # 上交所：6 开头，或其他 9 开头（如科创板CDR）
        if symbol.startswith('6'): return f"sh{symbol}", "cn"
        if symbol.startswith('9'): return f"sh{symbol}", "cn"
        # 深交所：0/3 开头
        if symbol.startswith(('0', '3')): return f"sz{symbol}", "cn"
    return symbol, "us"


def fetch_realtime_data(symbol: str, use_cache: bool = True, is_trading_time: bool = False) -> Tuple[Optional[float], Optional[str]]:
    """
    获取实时价格和股票名称（使用多数据源协调器）

    Args:
        symbol: 股票代码
        use_cache: 是否使用缓存（非交易时间使用）
        is_trading_time: 是否在交易时间内（交易时间内不缓存价格数据）

    Returns:
        Tuple[Optional[float], Optional[str]]: (价格, 名称)
    """
    # 交易时间内不使用缓存，确保数据实时性
    if use_cache and not is_trading_time and symbol in price_cache:
        logger.info(f"[实时行情] 缓存命中 | 股票: {symbol}")
        return price_cache[symbol]

    # 使用数据源协调器获取数据
    coordinator = get_coordinator()
    normalized_code, market = normalize_symbol_for_sina(symbol)

    result = coordinator.get_realtime_price(symbol, normalized_code, market)

    if result.success and result.data:
        price = result.data.current_price
        name = result.data.name

        # 非交易时间缓存数据
        if not is_trading_time:
            price_cache[symbol] = (price, name)

        logger.info(f"[实时行情] 获取成功 | 股票: {symbol} | 数据源: {result.provider_name} | 名称: {name} | 价格: {price}")
        return price, name

    logger.warning(f"[实时行情] 获取失败 | 股票: {symbol} | 尝试过: {result.tried_providers}")
    return None, None


def fetch_stock_name(symbol: str) -> Optional[str]:
    """获取股票中文名称"""
    _, name = fetch_realtime_data(symbol)
    return name


def get_stock_chart_urls(symbol: str) -> Dict[str, str]:
    """获取股票趋势图 URL (新浪财经 GIF)"""
    code, market = normalize_symbol_for_sina(symbol)

    if market == "cn":
        base_url = "https://image.sinajs.cn/newchart"
        urls = {
            "min": f"{base_url}/min/n/{code}.gif",
            "daily": f"{base_url}/daily/n/{code}.gif",
            "weekly": f"{base_url}/weekly/n/{code}.gif",
            "monthly": f"{base_url}/monthly/n/{code}.gif"
        }
    else:
        us_code = code.lower()
        base_url = "https://image.sinajs.cn/newchart/v5/usstock"
        urls = {
            "min": f"{base_url}/min/{us_code}.gif",
            "daily": f"{base_url}/daily/{us_code}.gif",
            "weekly": f"{base_url}/weekly/{us_code}.gif",
            "monthly": f"{base_url}/monthly/{us_code}.gif"
        }

    logger.info(f"[新浪趋势图] 生成URL | 股票: {symbol} | 图表类型: 分时/日K/周K/月K")
    return urls


def enrich_stock_with_status(stock: Stock, force_refresh: bool = False, db = None, need_calc: bool = False) -> StockWithStatus:
    """为股票对象添加实时价格和多指标状态信息（带缓存 + 交易时间智能缓存）

    Args:
        stock: 股票对象
        force_refresh: 是否强制刷新（绕过缓存），默认 False
        db: 数据库会话（用于交易日判断）
        need_calc: 是否需要计算（新增股票/指标时为True，非交易时间也会获取数据）

    Returns:
        StockWithStatus: 包含 is_realtime 字段，标识数据是否为实时获取
    """
    from ..schemas import MAResult

    # 获取市场类型
    _, market = normalize_symbol_for_sina(stock.symbol)

    # 智能缓存决策：判断是否需要获取数据
    need_fetch_data = False
    is_realtime = False
    refresh_reason = ""
    data_fetched_at = None  # 数据获取时间

    if force_refresh:
        need_fetch_data = True
        # 只有在真正的交易时间内才标记为实时（交易日 + 交易时间段）
        is_realtime = is_real_trading_time(market, db=db)
        refresh_reason = "强制刷新"
    else:
        need_refresh, refresh_reason = should_refresh_price(stock, market, db=db, need_calc=need_calc)
        if need_refresh:
            need_fetch_data = True
            # 只有在真正的交易时间内才标记为实时（交易日 + 交易时间段）
            is_realtime = is_real_trading_time(market, db=db)

    logger.info(f"[数据富化] 开始处理 | 股票: {stock.symbol} ({stock.name}) | 指标: {stock.ma_types} | 实时模式: {is_realtime} | 获取数据: {need_fetch_data} | 原因: {refresh_reason}")
    enrich_start = time.time()

    # 解析 ma_types，过滤无效值
    if stock.ma_types and stock.ma_types.strip():
        ma_types_list = [ma.strip() for ma in stock.ma_types.split(",") if ma.strip()]
    else:
        ma_types_list = []

    # 如果没有有效的 ma_types，使用默认值
    if not ma_types_list:
        ma_types_list = ["MA5"]
        logger.warning(f"[数据富化] 指标为空，使用默认值 MA5 | 股票: {stock.symbol}")

    ma_results = {}

    # 根据智能缓存决策获取数据
    if need_fetch_data:
        # 【获取数据模式】请求 API 获取最新数据
        # 交易时间内不缓存，确保数据实时性
        current_price, _ = fetch_realtime_data(stock.symbol, use_cache=False, is_trading_time=is_realtime)
        # 记录数据获取时间
        data_fetched_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    else:
        # 【缓存模式】使用数据库中已有的价格
        current_price = stock.current_price
        # 缓存模式下，使用数据库的 updated_at 作为数据获取时间
        data_fetched_at = stock.updated_at

        # 【修复】如果缓存价格为 None 或 0，强制重新获取
        if current_price is None or current_price <= 0:
            logger.warning(f"[智能缓存] 缓存价格无效，强制刷新 | 股票: {stock.symbol} | 缓存价格: {current_price}")
            current_price, _ = fetch_realtime_data(stock.symbol, use_cache=False, is_trading_time=is_realtime)
            # 只有在真正的交易时间内才标记为实时（交易日 + 交易时间段）
            is_realtime = is_real_trading_time(market, db=db)
            # 重新获取数据后，更新获取时间
            data_fetched_at = datetime.now(ZoneInfo("Asia/Shanghai"))
        else:
            logger.info(f"[智能缓存] 使用缓存数据 | 股票: {stock.symbol} | 价格: {current_price}")

    # 【优化2】一次获取足够多的 K 线数据（取最大周期），避免每个 MA 类型重复请求
    # 安全提取 MA 周期数字
    ma_periods = []
    for ma in ma_types_list:
        match = re.search(r'\d+', ma)
        if match:
            ma_periods.append(int(match.group()))
        else:
            logger.warning(f"[数据富化] 无效的指标格式: {ma} | 股票: {stock.symbol}")

    # 如果没有有效的周期，使用默认值 5
    max_ma_period = max(ma_periods) if ma_periods else 5

    normalized_code, _ = normalize_symbol_for_sina(stock.symbol)
    kline_closes = None

    # K线缓存键：股票代码:日期:最大周期（确保不同指标组合使用独立缓存）
    cache_key = f"{stock.symbol}:{date.today()}:{max_ma_period}"

    # 检查 K 线缓存（仅在非实时模式下使用缓存）
    if not is_realtime and cache_key in kline_cache:
        logger.info(f"[K线数据] 缓存命中 | 股票: {stock.symbol} | 周期: {max_ma_period}")
        kline_closes = kline_cache[cache_key]
    else:
        # 缓存未命中或实时模式，使用协调器请求 API
        datalen = max_ma_period + 2
        coordinator = get_coordinator()
        kline_data, provider_name, tried_providers = coordinator.get_kline_data(
            stock.symbol, normalized_code, market, datalen
        )

        if kline_data:
            try:
                # 【修复】过滤无效的 close 值，避免 None 或空字符串导致后续计算错误
                kline_closes = []
                for item in kline_data:
                    close_val = item.get('close')
                    if close_val is not None and close_val != '' and close_val != 0:
                        try:
                            kline_closes.append(float(close_val))
                        except (ValueError, TypeError):
                            pass  # 跳过无效数据

                # 【修正】根据交易时间决定是否加入实时价格到 MA 计算
                # 交易时间内：加入实时价格，MA 动态计算
                # 非交易时间：只用历史 K 线收盘价
                if is_realtime and current_price is not None and current_price > 0:
                    kline_closes.append(current_price)
                    logger.info(f"[MA计算] 交易时间内，实时价格加入MA计算 | 股票: {stock.symbol} | 实时价格: {current_price}")

                # 存入缓存（仅当有有效数据且非实时模式时）
                if kline_closes and not is_realtime:
                    kline_cache[cache_key] = kline_closes
                logger.info(f"[K线数据] 获取成功 | 股票: {stock.symbol} | 数据源: {provider_name} | K线数量: {len(kline_closes)}")
            except Exception as e:
                logger.error(f"[K线数据] 解析异常 | 股票: {stock.symbol} | 错误: {e}")

    # 【新增】如果实时价格获取失败（停牌、退市等），使用 K 线历史数据的最后收盘价
    if current_price is None and kline_closes and len(kline_closes) > 0:
        current_price = kline_closes[-1]
        logger.info(f"[历史数据兜底] 使用 K 线最后收盘价 | 股票: {stock.symbol} | 价格: {current_price}")

    # 【优化3】本地计算所有 MA 值（无需再次请求 API）
    for ma_type in ma_types_list:
        ma_period = int(re.search(r'\d+', ma_type).group())
        res = MAResult(reached_target=False)

        if current_price is not None and kline_closes and len(kline_closes) >= ma_period:
            final_closes = kline_closes[-ma_period:]
            # 【安全检查】过滤掉可能的 None 值
            final_closes = [c for c in final_closes if c is not None]

            if len(final_closes) >= ma_period:
                ma_val = round(sum(final_closes) / ma_period, 2)
            else:
                ma_val = None

            if ma_val is not None and ma_val > 0:
                diff = current_price - ma_val
                res = MAResult(
                    ma_price=ma_val,
                    reached_target=current_price >= ma_val,
                    price_difference=round(diff, 2),
                    price_difference_percent=round((diff / ma_val) * 100, 2)
                )
                status = "✅达标" if res.reached_target else "⏳未达"
                logger.debug(f"[MA计算] {ma_type}: {ma_val} | 当前价: {current_price} | 偏离: {diff:.2f} ({res.price_difference_percent:.2f}%) | {status}")

        ma_results[ma_type] = res

    # 汇总日志
    enrich_elapsed = (time.time() - enrich_start) * 1000
    reached_count = sum(1 for r in ma_results.values() if r.reached_target)
    logger.info(f"[数据富化] 处理完成 | 股票: {stock.symbol} | 当前价: {current_price} | 达标: {reached_count}/{len(ma_types_list)} | 实时: {is_realtime} | 总耗时: {enrich_elapsed:.0f}ms")

    # 为了兼容前端或作为汇总展示，取第一个指标的结果作为汇总字段
    first_ma = ma_types_list[0] if ma_types_list else "MA5"
    main_res = ma_results.get(first_ma)

    # 生成买卖信号（使用 K 线数据）
    signal_data = None
    if kline_closes and len(kline_closes) >= 20:
        try:
            import pandas as pd
            # 构建 DataFrame 用于信号计算
            kline_df = pd.DataFrame({
                'open': kline_closes,
                'high': kline_closes,
                'low': kline_closes,
                'close': kline_closes,
                'volume': [0] * len(kline_closes)
            })
            signal_result = generate_signal(kline_df, current_price)
            # 只保留前端需要的字段
            signal_data = {
                'signal_type': signal_result['signal_type'],
                'strength': signal_result['strength'],
                'entry_price': signal_result.get('entry_price'),
                'stop_loss': signal_result.get('stop_loss'),
                'take_profit': signal_result.get('take_profit'),
                'triggers': signal_result.get('triggers', []),
                'message': signal_result.get('message', '')
            }
            logger.debug(f"[信号生成] 股票: {stock.symbol} | 信号: {signal_result['signal_type']} | 强度: {signal_result['strength']}")
        except Exception as e:
            logger.warning(f"[信号生成] 失败 | 股票: {stock.symbol} | 错误: {e}")

    return StockWithStatus(
        id=stock.id,
        symbol=stock.symbol,
        name=stock.name,
        ma_types=ma_types_list,
        ma_results=ma_results,
        group_ids=[g.id for g in stock.groups],
        group_names=[g.name for g in stock.groups],
        ma_price=main_res.ma_price if main_res else None,
        current_price=current_price or stock.current_price,
        created_at=stock.created_at,
        updated_at=stock.updated_at,
        reached_target=main_res.reached_target if main_res else False,
        price_difference=main_res.price_difference if main_res else None,
        price_difference_percent=main_res.price_difference_percent if main_res else None,
        is_realtime=is_realtime,
        data_fetched_at=data_fetched_at,
        signal=signal_data
    )


def enrich_stocks_batch(stocks: List[Stock], force_refresh: bool = False, max_workers: int = 10, db = None, need_calc: bool = False) -> List[StockWithStatus]:
    """
    并发富化多只股票的状态信息

    Args:
        stocks: 股票对象列表
        force_refresh: 是否强制刷新（绕过缓存）
        max_workers: 最大并发线程数，默认10
        db: 数据库会话（用于交易日判断）
        need_calc: 是否需要计算（新增股票/指标时为True）

    Returns:
        List[StockWithStatus]: 富化后的股票状态列表
    """
    if not stocks:
        return []

    batch_start = time.time()
    logger.info(f"[批量富化] 开始处理 {len(stocks)} 只股票 | 并发数: {max_workers} | 强制刷新: {force_refresh} | 需要计算: {need_calc}")

    # ========== 线程安全修复：在主线程中预先计算所有需要 db 的数据 ==========
    # 1. 预先计算每个市场的交易日状态（避免子线程访问 db）
    trading_day_cache = {}
    realtime_cache = {}
    for market in ["cn", "us"]:
        if market == "cn" and db is not None:
            trading_day_cache[market] = is_trading_day(db)
        else:
            trading_day_cache[market] = (True, "美股或无数据库连接")
        # 预计算是否为真正的交易时间（交易日 + 交易时间段）
        realtime_cache[market] = is_real_trading_time(market, db=db)

    # 2. 预加载所有股票的 groups 数据（避免子线程懒加载 relationship）
    stocks_data = []
    for stock in stocks:
        stocks_data.append({
            'stock': stock,
            'group_ids': [g.id for g in stock.groups] if stock.groups else [],
            'group_names': [g.name for g in stock.groups] if stock.groups else [],
        })

    results = [None] * len(stocks)  # 预分配结果列表，保持顺序

    def process_stock(index, stock_data):
        """处理单只股票并返回带索引的结果（线程安全版本）"""
        try:
            stock = stock_data['stock']
            result = _enrich_stock_with_status_threadsafe(
                stock=stock,
                group_ids=stock_data['group_ids'],
                group_names=stock_data['group_names'],
                force_refresh=force_refresh,
                need_calc=need_calc,
                trading_day_cache=trading_day_cache,
                realtime_cache=realtime_cache
            )
            return (index, result)
        except Exception as e:
            import traceback
            logger.error(f"[批量富化] 处理失败 | 股票: {stock_data['stock'].symbol} | 错误: {e}\n{traceback.format_exc()}")
            return (index, None)

    # 使用线程池并发处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(process_stock, i, stock_data): i
            for i, stock_data in enumerate(stocks_data)
        }

        # 收集结果
        for future in as_completed(futures):
            try:
                index, result = future.result()
                if result:
                    results[index] = result
            except Exception as e:
                logger.error(f"[批量富化] 任务异常 | 错误: {e}")

    # 过滤掉 None 结果
    valid_results = [r for r in results if r is not None]

    batch_elapsed = (time.time() - batch_start) * 1000
    logger.info(f"[批量富化] 处理完成 | 成功: {len(valid_results)}/{len(stocks)} | 总耗时: {batch_elapsed:.0f}ms | 平均: {batch_elapsed/len(stocks):.0f}ms/只")

    return valid_results


def _enrich_stock_with_status_threadsafe(
    stock: Stock,
    group_ids: List[int],
    group_names: List[str],
    force_refresh: bool = False,
    need_calc: bool = False,
    trading_day_cache: dict = None,
    realtime_cache: dict = None
) -> StockWithStatus:
    """
    线程安全版本的 enrich_stock_with_status

    与 enrich_stock_with_status 的区别：
    - 不访问 db 参数
    - 使用预计算的 trading_day_cache 和 realtime_cache
    - 使用预加载的 group_ids 和 group_names

    Args:
        stock: 股票对象
        group_ids: 预加载的分组ID列表
        group_names: 预加载的分组名称列表
        force_refresh: 是否强制刷新（绕过缓存），默认 False
        need_calc: 是否需要计算（新增股票/指标时为True）
        trading_day_cache: 预计算的交易日状态缓存 {"cn": (bool, str), "us": (bool, str)}
        realtime_cache: 预计算的实时状态缓存 {"cn": bool, "us": bool}

    Returns:
        StockWithStatus: 包含状态信息的股票对象
    """
    from ..schemas import MAResult

    # 获取市场类型
    _, market = normalize_symbol_for_sina(stock.symbol)

    # 智能缓存决策：判断是否需要获取数据（使用预计算缓存）
    need_fetch_data = False
    is_realtime = False
    refresh_reason = ""
    data_fetched_at = None  # 数据获取时间

    if force_refresh:
        need_fetch_data = True
        # 使用预计算的实时状态
        is_realtime = realtime_cache.get(market, False) if realtime_cache else False
        refresh_reason = "强制刷新"
    else:
        # 使用预计算的交易日状态判断是否需要刷新
        need_refresh, refresh_reason = _should_refresh_price_threadsafe(
            stock, market, need_calc, trading_day_cache
        )
        if need_refresh:
            need_fetch_data = True
            # 使用预计算的实时状态
            is_realtime = realtime_cache.get(market, False) if realtime_cache else False

    logger.info(f"[数据富化] 开始处理 | 股票: {stock.symbol} ({stock.name}) | 指标: {stock.ma_types} | 实时模式: {is_realtime} | 获取数据: {need_fetch_data} | 原因: {refresh_reason}")
    enrich_start = time.time()

    # 解析 ma_types，过滤无效值
    if stock.ma_types and stock.ma_types.strip():
        ma_types_list = [ma.strip() for ma in stock.ma_types.split(",") if ma.strip()]
    else:
        ma_types_list = []

    # 如果没有有效的 ma_types，使用默认值
    if not ma_types_list:
        ma_types_list = ["MA5"]
        logger.warning(f"[数据富化] 指标为空，使用默认值 MA5 | 股票: {stock.symbol}")

    ma_results = {}

    # 根据智能缓存决策获取数据
    if need_fetch_data:
        # 【获取数据模式】请求 API 获取最新数据
        # 交易时间内不缓存，确保数据实时性
        current_price, _ = fetch_realtime_data(stock.symbol, use_cache=False, is_trading_time=is_realtime)
        # 记录数据获取时间
        data_fetched_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    else:
        # 【缓存模式】使用数据库中已有的价格
        current_price = stock.current_price
        # 缓存模式下，使用数据库的 updated_at 作为数据获取时间
        data_fetched_at = stock.updated_at

        # 【修复】如果缓存价格为 None 或 0，强制重新获取
        if current_price is None or current_price <= 0:
            logger.warning(f"[智能缓存] 缓存价格无效，强制刷新 | 股票: {stock.symbol} | 缓存价格: {current_price}")
            current_price, _ = fetch_realtime_data(stock.symbol, use_cache=False, is_trading_time=is_realtime)
            # 使用预计算的实时状态
            is_realtime = realtime_cache.get(market, False) if realtime_cache else False
            # 重新获取数据后，更新获取时间
            data_fetched_at = datetime.now(ZoneInfo("Asia/Shanghai"))
        else:
            logger.info(f"[智能缓存] 使用缓存数据 | 股票: {stock.symbol} | 价格: {current_price}")

    # 【优化2】一次获取足够多的 K 线数据（取最大周期），避免每个 MA 类型重复请求
    # 安全提取 MA 周期数字
    ma_periods = []
    for ma in ma_types_list:
        match = re.search(r'\d+', ma)
        if match:
            ma_periods.append(int(match.group()))
        else:
            logger.warning(f"[数据富化] 无效的指标格式: {ma} | 股票: {stock.symbol}")

    # 如果没有有效的周期，使用默认值 5
    max_ma_period = max(ma_periods) if ma_periods else 5

    normalized_code, _ = normalize_symbol_for_sina(stock.symbol)
    kline_closes = None

    # K线缓存键：股票代码:日期:最大周期（确保不同指标组合使用独立缓存）
    cache_key = f"{stock.symbol}:{date.today()}:{max_ma_period}"

    # 检查 K 线缓存（仅在非实时模式下使用缓存）
    if not is_realtime and cache_key in kline_cache:
        logger.info(f"[K线数据] 缓存命中 | 股票: {stock.symbol} | 周期: {max_ma_period}")
        kline_closes = kline_cache[cache_key]
    else:
        # 缓存未命中或实时模式，使用协调器请求 API
        datalen = max_ma_period + 2
        coordinator = get_coordinator()
        kline_data, provider_name, tried_providers = coordinator.get_kline_data(
            stock.symbol, normalized_code, market, datalen
        )

        if kline_data:
            try:
                # 【修复】过滤无效的 close 值，避免 None 或空字符串导致后续计算错误
                kline_closes = []
                for item in kline_data:
                    close_val = item.get('close')
                    if close_val is not None and close_val != '' and close_val != 0:
                        try:
                            kline_closes.append(float(close_val))
                        except (ValueError, TypeError):
                            pass  # 跳过无效数据

                # 【修正】根据交易时间决定是否加入实时价格到 MA 计算
                # 交易时间内：加入实时价格，MA 动态计算
                # 非交易时间：只用历史 K 线收盘价
                if is_realtime and current_price is not None and current_price > 0:
                    kline_closes.append(current_price)
                    logger.info(f"[MA计算] 交易时间内，实时价格加入MA计算 | 股票: {stock.symbol} | 实时价格: {current_price}")

                # 存入缓存（仅当有有效数据且非实时模式时）
                if kline_closes and not is_realtime:
                    kline_cache[cache_key] = kline_closes
                logger.info(f"[K线数据] 获取成功 | 股票: {stock.symbol} | 数据源: {provider_name} | K线数量: {len(kline_closes)}")
            except Exception as e:
                logger.error(f"[K线数据] 解析异常 | 股票: {stock.symbol} | 错误: {e}")

    # 【新增】如果实时价格获取失败（停牌、退市等），使用 K 线历史数据的最后收盘价
    if current_price is None and kline_closes and len(kline_closes) > 0:
        current_price = kline_closes[-1]
        logger.info(f"[历史数据兜底] 使用 K 线最后收盘价 | 股票: {stock.symbol} | 价格: {current_price}")

    # 【优化3】本地计算所有 MA 值（无需再次请求 API）
    for ma_type in ma_types_list:
        ma_period = int(re.search(r'\d+', ma_type).group())
        res = MAResult(reached_target=False)

        if current_price is not None and kline_closes and len(kline_closes) >= ma_period:
            final_closes = kline_closes[-ma_period:]
            # 【安全检查】过滤掉可能的 None 值
            final_closes = [c for c in final_closes if c is not None]

            if len(final_closes) >= ma_period:
                ma_val = round(sum(final_closes) / ma_period, 2)
            else:
                ma_val = None

            if ma_val is not None and ma_val > 0:
                diff = current_price - ma_val
                res = MAResult(
                    ma_price=ma_val,
                    reached_target=current_price >= ma_val,
                    price_difference=round(diff, 2),
                    price_difference_percent=round((diff / ma_val) * 100, 2)
                )
                status = "✅达标" if res.reached_target else "⏳未达"
                logger.debug(f"[MA计算] {ma_type}: {ma_val} | 当前价: {current_price} | 偏离: {diff:.2f} ({res.price_difference_percent:.2f}%) | {status}")

        ma_results[ma_type] = res

    # 汇总日志
    enrich_elapsed = (time.time() - enrich_start) * 1000
    reached_count = sum(1 for r in ma_results.values() if r.reached_target)
    logger.info(f"[数据富化] 处理完成 | 股票: {stock.symbol} | 当前价: {current_price} | 达标: {reached_count}/{len(ma_types_list)} | 实时: {is_realtime} | 总耗时: {enrich_elapsed:.0f}ms")

    # 为了兼容前端或作为汇总展示，取第一个指标的结果作为汇总字段
    first_ma = ma_types_list[0] if ma_types_list else "MA5"
    main_res = ma_results.get(first_ma)

    # 生成买卖信号（使用 K 线数据）
    signal_data = None
    if kline_closes and len(kline_closes) >= 20:
        try:
            import pandas as pd
            # 构建 DataFrame 用于信号计算
            kline_df = pd.DataFrame({
                'open': kline_closes,
                'high': kline_closes,
                'low': kline_closes,
                'close': kline_closes,
                'volume': [0] * len(kline_closes)
            })
            signal_result = generate_signal(kline_df, current_price)
            # 只保留前端需要的字段
            signal_data = {
                'signal_type': signal_result['signal_type'],
                'strength': signal_result['strength'],
                'entry_price': signal_result.get('entry_price'),
                'stop_loss': signal_result.get('stop_loss'),
                'take_profit': signal_result.get('take_profit'),
                'triggers': signal_result.get('triggers', []),
                'message': signal_result.get('message', '')
            }
            logger.debug(f"[信号生成] 股票: {stock.symbol} | 信号: {signal_result['signal_type']} | 强度: {signal_result['strength']}")
        except Exception as e:
            logger.warning(f"[信号生成] 失败 | 股票: {stock.symbol} | 错误: {e}")

    return StockWithStatus(
        id=stock.id,
        symbol=stock.symbol,
        name=stock.name,
        ma_types=ma_types_list,
        ma_results=ma_results,
        group_ids=group_ids,
        group_names=group_names,
        ma_price=main_res.ma_price if main_res else None,
        current_price=current_price or stock.current_price,
        created_at=stock.created_at,
        updated_at=stock.updated_at,
        reached_target=main_res.reached_target if main_res else False,
        price_difference=main_res.price_difference if main_res else None,
        price_difference_percent=main_res.price_difference_percent if main_res else None,
        is_realtime=is_realtime,
        data_fetched_at=data_fetched_at,
        signal=signal_data
    )


def _should_refresh_price_threadsafe(
    stock: Stock,
    market: str,
    need_calc: bool,
    trading_day_cache: dict = None
) -> Tuple[bool, str]:
    """
    线程安全版本的 should_refresh_price

    使用预计算的 trading_day_cache 代替 db 访问

    Args:
        stock: 股票对象
        market: 市场类型 ("cn" 或 "us")
        need_calc: 是否需要计算（新增股票/指标时为True）
        trading_day_cache: 预计算的交易日状态缓存

    Returns:
        Tuple[bool, str]: (是否需要刷新, 原因说明)
    """
    # 1. 如果需要计算（新增股票/指标），直接获取数据
    if need_calc:
        return True, "新增股票或指标变更，获取最近交易日数据"

    # 2. 判断是否为交易日（使用预计算缓存）
    if trading_day_cache and market in trading_day_cache:
        is_trading, reason = trading_day_cache[market]
        if not is_trading:
            # 非交易日，不刷新，使用缓存
            return False, f"非交易日（{reason}），使用缓存数据"

    # 3. 如果在交易时间内，刷新获取实时数据
    if is_trading_time(market):
        return True, "交易时间内，实时获取最新价格"

    # 4. 非交易时间，检查是否需要更新收盘数据
    # 如果当前价格为空，需要获取
    if stock.current_price is None:
        return True, "当前价格为空，需要获取"

    # 检查数据是否已是最新的收盘数据
    if stock.updated_at is None:
        return True, "更新时间为空，需要获取"

    # 确保 stock.updated_at 是 timezone-aware
    beijing_tz = ZoneInfo("Asia/Shanghai")
    if stock.updated_at.tzinfo is None:
        # 假设数据库存储的是 UTC 时间
        last_update = stock.updated_at.replace(tzinfo=timezone.utc)
    else:
        last_update = stock.updated_at

    # 获取最近交易日收盘时间
    last_close_time = get_last_trading_day_close()

    # 如果更新时间早于最近收盘时间，需要刷新
    if last_update.astimezone(beijing_tz) < last_close_time:
        return True, f"数据过期，上次更新: {last_update.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M')}"

    return False, f"数据已是最新收盘数据，更新于: {last_update.astimezone(beijing_tz).strftime('%Y-%m-%d %H:%M')}"


# ============ 快照和报告服务 ============

def generate_daily_snapshots(db, force: bool = False, target_date: date = None) -> Tuple[int, int, str]:
    """
    为所有监控的股票生成快照

    Args:
        db: 数据库会话
        force: 是否强制刷新（即使已有快照）
        target_date: 目标日期，默认为今天。历史日期使用 K 线收盘价。

    Returns:
        Tuple[int, int, str]: (新建数量, 更新数量, 消息)
    """
    from .. import crud

    if target_date is None:
        target_date = date.today()

    # 判断是否为历史日期
    is_historical = target_date < date.today()

    # 获取所有股票
    stocks = db.query(Stock).all()

    if not stocks:
        return 0, 0, "没有监控的股票"

    created_count = 0
    updated_count = 0
    skipped_count = 0

    if is_historical:
        # 历史日期：使用 K 线数据
        logger.info(f"[快照生成] 生成历史快照 | 日期: {target_date} | 股票数: {len(stocks)}")

        for stock in stocks:
            # 检查是否已存在快照
            existing = crud.get_snapshot(db, stock.id, target_date)
            if existing and not force:
                skipped_count += 1
                continue

            # 解析 ma_types
            if stock.ma_types and stock.ma_types.strip():
                ma_types_list = [ma.strip() for ma in stock.ma_types.split(",") if ma.strip()]
            else:
                ma_types_list = ["MA5"]

            # 获取历史 K 线数据
            close_price, ma_results = fetch_historical_kline_data(stock.symbol, target_date, ma_types_list)

            if close_price is None or close_price <= 0:
                logger.warning(f"[快照生成] 跳过股票 {stock.symbol}，无法获取历史数据")
                skipped_count += 1
                continue

            # 添加数据来源标记
            for ma_type in ma_results:
                ma_results[ma_type]["data_source"] = "kline_close"

            # 保存快照
            crud.create_or_update_snapshot(
                db, stock.id, target_date,
                close_price,
                ma_results
            )

            if existing:
                updated_count += 1
            else:
                created_count += 1

    else:
        # 当天：使用实时数据
        logger.info(f"[快照生成] 生成今日快照 | 日期: {target_date} | 股票数: {len(stocks)}")

        # 使用并发获取所有股票的实时数据
        enriched_stocks = enrich_stocks_batch(stocks, force_refresh=True)

        for enriched in enriched_stocks:
            # 构建 ma_results 字典
            ma_results = {}
            for ma_type, result in enriched.ma_results.items():
                ma_results[ma_type] = {
                    "ma_price": result.ma_price,
                    "reached_target": result.reached_target,
                    "price_difference": result.price_difference,
                    "price_difference_percent": result.price_difference_percent,
                    "data_source": "realtime"
                }

            # 检查是否已存在快照
            existing = crud.get_snapshot(db, enriched.id, target_date)

            if existing:
                if force:
                    crud.create_or_update_snapshot(
                        db, enriched.id, target_date,
                        enriched.current_price or 0,
                        ma_results
                    )
                    updated_count += 1
            else:
                crud.create_or_update_snapshot(
                    db, enriched.id, target_date,
                    enriched.current_price or 0,
                    ma_results
                )
                created_count += 1

    message = f"已生成 {created_count} 个新快照"
    if updated_count > 0:
        message += f"，更新 {updated_count} 个现有快照"
    if skipped_count > 0:
        message += f"，跳过 {skipped_count} 个"

    logger.info(f"[快照生成] {message} | 日期: {target_date}")

    return created_count, updated_count, message


def get_daily_report(db, target_date: date = None, page: int = 1, page_size: int = 10) -> Dict:
    """
    生成每日报告

    Args:
        db: 数据库会话
        target_date: 目标日期，默认为今天
        page: 页码（用于达标个股分页），从1开始
        page_size: 每页条数，默认10，最大50

    Returns:
        Dict: 报告数据
    """
    from .. import crud

    if target_date is None:
        target_date = date.today()

    # 分页参数约束
    page = max(1, page)
    page_size = min(max(1, page_size), 50)  # 最小1，最大50

    # 获取目标日期快照
    target_snapshots = crud.get_snapshots_by_date(db, target_date)

    if not target_snapshots:
        return {
            "date": target_date,
            "has_today": False,
            "has_yesterday": False,
            "summary": {
                "total_stocks": 0,
                "reached_count": 0,
                "newly_reached": 0,
                "newly_below": 0,
                "continuous_below": 0,
                "reached_rate": 0.0,
                "reached_rate_change": 0.0
            },
            "newly_reached": [],
            "newly_below": [],
            "all_below_stocks": [],
            "reached_stocks": [],
            "total_reached": 0
        }

    # 获取前一交易日快照
    yesterday_snapshots = crud.get_previous_trading_day_snapshots(db, target_date)

    # 构建昨日数据索引（只保留每个股票的最新快照，即第一条记录）
    yesterday_data = {}
    for snap in yesterday_snapshots:
        if snap.snapshot_date < target_date and snap.stock_id not in yesterday_data:
            yesterday_data[snap.stock_id] = {
                "date": snap.snapshot_date,
                "ma_results": json.loads(snap.ma_results) if snap.ma_results else {}
            }

    has_yesterday = len(yesterday_data) > 0

    # 获取所有股票信息
    stocks = {s.id: s for s in db.query(Stock).all()}

    # 统计目标日期数据
    total_stocks = len(target_snapshots)
    reached_count = 0
    newly_reached_list = []
    newly_below_list = []

    # ========== 新增：达标个股聚合 ==========
    reached_stocks_map = {}  # stock_id -> {stock_info, indicators: []}

    # ========== 新增：未达标个股聚合（含分类） ==========
    all_below_stocks_list = []  # 所有未达标股票列表

    # 昨日达标率
    yesterday_reached_count = 0
    yesterday_total = 0

    for snap in target_snapshots:
        ma_results = json.loads(snap.ma_results) if snap.ma_results else {}

        # 判断是否达标（任一 MA 达标即算达标）
        is_reached = any(r.get("reached_target", False) for r in ma_results.values())
        if is_reached:
            reached_count += 1

        # ========== 收集达标指标的详细信息 ==========
        stock = stocks.get(snap.stock_id)
        if stock and is_reached:
            reached_indicators = []
            max_deviation = 0.0

            for ma_type, result in ma_results.items():
                if result.get("reached_target", False):
                    deviation = result.get("price_difference_percent", 0)

                    # 计算 reach_type：判断是新增达标还是持续达标
                    if snap.stock_id in yesterday_data:
                        yesterday_ma = yesterday_data[snap.stock_id]["ma_results"]
                        yesterday_result = yesterday_ma.get(ma_type, {})
                        yesterday_reached = yesterday_result.get("reached_target", False)

                        if yesterday_reached:
                            reach_type = "continuous_reach"  # 昨日达标 → 今日达标
                        else:
                            reach_type = "new_reach"  # 昨日未达标 → 今日达标
                    else:
                        reach_type = "new_reach"  # 无昨日数据，视为新增

                    reached_indicators.append({
                        "ma_type": ma_type,
                        "ma_price": result.get("ma_price", 0),
                        "price_difference_percent": deviation,
                        "reach_type": reach_type
                    })
                    max_deviation = max(max_deviation, abs(deviation))

            # 保留原始符号（正/负）
            original_max_deviation = max(
                (r["price_difference_percent"] for r in reached_indicators),
                key=abs,
                default=0
            )

            reached_stocks_map[snap.stock_id] = {
                "stock_id": snap.stock_id,
                "symbol": stock.symbol,
                "name": stock.name,
                "current_price": snap.price or 0,
                "max_deviation_percent": original_max_deviation,
                "reached_indicators": reached_indicators
            }

        # ========== 新增：收集所有未达标股票（含分类） ==========
        if stock:
            yesterday_ma = yesterday_data.get(snap.stock_id, {}).get("ma_results", {})

            for ma_type, today_result in ma_results.items():
                today_reached = today_result.get("reached_target", False)

                # 只处理未达标的 MA
                if not today_reached:
                    yesterday_result = yesterday_ma.get(ma_type, {})
                    yesterday_reached = yesterday_result.get("reached_target", False)

                    # 判断 fall_type
                    if snap.stock_id in yesterday_data and yesterday_reached:
                        fall_type = "new_fall"  # 昨日达标 → 今日不达标
                    else:
                        fall_type = "continuous_below"  # 持续未达标或无昨日数据

                    all_below_stocks_list.append({
                        "stock_id": snap.stock_id,
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "current_price": snap.price or 0,
                        "ma_type": ma_type,
                        "ma_price": today_result.get("ma_price", 0),
                        "price_difference_percent": today_result.get("price_difference_percent", 0),
                        "fall_type": fall_type
                    })

        # 对比昨日（保留原有逻辑用于 newly_reached 和 newly_below）
        if stock and snap.stock_id in yesterday_data:
            yesterday_ma = yesterday_data[snap.stock_id]["ma_results"]

            for ma_type, today_result in ma_results.items():
                today_reached = today_result.get("reached_target", False)
                yesterday_result = yesterday_ma.get(ma_type, {})
                yesterday_reached = yesterday_result.get("reached_target", False)

                # 检测变化
                if today_reached and not yesterday_reached:
                    # 新增达标
                    newly_reached_list.append({
                        "stock_id": snap.stock_id,
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "ma_type": ma_type,
                        "current_price": snap.price,
                        "ma_price": today_result.get("ma_price", 0),
                        "price_difference_percent": today_result.get("price_difference_percent", 0)
                    })
                elif not today_reached and yesterday_reached:
                    # 跌破均线（状态变化）
                    newly_below_list.append({
                        "stock_id": snap.stock_id,
                        "symbol": stock.symbol,
                        "name": stock.name,
                        "ma_type": ma_type,
                        "current_price": snap.price,
                        "ma_price": today_result.get("ma_price", 0),
                        "price_difference_percent": today_result.get("price_difference_percent", 0)
                    })

    # 计算昨日达标率
    if has_yesterday:
        for snap_data in yesterday_data.values():
            yesterday_total += 1
            if any(r.get("reached_target", False) for r in snap_data["ma_results"].values()):
                yesterday_reached_count += 1

    # 计算达标率变化
    today_rate = (reached_count / total_stocks * 100) if total_stocks > 0 else 0
    yesterday_rate = (yesterday_reached_count / yesterday_total * 100) if yesterday_total > 0 else 0
    rate_change = today_rate - yesterday_rate if has_yesterday else 0

    # ========== 新增：排序 + 分页 ==========
    # 按偏离度降序排序（偏离越大越靠前）
    all_reached_stocks = sorted(
        reached_stocks_map.values(),
        key=lambda x: abs(x["max_deviation_percent"]),
        reverse=True
    )

    total_reached = len(all_reached_stocks)

    # 分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_reached_stocks = all_reached_stocks[start_idx:end_idx]

    # ========== 新增：未达标股票排序 ==========
    # 按 MA 类型排序，然后按 fall_type（new_fall 优先），最后按偏离度（最负优先）
    def get_ma_number(item):
        """提取 MA 类型中的数字用于排序"""
        import re
        match = re.search(r'\d+', item.get("ma_type", "MA0"))
        return int(match.group()) if match else 0

    def below_sort_key(item):
        """未达标股票排序键"""
        ma_num = get_ma_number(item)
        # fall_type: new_fall=0, continuous_below=1（new_fall 优先）
        fall_order = 0 if item.get("fall_type") == "new_fall" else 1
        # 偏离度升序（最负的排前面）
        deviation = item.get("price_difference_percent", 0)
        return (ma_num, fall_order, deviation)

    sorted_all_below_stocks = sorted(all_below_stocks_list, key=below_sort_key)

    # 计算持续未达标数量
    continuous_below_count = sum(1 for item in all_below_stocks_list if item.get("fall_type") == "continuous_below")

    return {
        "date": target_date,
        "has_today": True,
        "has_yesterday": has_yesterday,
        "summary": {
            "total_stocks": total_stocks,
            "reached_count": reached_count,
            "newly_reached": len(newly_reached_list),
            "newly_below": len(newly_below_list),
            "continuous_below": continuous_below_count,
            "reached_rate": round(today_rate, 1),
            "reached_rate_change": round(rate_change, 1)
        },
        "newly_reached": newly_reached_list,
        "newly_below": newly_below_list,
        "all_below_stocks": sorted_all_below_stocks,
        "reached_stocks": paginated_reached_stocks,
        "total_reached": total_reached
    }
