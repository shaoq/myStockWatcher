"""
AKShare 数据源提供者

使用 AKShare 获取 A 股高级金融数据。
支持财报、估值指标等数据类型。

优先级 L4 - 用于 A 股高级数据。
"""

import logging
from typing import Optional, List, Dict, Set
from datetime import datetime
from threading import Lock

from .base import DataProvider, StockData
from .spot_cache import get_spot_data_with_cache

logger = logging.getLogger(__name__)

# AKShare 懒加载相关变量
_ak = None
_ak_lock = Lock()
_ak_available = None


def get_ak():
    """
    懒加载 AKShare 模块

    Returns:
        AKShare 模块或 None（如果未安装）
    """
    global _ak, _ak_available

    if _ak_available is not None:
        return _ak if _ak_available else None

    with _ak_lock:
        if _ak_available is not None:
            return _ak if _ak_available else None

        try:
            import akshare
            _ak = akshare
            _ak_available = True
            logger.info("[AKShare] 初始化成功")
            return _ak
        except ImportError as e:
            logger.warning(f"[AKShare] 未安装，A 股高级数据功能不可用: {e}")
            _ak_available = False
            return None
        except Exception as e:
            logger.error(f"[AKShare] 初始化失败: {e}")
            _ak_available = False
            return None


class AKShareProvider(DataProvider):
    """
    AKShare 数据源提供者

    专门用于获取 A 股的高级数据（财报、估值指标等）。
    使用东方财富、同花顺等数据源。

    优先级: 4 (在 OpenBB 之前，专门处理 A 股)
    """

    PRIORITY = 4
    NAME = "akshare"
    CAPABILITIES: Set[str] = {
        "realtime_price",
        "kline_data",
        "financial_report",
        "valuation_metrics",
    }

    def __init__(self):
        self._ak = None

    @property
    def ak(self):
        """懒加载 AKShare"""
        if self._ak is None:
            self._ak = get_ak()
        return self._ak

    def is_available(self) -> bool:
        """检查 AKShare 是否可用"""
        return self.ak is not None

    def get_realtime_price(self, symbol: str, normalized_code: str, market: str) -> Optional[StockData]:
        """
        获取实时价格 - AKShare 不作为主要价格数据源
        返回 None，让其他数据源处理
        """
        return None

    def get_kline_data(self, symbol: str, normalized_code: str, market: str,
                       datalen: int = 30) -> Optional[List[Dict]]:
        """
        获取 K 线数据 - AKShare 不作为主要 K 线数据源
        返回 None，让其他数据源处理
        """
        return None

    def get_financial_report(self, symbol: str, normalized_code: str, market: str,
                             report_type: str = "balance_sheet",
                             period: str = "quarterly") -> Optional[Dict]:
        """
        获取财报数据

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型
            report_type: 报告类型 (balance_sheet, income, cash_flow)
            period: 周期 (annual, quarterly)

        Returns:
            财报数据字典
        """
        if not self.is_available() or market != "cn":
            return None

        try:
            logger.info(f"[AKShare] 获取财报 | 股票: {symbol} | 类型: {report_type}")

            # 使用同花顺财务摘要接口
            indicator = "按报告期" if period == "quarterly" else "按年度"

            try:
                df = self.ak.stock_financial_abstract_ths(
                    symbol=normalized_code,
                    indicator=indicator
                )
            except Exception:
                # 尝试使用 6 位代码
                df = self.ak.stock_financial_abstract_ths(
                    symbol=symbol,
                    indicator=indicator
                )

            if df is None or df.empty:
                logger.warning(f"[AKShare] 财报数据为空 | 股票: {symbol}")
                return None

            # 按报告期降序排序，获取最新一期数据
            df = df.sort_values(by='报告期', ascending=False)
            latest = df.iloc[0] if len(df) > 0 else None
            if latest is None:
                return None

            # 构建财报数据
            result = {
                "report_date": str(latest.get("报告期", "")),
                "total_assets": self._parse_value(latest.get("总资产")),
                "total_liabilities": None,  # 需要计算
                "total_equity": self._parse_value(latest.get("股东权益")),
                "current_assets": None,
                "current_liabilities": None,
                "revenue": self._parse_value(latest.get("营业总收入")),
                "net_income": self._parse_value(latest.get("净利润")),
                "earnings_per_share": self._parse_value(latest.get("基本每股收益")),
                "operating_cash_flow": None,
                "investing_cash_flow": None,
                "financing_cash_flow": None,
                "gross_profit": self._parse_value(latest.get("毛利润")),
                "operating_income": self._parse_value(latest.get("营业利润")),
                "raw_data": latest.to_dict() if hasattr(latest, 'to_dict') else {},
            }

            logger.info(f"[AKShare] 财报获取成功 | 股票: {symbol} | 报告期: {result['report_date']}")
            return result

        except Exception as e:
            logger.error(f"[AKShare] 财报获取异常 | 股票: {symbol} | 错误: {e}")
            return None

    def get_valuation_metrics(self, symbol: str, normalized_code: str, market: str) -> Optional[Dict]:
        """
        获取估值指标

        使用共享缓存获取全量数据，避免重复下载

        Args:
            symbol: 原始股票代码
            normalized_code: 规范化后的代码
            market: 市场类型

        Returns:
            估值指标字典
        """
        if not self.is_available() or market != "cn":
            return None

        try:
            logger.info(f"[AKShare] 获取估值指标 | 股票: {symbol}")

            # 使用缓存获取全量数据
            df = get_spot_data_with_cache(
                fetch_func=lambda: self.ak.stock_zh_a_spot_em(),
                source="akshare"
            )

            if df is None:
                logger.warning(f"[AKShare] 全量数据获取失败 | 股票: {symbol}")
                return None

            # 查找对应股票
            row = df[df['代码'] == normalized_code]
            if row.empty:
                row = df[df['代码'] == symbol]

            if row.empty:
                logger.warning(f"[AKShare] 未找到股票估值数据 | 股票: {symbol}")
                return None

            latest = row.iloc[0]

            # 构建估值指标
            result = {
                "pe_ratio": self._parse_value(latest.get("市盈率-动态")),
                "pb_ratio": self._parse_value(latest.get("市净率")),
                "ps_ratio": None,  # AKShare 实时数据不包含
                "roe": None,
                "roa": None,
                "revenue_growth": None,
                "profit_margin": None,
                "gross_margin": None,
                "debt_to_equity": None,
                "current_ratio": None,
                "dividend_yield": None,
                "eps": None,
                "book_value_per_share": None,
                "market_cap": self._parse_value(latest.get("总市值")),
                "circulating_market_cap": self._parse_value(latest.get("流通市值")),
            }

            # 尝试获取财务摘要中的 ROE 等指标
            try:
                fin_df = self.ak.stock_financial_abstract_ths(symbol=normalized_code, indicator="按报告期")
                if fin_df is not None and not fin_df.empty:
                    # 按报告期降序排序，获取最新数据
                    fin_df = fin_df.sort_values(by='报告期', ascending=False)
                    fin_latest = fin_df.iloc[0]
                    result["roe"] = self._parse_percent(fin_latest.get("净资产收益率"))
                    result["gross_margin"] = self._parse_percent(fin_latest.get("销售毛利率"))
                    result["eps"] = self._parse_value(fin_latest.get("基本每股收益"))
                    result["book_value_per_share"] = self._parse_value(fin_latest.get("每股净资产"))
            except Exception:
                pass

            logger.info(f"[AKShare] 估值获取成功 | 股票: {symbol} | PE: {result['pe_ratio']} | PB: {result['pb_ratio']}")
            return result

        except Exception as e:
            logger.error(f"[AKShare] 估值指标获取异常 | 股票: {symbol} | 错误: {e}")
            return None

    def get_macro_indicators(self, market: str = "cn",
                            indicators: List[str] = None) -> Optional[Dict]:
        """
        获取宏观经济指标 - AKShare 不提供此功能
        返回 None，让 OpenBB 处理
        """
        return None

    def _parse_value(self, value) -> Optional[float]:
        """解析数值，处理各种格式"""
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            # 处理字符串格式
            s = str(value).strip()
            if not s or s == "-" or s == "--" or s.lower() == "nan":
                return None
            # 移除逗号
            s = s.replace(",", "")
            # 处理单位
            multiplier = 1
            if "亿" in s:
                multiplier = 1e8
                s = s.replace("亿", "")
            elif "万" in s:
                multiplier = 1e4
                s = s.replace("万", "")
            # 转换为浮点数
            return float(s) * multiplier
        except (ValueError, TypeError):
            return None

    def _parse_percent(self, value) -> Optional[float]:
        """解析百分比数值"""
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            s = str(value).strip()
            if not s or s == "-" or s == "--":
                return None
            s = s.replace("%", "").strip()
            return float(s)
        except (ValueError, TypeError):
            return None
