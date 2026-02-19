"""
规则引擎服务

解析 JSON 格式的规则配置，执行条件判断，计算价位，生成买卖信号。
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import date

from .indicators import calc_all_indicators

logger = logging.getLogger(__name__)


class ConditionParser:
    """条件解析器 - 解析和评估触发条件"""

    # 支持的操作符
    OPERATORS = {
        # 比较操作符
        "gt": lambda a, b: a > b,
        "lt": lambda a, b: a < b,
        "gte": lambda a, b: a >= b,
        "lte": lambda a, b: a <= b,
        "eq": lambda a, b: a == b,
        # 阈值操作符（语义化别名）
        "below_threshold": lambda a, b: a < b,
        "above_threshold": lambda a, b: a > b,
    }

    # 交叉操作符（需要历史数据）
    CROSS_OPERATORS = ["cross_above", "cross_below"]

    def __init__(self, indicators: Dict[str, Any], df_history=None):
        """
        初始化条件解析器

        Args:
            indicators: calc_all_indicators 返回的指标数据
            df_history: K线历史数据 DataFrame（交叉操作需要）
        """
        self.indicators = indicators
        self.df_history = df_history

    def get_indicator_value(self, indicator_type: str, field: str) -> Optional[float]:
        """
        获取指定指标的值

        Args:
            indicator_type: 指标类型 (MA/MACD/RSI/KDJ/Bollinger)
            field: 字段名 (MA5, RSI, DIF 等)

        Returns:
            指标值，不存在则返回 None
        """
        indicator_values = self.indicators.get("indicators", {}).get(indicator_type, {})
        return indicator_values.get(field)

    def evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """
        评估单个条件

        Args:
            condition: 条件配置字典

        Returns:
            条件是否满足
        """
        operator = condition.get("operator")
        target_type = condition.get("target_type")

        # 获取左值
        left_value = self.get_indicator_value(
            condition.get("indicator"),
            condition.get("field")
        )
        if left_value is None:
            logger.warning(f"无法获取指标值: {condition.get('indicator')}.{condition.get('field')}")
            return False

        # 获取右值
        if target_type == "indicator":
            right_value = self.get_indicator_value(
                condition.get("target_indicator"),
                condition.get("target_field")
            )
        elif target_type == "value":
            right_value = condition.get("target_value")
        else:
            logger.warning(f"未知的 target_type: {target_type}")
            return False

        if right_value is None:
            logger.warning(f"无法获取目标值: {condition}")
            return False

        # 交叉操作需要历史数据
        if operator in self.CROSS_OPERATORS:
            return self._evaluate_cross(condition, left_value, right_value)

        # 普通比较操作
        if operator in self.OPERATORS:
            return self.OPERATORS[operator](left_value, right_value)

        logger.warning(f"未知的操作符: {operator}")
        return False

    def _evaluate_cross(self, condition: Dict[str, Any], curr_left: float, curr_right: float) -> bool:
        """
        评估交叉条件（需要历史数据）

        Args:
            condition: 条件配置
            curr_left: 当日左值
            curr_right: 当日右值

        Returns:
            是否发生交叉
        """
        if self.df_history is None or len(self.df_history) < 2:
            return False

        operator = condition.get("operator")

        # 计算前一天的指标值
        # 这里简化处理：重新计算前一天的所有指标
        # 实际优化可以缓存历史指标
        df_prev = self.df_history.iloc[:-1]  # 排除最后一行（当日）
        if len(df_prev) < 20:  # 需要足够数据计算指标
            return False

        prev_indicators = calc_all_indicators(df_prev)
        prev_parser = ConditionParser(prev_indicators)

        prev_left = prev_parser.get_indicator_value(
            condition.get("indicator"),
            condition.get("field")
        )
        prev_right = prev_parser.get_indicator_value(
            condition.get("target_indicator"),
            condition.get("target_field")
        ) if condition.get("target_type") == "indicator" else condition.get("target_value")

        if prev_left is None or prev_right is None:
            return False

        if operator == "cross_above":
            # 上穿：前一日左值 <= 右值，当日左值 > 右值
            return prev_left <= prev_right and curr_left > curr_right
        elif operator == "cross_below":
            # 下穿：前一日左值 >= 右值，当日左值 < 右值
            return prev_left >= prev_right and curr_left < curr_right

        return False

    def evaluate_all(self, conditions: List[Dict[str, Any]]) -> bool:
        """
        评估所有条件（AND 组合）

        Args:
            conditions: 条件列表

        Returns:
            所有条件是否都满足
        """
        if not conditions:
            return True

        return all(self.evaluate_condition(cond) for cond in conditions)


class PriceCalculator:
    """价位计算器 - 计算入场价、止损价、止盈价"""

    def __init__(self, indicators: Dict[str, Any], current_price: float):
        """
        初始化价位计算器

        Args:
            indicators: calc_all_indicators 返回的指标数据
            current_price: 当前价格
        """
        self.indicators = indicators
        self.current_price = current_price

    def get_indicator_value(self, indicator_type: str, field: str) -> Optional[float]:
        """获取指定指标的值"""
        indicator_values = self.indicators.get("indicators", {}).get(indicator_type, {})
        return indicator_values.get(field)

    def calculate_entry_price(self, config: Dict[str, Any]) -> Optional[float]:
        """
        计算入场价

        Args:
            config: 入场价配置

        Returns:
            入场价
        """
        price_type = config.get("type")

        if price_type == "indicator":
            return self.get_indicator_value(
                config.get("indicator"),
                config.get("field")
            )
        elif price_type == "percentage":
            # 基于当前价的百分比
            percentage = config.get("value", 0)
            return round(self.current_price * (1 + percentage), 2)
        elif price_type == "current":
            return self.current_price

        return None

    def calculate_exit_price(self, config: Dict[str, Any], entry_price: float) -> Optional[float]:
        """
        计算止损/止盈价

        Args:
            config: 价位配置
            entry_price: 入场价（百分比计算需要）

        Returns:
            价位
        """
        if not config:
            return None

        price_type = config.get("type")

        if price_type == "indicator":
            return self.get_indicator_value(
                config.get("indicator"),
                config.get("field")
            )
        elif price_type == "percentage":
            base = config.get("base", "entry")
            base_price = entry_price if base == "entry" else self.current_price
            percentage = config.get("value", 0)
            return round(base_price * (1 + percentage), 2)

        return None


class RuleEngine:
    """规则引擎 - 评估规则并生成信号"""

    def __init__(self, rules: List[Any]):
        """
        初始化规则引擎

        Args:
            rules: TradingRule 模型列表
        """
        self.rules = sorted(
            [r for r in rules if r.enabled],
            key=lambda x: x.priority,
            reverse=True
        )

    def evaluate(self, rule: Any, df, current_price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        评估单条规则

        Args:
            rule: TradingRule 模型实例
            df: K线数据 DataFrame
            current_price: 当前价格（可选，默认使用最新收盘价）

        Returns:
            信号字典，条件不满足返回 None
        """
        # 计算指标
        indicators = calc_all_indicators(df)

        if current_price is None:
            current_price = indicators.get("current_price", 0)

        if not current_price:
            return None

        # 解析条件配置
        try:
            conditions = json.loads(rule.conditions) if isinstance(rule.conditions, str) else rule.conditions
            if isinstance(conditions, dict) and "conditions" in conditions:
                conditions = conditions["conditions"]
        except (json.JSONDecodeError, TypeError):
            logger.error(f"规则 {rule.id} 条件配置解析失败")
            return None

        # 解析价位配置
        try:
            price_config = json.loads(rule.price_config) if isinstance(rule.price_config, str) else rule.price_config
        except (json.JSONDecodeError, TypeError):
            logger.error(f"规则 {rule.id} 价位配置解析失败")
            return None

        # 评估条件
        parser = ConditionParser(indicators, df)
        if not parser.evaluate_all(conditions):
            return None

        # 计算价位
        calculator = PriceCalculator(indicators, current_price)
        entry_price = calculator.calculate_entry_price(price_config.get("entry", {}))
        stop_loss = calculator.calculate_exit_price(price_config.get("stop_loss"), entry_price) if entry_price else None
        take_profit = calculator.calculate_exit_price(price_config.get("take_profit"), entry_price) if entry_price else None

        # 构建信号
        triggers = [rule.name]

        # 生成描述
        description = rule.description_template or f"{rule.name}触发"
        if entry_price:
            try:
                description = description.format(entry_price=entry_price)
            except KeyError:
                pass

        return {
            "signal_type": rule.rule_type,  # buy 或 sell
            "current_price": current_price,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "strength": rule.strength,
            "triggers": triggers,
            "indicators": indicators.get("indicators", {}),
            "message": description,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "priority": rule.priority
        }

    def evaluate_all(self, df, current_price: Optional[float] = None) -> Dict[str, Any]:
        """
        评估所有规则，返回最佳信号

        Args:
            df: K线数据 DataFrame
            current_price: 当前价格

        Returns:
            最佳信号（按优先级和强度选择）
        """
        buy_signals = []
        sell_signals = []

        for rule in self.rules:
            signal = self.evaluate(rule, df, current_price)
            if signal:
                if signal["signal_type"] == "buy":
                    buy_signals.append(signal)
                elif signal["signal_type"] == "sell":
                    sell_signals.append(signal)

        # 选择信号：优先返回买入信号（如果有）
        if buy_signals:
            # 按优先级和强度排序，选择最佳
            best = max(buy_signals, key=lambda x: (x["priority"], x["strength"]))
            return best

        if sell_signals:
            best = max(sell_signals, key=lambda x: (x["priority"], x["strength"]))
            return best

        # 无信号，返回 hold
        indicators = calc_all_indicators(df)
        return {
            "signal_type": "hold",
            "current_price": current_price or indicators.get("current_price"),
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "strength": 0,
            "triggers": [],
            "indicators": indicators.get("indicators", {}),
            "message": "当前无明显买卖信号，建议持有观望"
        }


