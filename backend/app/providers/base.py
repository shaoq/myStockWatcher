"""
数据源提供者抽象基类

定义统一的数据获取接口，支持多数据源 fallback。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """数据源状态"""
    HEALTHY = "healthy"           # 健康，可正常使用
    DEGRADED = "degraded"         # 降级，偶尔失败
    COOLING = "cooling"           # 冷却中，被封禁后恢复期
    DISABLED = "disabled"         # 禁用，不可用


@dataclass
class ProviderHealth:
    """数据源健康状态"""
    status: ProviderStatus = ProviderStatus.HEALTHY
    consecutive_failures: int = 0      # 连续失败次数
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None  # 冷却结束时间
    total_requests: int = 0
    total_failures: int = 0

    def is_available(self) -> bool:
        """检查数据源是否可用"""
        if self.status == ProviderStatus.DISABLED:
            return False
        if self.status == ProviderStatus.COOLING:
            if self.cooldown_until and datetime.now() < self.cooldown_until:
                return False
            # 冷却期结束，恢复为健康状态
            self.status = ProviderStatus.HEALTHY
            self.cooldown_until = None
            self.consecutive_failures = 0
        return True

    def record_success(self):
        """记录成功请求"""
        self.last_success_time = datetime.now()
        self.consecutive_failures = 0
        self.total_requests += 1
        if self.status == ProviderStatus.DEGRADED:
            self.status = ProviderStatus.HEALTHY

    def record_failure(self, cooldown_minutes: int = 5):
        """记录失败请求"""
        self.last_failure_time = datetime.now()
        self.consecutive_failures += 1
        self.total_requests += 1
        self.total_failures += 1

        # 连续失败 3 次进入冷却期
        if self.consecutive_failures >= 3:
            self.status = ProviderStatus.COOLING
            self.cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
            logger.warning(f"[数据源] 连续失败 {self.consecutive_failures} 次，进入 {cooldown_minutes} 分钟冷却期")
        elif self.consecutive_failures >= 1:
            self.status = ProviderStatus.DEGRADED


@dataclass
class StockData:
    """股票数据结构"""
    symbol: str                           # 股票代码（用户输入格式）
    name: Optional[str] = None            # 股票名称
    current_price: Optional[float] = None # 当前价格
    open_price: Optional[float] = None    # 开盘价
    close_price: Optional[float] = None   # 昨收价
    high_price: Optional[float] = None    # 最高价
    low_price: Optional[float] = None     # 最低价
    volume: Optional[int] = None          # 成交量
    turnover: Optional[float] = None      # 成交额
    kline_data: Optional[List[Dict]] = None  # K线数据列表
    provider_name: str = ""               # 数据来源提供者
    fetched_at: datetime = field(default_factory=datetime.now)  # 数据获取时间

    def is_valid(self) -> bool:
        """检查数据是否有效"""
        return self.current_price is not None and self.current_price > 0


class DataProvider(ABC):
    """
    数据源提供者抽象基类

    所有数据源实现都需要继承此类并实现相应方法。
    """

    # 数据源优先级，数字越小优先级越高
    PRIORITY: int = 99
    # 数据源名称
    NAME: str = "base"
    # 数据源支持的能力集合
    CAPABILITIES: Set[str] = set()

    def __init__(self):
        self.health = ProviderHealth()

    @abstractmethod
    def get_realtime_price(self, symbol: str, normalized_code: str, market: str) -> Optional[StockData]:
        """
        获取实时价格

        Args:
            symbol: 原始股票代码（用户输入）
            normalized_code: 规范化后的代码（用于 API）
            market: 市场类型 "cn" 或 "us"

        Returns:
            StockData 或 None
        """
        pass

    @abstractmethod
    def get_kline_data(self, symbol: str, normalized_code: str, market: str,
                       datalen: int = 30) -> Optional[List[Dict]]:
        """
        获取 K 线数据

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型
            datalen: 需要的 K 线数量

        Returns:
            K 线数据列表，格式: [{"day": "2026-01-01", "open": 10.0, "close": 10.5, ...}, ...]
        """
        pass

    def get_stock_name(self, symbol: str, normalized_code: str, market: str) -> Optional[str]:
        """
        获取股票名称（可选实现，默认通过获取实时价格来获取）

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型

        Returns:
            股票名称或 None
        """
        data = self.get_realtime_price(symbol, normalized_code, market)
        return data.name if data else None

    def get_financial_report(self, symbol: str, normalized_code: str, market: str,
                            report_type: str = "balance_sheet",
                            period: str = "quarterly") -> Optional[Dict]:
        """
        获取财报数据（可选实现，默认抛出 NotImplementedError）

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型
            report_type: 报告类型 (balance_sheet, income, cash_flow)
            period: 周期 (annual, quarterly)

        Returns:
            财报数据字典或 None
        """
        raise NotImplementedError(f"[{self.NAME}] 不支持财报数据获取")

    def get_valuation_metrics(self, symbol: str, normalized_code: str,
                             market: str) -> Optional[Dict]:
        """
        获取估值指标（可选实现，默认抛出 NotImplementedError）

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型

        Returns:
            估值指标字典或 None
        """
        raise NotImplementedError(f"[{self.NAME}] 不支持估值指标获取")

    def get_macro_indicators(self, market: str = "cn",
                            indicators: List[str] = None) -> Optional[Dict]:
        """
        获取宏观经济指标（可选实现，默认抛出 NotImplementedError）

        Args:
            market: 市场类型 (cn, us)
            indicators: 指标列表 (gdp, cpi, interest_rate 等)

        Returns:
            宏观指标字典或 None
        """
        raise NotImplementedError(f"[{self.NAME}] 不支持宏观指标获取")

    def is_available(self) -> bool:
        """检查数据源是否可用"""
        return self.health.is_available()

    def record_success(self):
        """记录成功"""
        self.health.record_success()
        logger.debug(f"[{self.NAME}] 请求成功")

    def record_failure(self):
        """记录失败"""
        self.health.record_failure()
        logger.warning(f"[{self.NAME}] 请求失败，连续失败次数: {self.health.consecutive_failures}")

    def mark_banned(self, cooldown_minutes: int = 5):
        """
        标记为被封禁状态

        Args:
            cooldown_minutes: 冷却时间（分钟）
        """
        self.health.status = ProviderStatus.COOLING
        self.health.cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        self.health.consecutive_failures = 3
        logger.warning(f"[{self.NAME}] 检测到封禁，进入 {cooldown_minutes} 分钟冷却期")

    def __lt__(self, other):
        """用于排序，优先级高的排前面"""
        return self.PRIORITY < other.PRIORITY
