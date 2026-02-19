"""
数据源协调器

管理多个数据源，实现自动 fallback 机制。
确保股票数据获取的稳定性和高可用性。
"""

import logging
import threading
import time
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date
from dataclasses import dataclass

from .base import DataProvider, StockData, ProviderStatus
from .sina import SinaProvider
from .eastmoney import EastMoneyProvider
from .tencent import TencentProvider
from .netease import NeteaseProvider
from .akshare import AKShareProvider
from .openbb import OpenBBProvider

logger = logging.getLogger(__name__)

# 全局协调器实例（单例）
_coordinator_instance = None
_coordinator_lock = threading.Lock()


@dataclass
class FetchResult:
    """数据获取结果"""
    success: bool
    data: Optional[StockData] = None
    provider_name: str = ""
    error_message: str = ""
    tried_providers: List[str] = None  # 尝试过的数据源列表

    def __post_init__(self):
        if self.tried_providers is None:
            self.tried_providers = []


class DataSourceCoordinator:
    """
    数据源协调器

    功能:
    1. 管理多个数据源，按优先级排序
    2. 自动 fallback 到下一个可用数据源
    3. 数据源健康状态监控
    4. 封禁检测和冷却机制
    5. 请求限流保护
    """

    # 冷却时间（分钟）
    COOLDOWN_MINUTES = 5
    # 请求最小间隔（秒）- 防止请求过于频繁
    MIN_REQUEST_INTERVAL = 0.2  # 200ms
    # 连续失败阈值
    MAX_CONSECUTIVE_FAILURES = 3

    def __init__(self):
        # 初始化所有数据源
        self.providers: List[DataProvider] = [
            SinaProvider(),
            EastMoneyProvider(),
            TencentProvider(),
            NeteaseProvider(),
            AKShareProvider(),
            OpenBBProvider(),
        ]
        # 按优先级排序
        self.providers.sort()

        # 请求限流
        self._last_request_time = 0.0
        self._request_lock = threading.Lock()

        logger.info(f"[数据协调器] 初始化完成 | 数据源: {[p.NAME for p in self.providers]}")

    def _wait_for_rate_limit(self):
        """请求限流，确保请求间隔不低于最小值"""
        with self._request_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self.MIN_REQUEST_INTERVAL:
                wait_time = self.MIN_REQUEST_INTERVAL - elapsed
                time.sleep(wait_time)
            self._last_request_time = time.time()

    def get_available_providers(self) -> List[DataProvider]:
        """获取所有可用的数据源（按优先级排序）"""
        return [p for p in self.providers if p.is_available()]

    def get_realtime_price(self, symbol: str, normalized_code: str, market: str) -> FetchResult:
        """
        获取实时价格（带自动 fallback）

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型 "cn" 或 "us"

        Returns:
            FetchResult: 获取结果
        """
        self._wait_for_rate_limit()

        tried_providers = []
        last_error = ""

        for provider in self.providers:
            if not provider.is_available():
                logger.debug(f"[数据协调器] 跳过不可用数据源: {provider.NAME}")
                continue

            tried_providers.append(provider.NAME)
            logger.info(f"[数据协调器] 尝试数据源: {provider.NAME} | 股票: {symbol}")

            try:
                data = provider.get_realtime_price(symbol, normalized_code, market)
                if data and data.is_valid():
                    logger.info(f"[数据协调器] 获取成功 | 数据源: {provider.NAME} | 股票: {symbol} | 价格: {data.current_price}")
                    return FetchResult(
                        success=True,
                        data=data,
                        provider_name=provider.NAME,
                        tried_providers=tried_providers
                    )
                else:
                    last_error = f"数据无效或为空"
                    logger.warning(f"[数据协调器] 数据源 {provider.NAME} 返回无效数据 | 股票: {symbol}")

            except Exception as e:
                last_error = str(e)
                logger.error(f"[数据协调器] 数据源 {provider.NAME} 请求异常 | 股票: {symbol} | 错误: {e}")

        # 所有数据源都失败
        logger.error(f"[数据协调器] 所有数据源均失败 | 股票: {symbol} | 尝试过: {tried_providers}")
        return FetchResult(
            success=False,
            error_message=f"数据获取失败，请稍后重试。尝试过: {', '.join(tried_providers)}",
            tried_providers=tried_providers
        )

    def get_kline_data(self, symbol: str, normalized_code: str, market: str,
                       datalen: int = 30) -> Tuple[Optional[List[Dict]], str, List[str]]:
        """
        获取 K 线数据（带自动 fallback）

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型
            datalen: 需要的 K 线数量

        Returns:
            Tuple[Optional[List[Dict]], str, List[str]]: (K线数据, 数据源名称, 尝试过的数据源列表)
        """
        self._wait_for_rate_limit()

        tried_providers = []

        for provider in self.providers:
            if not provider.is_available():
                continue

            tried_providers.append(provider.NAME)
            logger.info(f"[数据协调器] 尝试获取K线 | 数据源: {provider.NAME} | 股票: {symbol}")

            try:
                kline_data = provider.get_kline_data(symbol, normalized_code, market, datalen)
                if kline_data and len(kline_data) > 0:
                    logger.info(f"[数据协调器] K线获取成功 | 数据源: {provider.NAME} | 股票: {symbol} | 数量: {len(kline_data)}")
                    return kline_data, provider.NAME, tried_providers

            except Exception as e:
                logger.error(f"[数据协调器] K线获取异常 | 数据源: {provider.NAME} | 股票: {symbol} | 错误: {e}")

        logger.error(f"[数据协调器] K线获取失败 | 股票: {symbol} | 尝试过: {tried_providers}")
        return None, "", tried_providers

    def get_stock_name(self, symbol: str, normalized_code: str, market: str) -> Tuple[Optional[str], str]:
        """
        获取股票名称（带自动 fallback）

        Returns:
            Tuple[Optional[str], str]: (股票名称, 数据源名称)
        """
        result = self.get_realtime_price(symbol, normalized_code, market)
        if result.success and result.data:
            return result.data.name, result.provider_name
        return None, ""

    def _get_capable_providers(self, capability: str) -> List[DataProvider]:
        """
        获取支持指定能力的所有可用数据源

        Args:
            capability: 能力名称 (如 "financial_report", "valuation_metrics")

        Returns:
            List[DataProvider]: 支持该能力且可用的数据源列表
        """
        return [
            p for p in self.providers
            if p.is_available() and capability in getattr(p, 'CAPABILITIES', set())
        ]

    def get_financial_report(self, symbol: str, normalized_code: str, market: str,
                            report_type: str = "balance_sheet",
                            period: str = "quarterly") -> Tuple[Optional[Dict], str]:
        """
        获取财报数据

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型
            report_type: 报告类型 (balance_sheet, income, cash_flow)
            period: 周期 (annual, quarterly)

        Returns:
            Tuple[Optional[Dict], str]: (财报数据, 数据源名称)
        """
        self._wait_for_rate_limit()

        tried_providers = []

        for provider in self._get_capable_providers("financial_report"):
            tried_providers.append(provider.NAME)
            logger.info(f"[数据协调器] 尝试获取财报 | 数据源: {provider.NAME} | 股票: {symbol}")

            try:
                data = provider.get_financial_report(symbol, normalized_code, market, report_type, period)
                if data:
                    logger.info(f"[数据协调器] 财报获取成功 | 数据源: {provider.NAME} | 股票: {symbol}")
                    return data, provider.NAME
            except NotImplementedError:
                logger.debug(f"[数据协调器] {provider.NAME} 不支持财报数据")
            except Exception as e:
                logger.error(f"[数据协调器] 财报获取异常 | 数据源: {provider.NAME} | 股票: {symbol} | 错误: {e}")

        logger.error(f"[数据协调器] 财报获取失败 | 股票: {symbol} | 尝试过: {tried_providers}")
        return None, ""

    def get_valuation_metrics(self, symbol: str, normalized_code: str,
                             market: str) -> Tuple[Optional[Dict], str]:
        """
        获取估值指标

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型

        Returns:
            Tuple[Optional[Dict], str]: (估值指标, 数据源名称)
        """
        self._wait_for_rate_limit()

        tried_providers = []

        for provider in self._get_capable_providers("valuation_metrics"):
            tried_providers.append(provider.NAME)
            logger.info(f"[数据协调器] 尝试获取估值 | 数据源: {provider.NAME} | 股票: {symbol}")

            try:
                data = provider.get_valuation_metrics(symbol, normalized_code, market)
                if data:
                    logger.info(f"[数据协调器] 估值获取成功 | 数据源: {provider.NAME} | 股票: {symbol}")
                    return data, provider.NAME
            except NotImplementedError:
                logger.debug(f"[数据协调器] {provider.NAME} 不支持估值指标")
            except Exception as e:
                logger.error(f"[数据协调器] 估值获取异常 | 数据源: {provider.NAME} | 股票: {symbol} | 错误: {e}")

        logger.error(f"[数据协调器] 估值获取失败 | 股票: {symbol} | 尝试过: {tried_providers}")
        return None, ""

    def get_macro_indicators(self, market: str = "cn",
                            indicators: List[str] = None) -> Tuple[Optional[Dict], str]:
        """
        获取宏观经济指标

        Args:
            market: 市场类型 (cn, us)
            indicators: 指标列表

        Returns:
            Tuple[Optional[Dict], str]: (宏观指标, 数据源名称)
        """
        self._wait_for_rate_limit()

        tried_providers = []

        for provider in self._get_capable_providers("macro_indicators"):
            tried_providers.append(provider.NAME)
            logger.info(f"[数据协调器] 尝试获取宏观指标 | 数据源: {provider.NAME} | 市场: {market}")

            try:
                data = provider.get_macro_indicators(market, indicators)
                if data:
                    logger.info(f"[数据协调器] 宏观指标获取成功 | 数据源: {provider.NAME} | 市场: {market}")
                    return data, provider.NAME
            except NotImplementedError:
                logger.debug(f"[数据协调器] {provider.NAME} 不支持宏观指标")
            except Exception as e:
                logger.error(f"[数据协调器] 宏观指标获取异常 | 数据源: {provider.NAME} | 市场: {market} | 错误: {e}")

        logger.error(f"[数据协调器] 宏观指标获取失败 | 市场: {market} | 尝试过: {tried_providers}")
        return None, ""

    def get_capabilities(self) -> Dict[str, List[str]]:
        """
        获取所有数据源的能力映射

        Returns:
            Dict[str, List[str]]: 数据源名称 -> 支持的能力列表
        """
        return {
            provider.NAME: list(getattr(provider, 'CAPABILITIES', set()))
            for provider in self.providers
        }

    def get_health_status(self) -> Dict[str, Dict]:
        """获取所有数据源的健康状态"""
        status = {}
        for provider in self.providers:
            status[provider.NAME] = {
                "priority": provider.PRIORITY,
                "status": provider.health.status.value,
                "consecutive_failures": provider.health.consecutive_failures,
                "is_available": provider.is_available(),
                "cooldown_until": provider.health.cooldown_until.isoformat() if provider.health.cooldown_until else None,
            }
        return status

    def reset_provider(self, provider_name: str) -> bool:
        """
        重置指定数据源的状态

        Args:
            provider_name: 数据源名称

        Returns:
            bool: 是否成功重置
        """
        for provider in self.providers:
            if provider.NAME == provider_name:
                provider.health = type(provider.health)()  # 重置健康状态
                logger.info(f"[数据协调器] 重置数据源状态: {provider_name}")
                return True
        return False

    def reset_all_providers(self):
        """重置所有数据源的状态"""
        for provider in self.providers:
            provider.health = type(provider.health)()
        logger.info("[数据协调器] 重置所有数据源状态")


def get_coordinator() -> DataSourceCoordinator:
    """获取全局协调器实例（单例）"""
    global _coordinator_instance
    if _coordinator_instance is None:
        with _coordinator_lock:
            if _coordinator_instance is None:
                _coordinator_instance = DataSourceCoordinator()
    return _coordinator_instance
