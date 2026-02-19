"""
买卖信号生成服务

基于技术指标生成买入/卖出信号，包含具体价位建议。
支持两种模式：
1. 规则引擎模式：使用数据库中配置的规则（推荐）
2. 硬编码模式：使用内置规则（兼容旧逻辑）
"""

import logging
import json
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime

from .indicators import calc_all_indicators
from .rule_engine import RuleEngine

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ============ 硬编码信号检测（保留作为 fallback） ============

def detect_buy_signals(indicators: Dict[str, Any], current_price: float) -> List[Dict[str, Any]]:
    """
    检测买入信号（硬编码规则，作为 fallback）

    Args:
        indicators: 技术指标计算结果
        current_price: 当前价格

    Returns:
        List[Dict]: 买入信号列表
    """
    signals = []
    ma_indicators = indicators.get("indicators", {}).get("MA", {})
    boll_indicators = indicators.get("indicators", {}).get("Bollinger", {})
    all_signals = indicators.get("signals", [])

    # 1. MA 金叉买入
    for signal in all_signals:
        if signal.get("type") == "golden_cross" and "MA" in signal.get("name", ""):
            ma20_price = ma_indicators.get("MA20", current_price)
            signals.append({
                "trigger": "MA金叉",
                "entry_price": round(ma20_price, 2),
                "stop_loss": round(ma20_price * 0.95, 2),
                "take_profit": round(ma20_price * 1.08, 2),
                "strength": 3,
                "description": f"MA5上穿MA20，建议在MA20附近{ma20_price:.2f}买入"
            })

    # 2. RSI 超卖买入
    for signal in all_signals:
        if signal.get("type") == "oversold":
            rsi_value = signal.get("value", 0)
            entry = round(current_price * 0.98, 2)
            signals.append({
                "trigger": "RSI超卖",
                "entry_price": entry,
                "stop_loss": round(entry * 0.95, 2),
                "take_profit": round(current_price * 1.05, 2),
                "strength": 2,
                "description": f"RSI={rsi_value:.1f}，超卖区间，建议逢低买入"
            })

    # 3. 布林下轨买入
    for signal in all_signals:
        if signal.get("type") == "below_lower":
            lower_price = signal.get("price", current_price)
            signals.append({
                "trigger": "跌破布林下轨",
                "entry_price": round(lower_price, 2),
                "stop_loss": round(lower_price * 0.95, 2),
                "take_profit": round(boll_indicators.get("middle", current_price), 2),
                "strength": 3,
                "description": f"价格跌破布林下轨{lower_price:.2f}，可能反弹"
            })

    # 4. MACD 金叉买入
    for signal in all_signals:
        if signal.get("type") == "golden_cross" and "MACD" in signal.get("name", ""):
            signals.append({
                "trigger": "MACD金叉",
                "entry_price": round(current_price, 2),
                "stop_loss": round(current_price * 0.95, 2),
                "take_profit": round(current_price * 1.08, 2),
                "strength": 2,
                "description": "MACD金叉形成，趋势可能转强"
            })

    return signals


def detect_sell_signals(indicators: Dict[str, Any], current_price: float) -> List[Dict[str, Any]]:
    """
    检测卖出信号（硬编码规则，作为 fallback）

    Args:
        indicators: 技术指标计算结果
        current_price: 当前价格

    Returns:
        List[Dict]: 卖出信号列表
    """
    signals = []
    ma_indicators = indicators.get("indicators", {}).get("MA", {})
    boll_indicators = indicators.get("indicators", {}).get("Bollinger", {})
    all_signals = indicators.get("signals", [])

    # 1. MA 死叉卖出
    for signal in all_signals:
        if signal.get("type") == "dead_cross" and "MA" in signal.get("name", ""):
            ma20_price = ma_indicators.get("MA20", current_price)
            signals.append({
                "trigger": "MA死叉",
                "entry_price": round(ma20_price, 2),
                "stop_loss": None,  # 卖出信号无止损
                "take_profit": round(ma20_price * 0.95, 2),  # 回撤目标
                "strength": 3,
                "description": f"MA5下穿MA20，建议在MA20附近{ma20_price:.2f}减仓"
            })

    # 2. RSI 超买卖出
    for signal in all_signals:
        if signal.get("type") == "overbought":
            rsi_value = signal.get("value", 0)
            exit_price = round(current_price * 1.02, 2)
            signals.append({
                "trigger": "RSI超买",
                "entry_price": exit_price,
                "stop_loss": None,
                "take_profit": round(current_price * 0.98, 2),
                "strength": 2,
                "description": f"RSI={rsi_value:.1f}，超买区间，建议逢高减仓"
            })

    # 3. 布林上轨卖出
    for signal in all_signals:
        if signal.get("type") == "above_upper":
            upper_price = signal.get("price", current_price)
            signals.append({
                "trigger": "突破布林上轨",
                "entry_price": round(upper_price, 2),
                "stop_loss": None,
                "take_profit": round(boll_indicators.get("middle", current_price), 2),
                "strength": 3,
                "description": f"价格突破布林上轨{upper_price:.2f}，可能回调"
            })

    # 4. MACD 死叉卖出
    for signal in all_signals:
        if signal.get("type") == "dead_cross" and "MACD" in signal.get("name", ""):
            signals.append({
                "trigger": "MACD死叉",
                "entry_price": round(current_price, 2),
                "stop_loss": None,
                "take_profit": round(current_price * 0.95, 2),
                "strength": 2,
                "description": "MACD死叉形成，趋势可能转弱"
            })

    return signals


