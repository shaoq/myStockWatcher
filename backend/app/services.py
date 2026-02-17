"""业务逻辑服务层 - 已升级为实时行情+动态均线计算 + 缓存优化 + 交易时间智能缓存 + 并发优化"""
import requests
import json
import re
import logging
import time
from typing import Optional, Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from .schemas import StockWithStatus
from .models import Stock
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo
from cachetools import TTLCache

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
    from . import crud

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


def is_trading_day(db, target_date: date = None) -> Tuple[bool, str]:
    """
    判断指定日期是否为交易日（多层数据源 + 3层兜底）

    数据源优先级：
    1. 数据库缓存（最准确，已同步）
    2. exchange_calendars 快速判断（备用）
    3. 周末判断（基础兜底）

    Args:
        db: 数据库会话
        target_date: 目标日期，默认为今天

    Returns:
        Tuple[bool, str]: (是否为交易日, 原因说明)
    """
    from . import crud

    if target_date is None:
        target_date = date.today()

    year = target_date.year

    # 第1层：检查数据库缓存
    if not crud.is_year_cached(db, year):
        # 缓存不存在，尝试获取并缓存
        logger.info(f"[交易日历] {year} 年缓存不存在，开始获取")
        refresh_trading_calendar(db, year)

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


def fetch_historical_kline_data(symbol: str, target_date: date, ma_types: List[str] = None) -> Tuple[Optional[float], Optional[Dict]]:
    """
    获取历史 K 线数据，用于生成历史快照

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

    code, market = normalize_symbol_for_sina(symbol)

    # 计算 K 线数据长度（取最大 MA 周期 + 额外天数以确保覆盖目标日期）
    max_ma_period = 5  # 默认值
    for ma in ma_types:
        match = re.search(r'\d+', ma)
        if match:
            max_ma_period = max(max_ma_period, int(match.group()))

    # 获取足够的 K 线数据（目标日期前后各取一些）
    datalen = max_ma_period + 30  # 多取一些确保有目标日期的数据

    if market == "cn":
        url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=240&ma=no&datalen={datalen}"
    else:
        url = f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/IO.Direct.Quotes.getKLineData?symbol={code}&scale=240&ma=no&datalen={datalen}"

    response, _ = _http_get(url, "历史K线数据", symbol=symbol)

    if response is None:
        logger.warning(f"[历史K线数据] 获取失败 | 股票: {symbol} | 日期: {target_date}")
        return None, None

    try:
        if market == "us":
            match = re.search(r'\[.*\]', response.text)
            data = json.loads(match.group()) if match else []
        else:
            data = response.json()

        if not data or not isinstance(data, list):
            logger.warning(f"[历史K线数据] 数据为空 | 股票: {symbol}")
            return None, None

        # 查找目标日期的 K 线数据
        target_date_str = target_date.strftime("%Y-%m-%d")
        target_kline = None
        target_index = -1

        for i, item in enumerate(data):
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
                closes.append(float(data[j].get('close', 0)))

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

        logger.info(f"[历史K线数据] 获取成功 | 股票: {symbol} | 日期: {target_date} | 收盘价: {close_price} | MA数量: {len(ma_results)}")

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


def should_refresh_price(stock: Stock, market: str) -> Tuple[bool, str]:
    """
    判断是否需要刷新价格数据

    Args:
        stock: 股票对象
        market: 市场类型 ("cn" 或 "us")

    Returns:
        Tuple[bool, str]: (是否需要刷新, 原因说明)
    """
    # 1. 如果在交易时间内，始终刷新
    if is_trading_time(market):
        return True, "交易时间内，实时获取最新价格"

    # 2. 如果当前价格为空，需要获取
    if stock.current_price is None:
        return True, "当前价格为空，需要获取"

    # 3. 非交易时间，检查数据是否已是最新的收盘数据
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

# 创建一个带有 User-Agent 的 session
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})


def _http_get(url: str, service_name: str, headers: dict = None, timeout: int = 5, symbol: str = None) -> Tuple[Optional[requests.Response], float]:
    """
    统一的 HTTP GET 请求方法，带日志记录

    Args:
        url: 请求 URL
        service_name: 服务名称（用于日志标识）
        headers: 请求头
        timeout: 超时时间（秒）
        symbol: 股票代码（可选，用于日志）

    Returns:
        Tuple[Optional[Response], float]: (响应对象, 耗时毫秒)
    """
    start_time = time.time()
    symbol_info = f" | 股票: {symbol}" if symbol else ""

    try:
        logger.info(f"[{service_name}] 请求开始{symbol_info} | URL: {url}")
        response = session.get(url, headers=headers or {}, timeout=timeout)
        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            logger.info(f"[{service_name}] 请求成功{symbol_info} | 状态码: {response.status_code} | 耗时: {elapsed_ms:.0f}ms")
        else:
            logger.warning(f"[{service_name}] 请求失败{symbol_info} | 状态码: {response.status_code} | 耗时: {elapsed_ms:.0f}ms | URL: {url}")

        return response, elapsed_ms
    except requests.exceptions.Timeout:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(f"[{service_name}] 请求超时{symbol_info} | 耗时: {elapsed_ms:.0f}ms | URL: {url}")
        return None, elapsed_ms
    except requests.exceptions.RequestException as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(f"[{service_name}] 请求异常{symbol_info} | 耗时: {elapsed_ms:.0f}ms | 错误: {e} | URL: {url}")
        return None, elapsed_ms


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
        if symbol.startswith(('6', '9')): return f"sh{symbol}", "cn"
        if symbol.startswith(('0', '3')): return f"sz{symbol}", "cn"
        if symbol.startswith(('8', '4')): return f"bj{symbol}", "cn"
    return symbol, "us"


def fetch_realtime_data(symbol: str, use_cache: bool = True) -> Tuple[Optional[float], Optional[str]]:
    """获取实时价格和股票名称（带缓存）"""
    # 检查缓存
    if use_cache and symbol in price_cache:
        logger.info(f"[新浪实时行情] 缓存命中 | 股票: {symbol}")
        return price_cache[symbol]

    code, market = normalize_symbol_for_sina(symbol)
    url = f"http://hq.sinajs.cn/list={code if market == 'cn' else 'gb_' + code.lower()}"
    headers = {'Referer': 'http://finance.sina.com.cn'}

    response, elapsed_ms = _http_get(url, "新浪实时行情", headers, symbol=symbol)

    if response is None:
        logger.warning(f"[新浪实时行情] 获取失败 | 股票: {symbol}")
        return None, None

    try:
        match = re.search(r'="([^"]+)"', response.text)
        if match:
            data = match.group(1).split(',')
            if market == "cn" and len(data) > 3:
                price, name = float(data[3]), data[0]
                # 存入缓存
                price_cache[symbol] = (price, name)
                logger.info(f"[新浪实时行情] 解析成功 | 股票: {symbol} | 名称: {name} | 价格: {price} | 耗时: {elapsed_ms:.0f}ms")
                return price, name
            elif market == "us" and len(data) > 1:
                price, name = float(data[1]), data[0]
                # 存入缓存
                price_cache[symbol] = (price, name)
                logger.info(f"[新浪实时行情] 解析成功 | 股票: {symbol} | 名称: {name} | 价格: {price} | 耗时: {elapsed_ms:.0f}ms")
                return price, name
        logger.warning(f"[新浪实时行情] 解析失败 | 股票: {symbol} | 响应内容异常 | 耗时: {elapsed_ms:.0f}ms")
        return None, None
    except Exception as e:
        logger.error(f"[新浪实时行情] 解析异常 | 股票: {symbol} | 错误: {e}")
        return None, None


def fetch_stock_name(symbol: str) -> Optional[str]:
    """获取股票中文名称"""
    _, name = fetch_realtime_data(symbol)
    return name


def fetch_stock_data_from_api(symbol: str, ma_type: str = "MA5", current_price: Optional[float] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    获取实时价格并动态计算包含今日数据的均线值
    current_price: 可选，如果已获取过实时价格可直接传入，避免重复请求
    """
    code, market = normalize_symbol_for_sina(symbol)

    # 安全提取 MA 周期数字
    match = re.search(r'\d+', ma_type)
    if not match:
        logger.warning(f"[新浪K线数据] 无效的指标格式: {ma_type} | 股票: {symbol}，使用默认值 5")
        ma_period = 5
    else:
        ma_period = int(match.group())

    # 1. 获取今日实时价格（如果未提供）
    if current_price is None:
        current_price, _ = fetch_realtime_data(symbol)
        if current_price is None:
            return None, None

    # 2. 获取历史 K 线数据以计算均线
    datalen = ma_period + 2
    if market == "cn":
        url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=240&ma=no&datalen={datalen}"
    else:
        url = f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/IO.Direct.Quotes.getKLineData?symbol={code}&scale=240&ma=no&datalen={datalen}"

    response, _ = _http_get(url, "新浪K线数据", symbol=symbol)

    if response is None:
        return current_price, None

    try:
        if market == "us":
            match = re.search(r'\[.*\]', response.text)
            data = json.loads(match.group()) if match else []
        else:
            data = response.json()

        if not data or not isinstance(data, list):
            logger.warning(f"[新浪K线数据] 数据为空 | 股票: {symbol}")
            return current_price, None

        # 提取收盘价序列
        closes = [float(item['close']) for item in data]
        today_str = datetime.now().strftime("%Y-%m-%d")
        last_day = data[-1]['day'].split(' ')[0]

        if last_day == today_str:
            final_closes = closes[-ma_period:]
        else:
            final_closes = closes[-(ma_period-1):] + [current_price]

        if len(final_closes) < ma_period:
            return current_price, None

        ma_price = round(sum(final_closes) / ma_period, 2)
        logger.info(f"[新浪K线数据] MA计算成功 | 股票: {symbol} | {ma_type}: {ma_price} | 数据点数: {len(final_closes)}")
        return current_price, ma_price

    except Exception as e:
        logger.error(f"[新浪K线数据] 解析异常 | 股票: {symbol} | 错误: {e}")
        return current_price, None


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


