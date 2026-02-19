"""
数据源提供者模块

提供多数据源 fallback 机制，确保股票数据获取的稳定性。

数据源优先级:
1. 新浪财经 (L1) - 速度快，但易封禁
2. 东方财富 (L2) - 通过 AKShare，稳定
3. 腾讯财经 (L3) - 备用
4. AKShare (L4) - A 股高级数据（财报、估值）
5. 网易财经 (L5) - 兜底
6. OpenBB (L6) - 高级数据源（美股财报、估值、宏观等）
"""

from .base import DataProvider, StockData, ProviderHealth
from .coordinator import DataSourceCoordinator, get_coordinator
from .sina import SinaProvider
from .eastmoney import EastMoneyProvider
from .tencent import TencentProvider
from .netease import NeteaseProvider
from .akshare import AKShareProvider
from .openbb import OpenBBProvider

__all__ = [
    'DataProvider',
    'StockData',
    'ProviderHealth',
    'DataSourceCoordinator',
    'get_coordinator',
    'SinaProvider',
    'EastMoneyProvider',
    'TencentProvider',
    'NeteaseProvider',
    'AKShareProvider',
    'OpenBBProvider',
]