# ============ 信号生成函数 ============

def generate_signal(df, current_price: Optional[float] = None, rules: Optional[List] = None) -> Dict[str, Any]:
    """
    生成综合买卖信号

    Args:
        df: K线数据 DataFrame
        current_price: 当前价格（可选，默认使用最新收盘价）
        rules: 交易规则列表（可选，传入则使用规则引擎，否则使用硬编码逻辑）

    Returns:
        Dict: 综合信号结果
    """
    if df is None or len(df) < 20:
        return {
            "signal_type": "hold",
            "strength": 0,
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "triggers": [],
            "indicators": {},
            "message": "数据不足，无法生成信号"
        }

    # 如果传入了规则，使用规则引擎
    if rules is not None:
        return _generate_signal_with_engine(df, current_price, rules)

    # 否则使用硬编码逻辑（向后兼容）
    return _generate_signal_legacy(df, current_price)


def _generate_signal_with_engine(df, current_price: Optional[float], rules: List) -> Dict[str, Any]:
    """
    使用规则引擎生成信号

    Args:
        df: K线数据 DataFrame
        current_price: 当前价格
        rules: 交易规则列表

    Returns:
        Dict: 信号结果
    """
    engine = RuleEngine(rules)
    signal = engine.evaluate_all(df, current_price)

    # 确保返回格式与旧接口兼容
    return {
        "signal_type": signal.get("signal_type", "hold"),
        "strength": signal.get("strength", 0),
        "entry_price": signal.get("entry_price"),
        "stop_loss": signal.get("stop_loss"),
        "take_profit": signal.get("take_profit"),
        "triggers": signal.get("triggers", []),
        "indicators": signal.get("indicators", {}),
        "message": signal.get("message", ""),
        "rule_id": signal.get("rule_id"),
        "rule_name": signal.get("rule_name")
    }


def _generate_signal_legacy(df, current_price: Optional[float]) -> Dict[str, Any]:
    """
    使用硬编码逻辑生成信号（向后兼容）

    Args:
        df: K线数据 DataFrame
        current_price: 当前价格

    Returns:
        Dict: 信号结果
    """
    # 计算所有指标
    indicators = calc_all_indicators(df)

    if current_price is None:
        current_price = indicators.get("current_price", 0)

    # 检测买入和卖出信号
    buy_signals = detect_buy_signals(indicators, current_price)
    sell_signals = detect_sell_signals(indicators, current_price)

    # 综合判断
    if len(buy_signals) > len(sell_signals):
        # 买入信号占优
        best_signal = max(buy_signals, key=lambda x: x["strength"])
        total_strength = min(sum(s["strength"] for s in buy_signals), 5)

        return {
            "signal_type": "buy",
            "strength": total_strength,
            "entry_price": best_signal["entry_price"],
            "stop_loss": best_signal["stop_loss"],
            "take_profit": best_signal["take_profit"],
            "triggers": [s["trigger"] for s in buy_signals],
            "indicators": indicators["indicators"],
            "message": "；".join([s["description"] for s in buy_signals[:2]])
        }

    elif len(sell_signals) > len(buy_signals):
        # 卖出信号占优
        best_signal = max(sell_signals, key=lambda x: x["strength"])
        total_strength = min(sum(s["strength"] for s in sell_signals), 5)

        return {
            "signal_type": "sell",
            "strength": total_strength,
            "entry_price": best_signal["entry_price"],
            "stop_loss": best_signal.get("stop_loss"),
            "take_profit": best_signal["take_profit"],
            "triggers": [s["trigger"] for s in sell_signals],
            "indicators": indicators["indicators"],
            "message": "；".join([s["description"] for s in sell_signals[:2]])
        }

    else:
        # 持有
        return {
            "signal_type": "hold",
            "strength": 0,
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "triggers": [],
            "indicators": indicators["indicators"],
            "message": "当前无明显买卖信号，建议持有观望"
        }


def generate_signal_with_db(df, db: "Session", current_price: Optional[float] = None) -> Dict[str, Any]:
    """
    使用数据库中的规则生成信号（推荐接口）

    Args:
        df: K线数据 DataFrame
        db: 数据库 Session
        current_price: 当前价格（可选）

    Returns:
        Dict: 综合信号结果
    """
    from ..models import TradingRule

    # 从数据库加载启用的规则
    rules = db.query(TradingRule).filter(TradingRule.enabled == True).all()

    if not rules:
        logger.warning("数据库中没有启用的交易规则，使用默认硬编码逻辑")
        return generate_signal(df, current_price)

    return generate_signal(df, current_price, rules=rules)


def format_signal_for_db(signal_result: Dict[str, Any], stock_id: int, signal_date: date) -> Dict[str, Any]:
    """
    格式化信号结果用于数据库存储

    Args:
        signal_result: generate_signal 的返回结果
        stock_id: 股票 ID
        signal_date: 信号日期

    Returns:
        Dict: 数据库存储格式
    """
    return {
        "stock_id": stock_id,
        "signal_date": signal_date,
        "signal_type": signal_result["signal_type"],
        "current_price": signal_result.get("current_price"),
        "entry_price": signal_result.get("entry_price"),
        "stop_loss": signal_result.get("stop_loss"),
        "take_profit": signal_result.get("take_profit"),
        "strength": signal_result["strength"],
        "triggers": json.dumps(signal_result["triggers"], ensure_ascii=False),
        "indicators": json.dumps(signal_result.get("indicators", {}), ensure_ascii=False),
    }