def enrich_stock_with_status(stock: Stock, force_refresh: bool = False) -> StockWithStatus:
    """为股票对象添加实时价格和多指标状态信息（带缓存 + 交易时间智能缓存）

    Args:
        stock: 股票对象
        force_refresh: 是否强制刷新（绕过缓存），默认 False

    Returns:
        StockWithStatus: 包含 is_realtime 字段，标识数据是否为实时获取
    """
    from .schemas import MAResult

    # 获取市场类型
    _, market = normalize_symbol_for_sina(stock.symbol)

    # 智能缓存决策：判断是否需要刷新数据
    is_realtime = False
    refresh_reason = ""

    if force_refresh:
        is_realtime = True
        refresh_reason = "强制刷新"
    else:
        need_refresh, refresh_reason = should_refresh_price(stock, market)
        if need_refresh:
            is_realtime = True

    logger.info(f"[数据富化] 开始处理 | 股票: {stock.symbol} ({stock.name}) | 指标: {stock.ma_types} | 实时模式: {is_realtime} | 原因: {refresh_reason}")
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
    if is_realtime:
        # 【实时模式】请求 API 获取最新数据
        current_price, _ = fetch_realtime_data(stock.symbol, use_cache=False)
    else:
        # 【缓存模式】使用数据库中已有的价格
        current_price = stock.current_price

        # 【修复】如果缓存价格为 None，强制重新获取
        if current_price is None:
            logger.warning(f"[智能缓存] 缓存价格为空，强制刷新 | 股票: {stock.symbol}")
            current_price, _ = fetch_realtime_data(stock.symbol, use_cache=False)
            is_realtime = True  # 标记为实时获取
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

    code, _ = normalize_symbol_for_sina(stock.symbol)
    kline_closes = None

    # K线缓存键：股票代码:日期:最大周期（确保不同指标组合使用独立缓存）
    cache_key = f"{stock.symbol}:{date.today()}:{max_ma_period}"

    # 检查 K 线缓存（仅在非实时模式下使用缓存）
    if not is_realtime and cache_key in kline_cache:
        logger.info(f"[新浪K线数据] 缓存命中 | 股票: {stock.symbol} | 周期: {max_ma_period}")
        kline_closes = kline_cache[cache_key]
    else:
        # 缓存未命中或实时模式，请求 API
        datalen = max_ma_period + 2
        if market == "cn":
            url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=240&ma=no&datalen={datalen}"
        else:
            url = f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/IO.Direct.Quotes.getKLineData?symbol={code}&scale=240&ma=no&datalen={datalen}"

        response, kline_elapsed = _http_get(url, "新浪K线数据", symbol=stock.symbol)

        if response:
            try:
                if market == "us":
                    match = re.search(r'\[.*\]', response.text)
                    data = json.loads(match.group()) if match else []
                else:
                    data = response.json()

                if data and isinstance(data, list):
                    kline_closes = [float(item['close']) for item in data]
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    last_day = data[-1]['day'].split(' ')[0]
                    if last_day != today_str and current_price is not None:
                        kline_closes.append(current_price)
                    # 存入缓存
                    kline_cache[cache_key] = kline_closes
                    logger.info(f"[新浪K线数据] 获取成功 | 股票: {stock.symbol} | K线数量: {len(kline_closes)} | 耗时: {kline_elapsed:.0f}ms")
            except Exception as e:
                logger.error(f"[新浪K线数据] 解析异常 | 股票: {stock.symbol} | 错误: {e}")

    # 【优化3】本地计算所有 MA 值（无需再次请求 API）
    for ma_type in ma_types_list:
        ma_period = int(re.search(r'\d+', ma_type).group())
        res = MAResult(reached_target=False)

        if current_price is not None and kline_closes and len(kline_closes) >= ma_period:
            final_closes = kline_closes[-ma_period:]
            ma_val = round(sum(final_closes) / ma_period, 2)

            if ma_val > 0:
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
        is_realtime=is_realtime
    )


