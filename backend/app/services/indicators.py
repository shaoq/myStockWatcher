"""
技术指标计算服务

支持多种技术指标计算：
- MA: 移动平均线
- MACD: 指数平滑异同移动平均线
- RSI: 相对强弱指标
- KDJ: 随机指标
- Bollinger: 布林带
"""

import logging
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def calc_ma(df: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> Dict[str, Any]:
    """
    计算移动平均线

    Args:
        df: K线数据，需包含 'close' 列
        periods: 计算周期列表

    Returns:
        Dict: 包含各周期 MA 值和交叉信号
    """
    if df is None or len(df) < max(periods):
        return {"values": {}, "signals": []}

    result = {"values": {}, "signals": []}
    close = df['close']

    for period in periods:
        if len(close) >= period:
            ma_value = close.rolling(window=period).mean().iloc[-1]
            result["values"][f"MA{period}"] = round(float(ma_value), 2)

    # 检测 MA 金叉/死叉 (MA5 vs MA20)
    if len(close) >= 20:
        ma5 = close.rolling(window=5).mean()
        ma20 = close.rolling(window=20).mean()

        # 前一日和当日的关系
        prev_ma5, prev_ma20 = ma5.iloc[-2], ma20.iloc[-2]
        curr_ma5, curr_ma20 = ma5.iloc[-1], ma20.iloc[-1]

        if prev_ma5 <= prev_ma20 and curr_ma5 > curr_ma20:
            result["signals"].append({
                "type": "golden_cross",
                "name": "MA金叉",
                "period": "MA5/MA20",
                "price": round(float(curr_ma20), 2)
            })
        elif prev_ma5 >= prev_ma20 and curr_ma5 < curr_ma20:
            result["signals"].append({
                "type": "dead_cross",
                "name": "MA死叉",
                "period": "MA5/MA20",
                "price": round(float(curr_ma20), 2)
            })

    return result


def calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Any]:
    """
    计算 MACD 指标

    Args:
        df: K线数据，需包含 'close' 列
        fast: 快线周期
        slow: 慢线周期
        signal: 信号线周期

    Returns:
        Dict: 包含 DIF、DEA、MACD 值和交叉信号
    """
    min_len = slow + signal
    if df is None or len(df) < min_len:
        return {"values": {}, "signals": []}

    result = {"values": {}, "signals": []}
    close = df['close']

    # 计算 EMA
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    # DIF = 快线EMA - 慢线EMA
    dif = ema_fast - ema_slow

    # DEA = DIF 的 EMA
    dea = dif.ewm(span=signal, adjust=False).mean()

    # MACD 柱 = 2 * (DIF - DEA)
    macd_hist = 2 * (dif - dea)

    result["values"] = {
        "DIF": round(float(dif.iloc[-1]), 4),
        "DEA": round(float(dea.iloc[-1]), 4),
        "MACD": round(float(macd_hist.iloc[-1]), 4)
    }

    # 检测 MACD 金叉/死叉
    if len(dif) >= 2:
        prev_dif, prev_dea = dif.iloc[-2], dea.iloc[-2]
        curr_dif, curr_dea = dif.iloc[-1], dea.iloc[-1]

        if prev_dif <= prev_dea and curr_dif > curr_dea:
            result["signals"].append({
                "type": "golden_cross",
                "name": "MACD金叉",
                "price": None
            })
        elif prev_dif >= prev_dea and curr_dif < curr_dea:
            result["signals"].append({
                "type": "dead_cross",
                "name": "MACD死叉",
                "price": None
            })

    return result


def calc_rsi(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
    """
    计算 RSI 相对强弱指标

    Args:
        df: K线数据，需包含 'close' 列
        period: 计算周期

    Returns:
        Dict: 包含 RSI 值和超买超卖信号
    """
    if df is None or len(df) < period + 1:
        return {"values": {}, "signals": []}

    result = {"values": {}, "signals": []}
    close = df['close']

    # 计算价格变化
    delta = close.diff()

    # 分离上涨和下跌
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)

    # 计算平均上涨和下跌
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    # 计算 RS 和 RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi_value = rsi.iloc[-1]
    result["values"] = {"RSI": round(float(rsi_value), 2)}

    # 判断超买超卖
    if rsi_value < 30:
        result["signals"].append({
            "type": "oversold",
            "name": "RSI超卖",
            "value": round(float(rsi_value), 2),
            "threshold": 30
        })
    elif rsi_value > 70:
        result["signals"].append({
            "type": "overbought",
            "name": "RSI超买",
            "value": round(float(rsi_value), 2),
            "threshold": 70
        })

    return result