def get_default_rules() -> List[Dict[str, Any]]:
    """
    获取默认规则配置（8条：4买4卖）

    Returns:
        默认规则配置列表
    """
    return [
        # ============ 买入规则 ============
        {
            "name": "MA金叉买入",
            "rule_type": "buy",
            "enabled": True,
            "priority": 3,
            "strength": 3,
            "conditions": json.dumps([{
                    "indicator": "MA",
                    "field": "MA5",
                    "operator": "cross_above",
                    "target_type": "indicator",
                    "target_indicator": "MA",
                    "target_field": "MA20"
                }]),
            "price_config": json.dumps({
                "entry": {"type": "indicator", "indicator": "MA", "field": "MA20"},
                "stop_loss": {"type": "percentage", "base": "entry", "value": -0.05},
                "take_profit": {"type": "percentage", "base": "entry", "value": 0.08}
            }),
            "description_template": "MA5上穿MA20，建议在MA20附近{entry_price:.2f}买入"
        },
        {
            "name": "RSI超卖买入",
            "rule_type": "buy",
            "enabled": True,
            "priority": 2,
            "strength": 2,
            "conditions": json.dumps([{
                    "indicator": "RSI",
                    "field": "RSI",
                    "operator": "lt",
                    "target_type": "value",
                    "target_value": 30
                }]),
            "price_config": json.dumps({
                "entry": {"type": "percentage", "value": -0.02},
                "stop_loss": {"type": "percentage", "base": "entry", "value": -0.05},
                "take_profit": {"type": "percentage", "base": "entry", "value": 0.05}
            }),
            "description_template": "RSI低于30，超卖区间，建议逢低买入"
        },
        {
            "name": "布林下轨买入",
            "rule_type": "buy",
            "enabled": True,
            "priority": 3,
            "strength": 3,
            "conditions": json.dumps([{
                    "indicator": "Bollinger",
                    "field": "lower",
                    "operator": "gt",
                    "target_type": "value",
                    "target_value": 0  # 占位，实际在 ConditionParser 中处理价格与下轨比较
                }]),
            "price_config": json.dumps({
                "entry": {"type": "indicator", "indicator": "Bollinger", "field": "lower"},
                "stop_loss": {"type": "percentage", "base": "entry", "value": -0.05},
                "take_profit": {"type": "indicator", "indicator": "Bollinger", "field": "middle"}
            }),
            "description_template": "价格跌破布林下轨，可能反弹"
        },
        {
            "name": "MACD金叉买入",
            "rule_type": "buy",
            "enabled": True,
            "priority": 2,
            "strength": 2,
            "conditions": json.dumps([{
                    "indicator": "MACD",
                    "field": "DIF",
                    "operator": "cross_above",
                    "target_type": "indicator",
                    "target_indicator": "MACD",
                    "target_field": "DEA"
                }]),
            "price_config": json.dumps({
                "entry": {"type": "current"},
                "stop_loss": {"type": "percentage", "base": "entry", "value": -0.05},
                "take_profit": {"type": "percentage", "base": "entry", "value": 0.08}
            }),
            "description_template": "MACD金叉形成，趋势可能转强"
        },
        # ============ 卖出规则 ============
        {
            "name": "MA死叉卖出",
            "rule_type": "sell",
            "enabled": True,
            "priority": 3,
            "strength": 3,
            "conditions": json.dumps([{
                    "indicator": "MA",
                    "field": "MA5",
                    "operator": "cross_below",
                    "target_type": "indicator",
                    "target_indicator": "MA",
                    "target_field": "MA20"
                }]),
            "price_config": json.dumps({
                "entry": {"type": "indicator", "indicator": "MA", "field": "MA20"},
                "stop_loss": None,
                "take_profit": {"type": "percentage", "base": "entry", "value": -0.05}
            }),
            "description_template": "MA5下穿MA20，建议在MA20附近{entry_price:.2f}减仓"
        },
        {
            "name": "RSI超买卖出",
            "rule_type": "sell",
            "enabled": True,
            "priority": 2,
            "strength": 2,
            "conditions": json.dumps([{
                    "indicator": "RSI",
                    "field": "RSI",
                    "operator": "gt",
                    "target_type": "value",
                    "target_value": 70
                }]),
            "price_config": json.dumps({
                "entry": {"type": "percentage", "value": 0.02},
                "stop_loss": None,
                "take_profit": {"type": "percentage", "base": "entry", "value": -0.02}
            }),
            "description_template": "RSI高于70，超买区间，建议逢高减仓"
        },
        {
            "name": "布林上轨卖出",
            "rule_type": "sell",
            "enabled": True,
            "priority": 3,
            "strength": 3,
            "conditions": json.dumps([{
                    "indicator": "Bollinger",
                    "field": "upper",
                    "operator": "lt",
                    "target_type": "value",
                    "target_value": 0  # 占位
                }]),
            "price_config": json.dumps({
                "entry": {"type": "indicator", "indicator": "Bollinger", "field": "upper"},
                "stop_loss": None,
                "take_profit": {"type": "indicator", "indicator": "Bollinger", "field": "middle"}
            }),
            "description_template": "价格突破布林上轨，可能回调"
        },
        {
            "name": "MACD死叉卖出",
            "rule_type": "sell",
            "enabled": True,
            "priority": 2,
            "strength": 2,
            "conditions": json.dumps([{
                    "indicator": "MACD",
                    "field": "DIF",
                    "operator": "cross_below",
                    "target_type": "indicator",
                    "target_indicator": "MACD",
                    "target_field": "DEA"
                }]),
            "price_config": json.dumps({
                "entry": {"type": "current"},
                "stop_loss": None,
                "take_profit": {"type": "percentage", "base": "entry", "value": -0.05}
            }),
            "description_template": "MACD死叉形成，趋势可能转弱"
        }
    ]