def enrich_stocks_batch(stocks: List[Stock], force_refresh: bool = False, max_workers: int = 10) -> List[StockWithStatus]:
    """
    并发富化多只股票的状态信息

    Args:
        stocks: 股票对象列表
        force_refresh: 是否强制刷新（绕过缓存）
        max_workers: 最大并发线程数，默认10

    Returns:
        List[StockWithStatus]: 富化后的股票状态列表
    """
    if not stocks:
        return []

    batch_start = time.time()
    logger.info(f"[批量富化] 开始处理 {len(stocks)} 只股票 | 并发数: {max_workers} | 强制刷新: {force_refresh}")

    results = [None] * len(stocks)  # 预分配结果列表，保持顺序

    def process_stock(index, stock):
        """处理单只股票并返回带索引的结果"""
        try:
            result = enrich_stock_with_status(stock, force_refresh=force_refresh)
            return (index, result)
        except Exception as e:
            logger.error(f"[批量富化] 处理失败 | 股票: {stock.symbol} | 错误: {e}")
            return (index, None)

    # 使用线程池并发处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(process_stock, i, stock): i
            for i, stock in enumerate(stocks)
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
    from . import crud

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


def get_daily_report(db, target_date: date = None) -> Dict:
    """
    生成每日报告

    Args:
        db: 数据库会话
        target_date: 目标日期，默认为今天

    Returns:
        Dict: 报告数据
    """
    from . import crud

    if target_date is None:
        target_date = date.today()

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
                "reached_rate": 0.0,
                "reached_rate_change": 0.0
            },
            "newly_reached": [],
            "newly_below": []
        }

    # 获取前一交易日快照
    yesterday_snapshots = crud.get_previous_trading_day_snapshots(db, target_date)

    # 构建昨日数据索引
    yesterday_data = {}
    for snap in yesterday_snapshots:
        if snap.snapshot_date < target_date:
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

    # 昨日达标率
    yesterday_reached_count = 0
    yesterday_total = 0

    for snap in target_snapshots:
        ma_results = json.loads(snap.ma_results) if snap.ma_results else {}

        # 判断是否达标（任一 MA 达标即算达标）
        is_reached = any(r.get("reached_target", False) for r in ma_results.values())
        if is_reached:
            reached_count += 1

        # 对比昨日
        stock = stocks.get(snap.stock_id)
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
                    # 跌破均线
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

    return {
        "date": target_date,
        "has_today": True,
        "has_yesterday": has_yesterday,
        "summary": {
            "total_stocks": total_stocks,
            "reached_count": reached_count,
            "newly_reached": len(newly_reached_list),
            "newly_below": len(newly_below_list),
            "reached_rate": round(today_rate, 1),
            "reached_rate_change": round(rate_change, 1)
        },
        "newly_reached": newly_reached_list,
        "newly_below": newly_below_list
    }

    if not today_snapshots:
        return {
            "date": today,
            "has_today": False,
            "has_yesterday": False,
            "summary": {
                "total_stocks": 0,
                "reached_count": 0,
                "newly_reached": 0,
                "newly_below": 0,
                "reached_rate": 0.0,
                "reached_rate_change": 0.0
            },
            "newly_reached": [],
            "newly_below": []
        }

    # 获取昨日快照（按日期降序取第一个不是今天的）
    yesterday_snapshots = crud.get_previous_trading_day_snapshots(db, today)

    # 构建昨日数据索引
    yesterday_data = {}
    for snap in yesterday_snapshots:
        if snap.snapshot_date < today:
            yesterday_data[snap.stock_id] = {
                "date": snap.snapshot_date,
                "ma_results": json.loads(snap.ma_results) if snap.ma_results else {}
            }

    has_yesterday = len(yesterday_data) > 0

    # 获取所有股票信息
    stocks = {s.id: s for s in db.query(Stock).all()}

    # 统计今日数据
    total_stocks = len(today_snapshots)
    reached_count = 0
    newly_reached_list = []
    newly_below_list = []

    # 昨日达标率
    yesterday_reached_count = 0
    yesterday_total = 0

    for snap in today_snapshots:
        ma_results = json.loads(snap.ma_results) if snap.ma_results else {}

        # 判断今日是否达标（任一 MA 达标即算达标）
        is_reached = any(r.get("reached_target", False) for r in ma_results.values())
        if is_reached:
            reached_count += 1

        # 对比昨日
        stock = stocks.get(snap.stock_id)
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
                    # 跌破均线
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

    return {
        "date": today,
        "has_today": True,
        "has_yesterday": has_yesterday,
        "summary": {
            "total_stocks": total_stocks,
            "reached_count": reached_count,
            "newly_reached": len(newly_reached_list),
            "newly_below": len(newly_below_list),
            "reached_rate": round(today_rate, 1),
            "reached_rate_change": round(rate_change, 1)
        },
        "newly_reached": newly_reached_list,
        "newly_below": newly_below_list
    }


def get_trend_data(db, days: int = 7) -> List[Dict]:
    """
    获取趋势数据

    Args:
        db: 数据库会话
        days: 天数

    Returns:
        List[Dict]: 趋势数据点列表
    """
    from . import crud

    # 获取快照数据
    snapshots_by_date = crud.get_snapshots_for_trend(db, days)

    if not snapshots_by_date:
        return []

    # 按日期排序，取最近 N 个交易日
    sorted_dates = sorted(snapshots_by_date.keys(), reverse=True)[:days]
    sorted_dates.reverse()  # 从旧到新排列

    trend_data = []
    for d in sorted_dates:
        snapshots = snapshots_by_date[d]
        total = len(snapshots)
        reached = 0

        for snap in snapshots:
            ma_results = json.loads(snap.ma_results) if snap.ma_results else {}
            if any(r.get("reached_target", False) for r in ma_results.values()):
                reached += 1

        trend_data.append({
            "date": d.strftime("%m/%d"),
            "reached_count": reached,
            "reached_rate": round(reached / total * 100, 1) if total > 0 else 0
        })

    return trend_data