def calc_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Dict[str, Any]:
    """
    计算 KDJ 随机指标

    Args:
        df: K线数据，需包含 'high', 'low', 'close' 列
        n: RSV 周期
        m1: K 值平滑周期
        m2: D 值平滑周期

    Returns:
        Dict: 包含 K、D、J 值和交叉信号
    """
    if df is None or len(df) < n:
        return {"values": {}, "signals": []}

    result = {"values": {}, "signals": []}

    # 计算 RSV
    low_n = df['low'].rolling(window=n).min()
    high_n = df['high'].rolling(window=n).max()
    rsv = (df['close'] - low_n) / (high_n - low_n) * 100

    # 计算 K、D、J
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d

    result["values"] = {
        "K": round(float(k.iloc[-1]), 2),
        "D": round(float(d.iloc[-1]), 2),
        "J": round(float(j.iloc[-1]), 2)
    }

    # 检测 KDJ 金叉/死叉
    if len(k) >= 2:
        prev_k, prev_d = k.iloc[-2], d.iloc[-2]
        curr_k, curr_d = k.iloc[-1], d.iloc[-1]

        if prev_k <= prev_d and curr_k > curr_d:
            result["signals"].append({
                "type": "golden_cross",
                "name": "KDJ金叉",
                "price": None
            })
        elif prev_k >= prev_d and curr_k < curr_d:
            result["signals"].append({
                "type": "dead_cross",
                "name": "KDJ死叉",
                "price": None
            })

    return result


def calc_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
    """
    计算布林带指标

    Args:
        df: K线数据，需包含 'close' 列
        period: 计算周期
        std_dev: 标准差倍数

    Returns:
        Dict: 包含上轨、中轨、下轨和突破信号
    """
    if df is None or len(df) < period:
        return {"values": {}, "signals": []}

    result = {"values": {}, "signals": []}
    close = df['close']

    # 计算中轨（MA）
    middle = close.rolling(window=period).mean()

    # 计算标准差
    std = close.rolling(window=period).std()

    # 计算上下轨
    upper = middle + std_dev * std
    lower = middle - std_dev * std

    current_price = close.iloc[-1]
    upper_val = upper.iloc[-1]
    middle_val = middle.iloc[-1]
    lower_val = lower.iloc[-1]

    result["values"] = {
        "upper": round(float(upper_val), 2),
        "middle": round(float(middle_val), 2),
        "lower": round(float(lower_val), 2),
        "width": round(float(upper_val - lower_val), 2)
    }

    # 检测突破信号
    if current_price < lower_val:
        result["signals"].append({
            "type": "below_lower",
            "name": "跌破布林下轨",
            "price": round(float(lower_val), 2)
        })
    elif current_price > upper_val:
        result["signals"].append({
            "type": "above_upper",
            "name": "突破布林上轨",
            "price": round(float(upper_val), 2)
        })

    return result


def calc_all_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """
    计算所有技术指标

    Args:
        df: K线数据，需包含 'open', 'high', 'low', 'close', 'volume' 列

    Returns:
        Dict: 包含所有指标和信号
    """
    if df is None or len(df) < 5:
        return {"indicators": {}, "signals": [], "current_price": None}

    result = {
        "indicators": {},
        "signals": [],
        "current_price": round(float(df['close'].iloc[-1]), 2)
    }

    # 计算各指标
    ma_result = calc_ma(df)
    macd_result = calc_macd(df)
    rsi_result = calc_rsi(df)
    kdj_result = calc_kdj(df)
    boll_result = calc_bollinger(df)

    # 汇总指标值
    result["indicators"]["MA"] = ma_result.get("values", {})
    result["indicators"]["MACD"] = macd_result.get("values", {})
    result["indicators"]["RSI"] = rsi_result.get("values", {})
    result["indicators"]["KDJ"] = kdj_result.get("values", {})
    result["indicators"]["Bollinger"] = boll_result.get("values", {})

    # 汇总信号
    for signal in ma_result.get("signals", []):
        result["signals"].append(signal)
    for signal in macd_result.get("signals", []):
        result["signals"].append(signal)
    for signal in rsi_result.get("signals", []):
        result["signals"].append(signal)
    for signal in kdj_result.get("signals", []):
        result["signals"].append(signal)
    for signal in boll_result.get("signals", []):
        result["signals"].append(signal)

    return result
