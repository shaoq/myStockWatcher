"""
OpenBB 数据源提供者

使用 OpenBB Platform 获取高级金融数据。
支持财报、估值指标、宏观经济等多种数据类型。

优先级 L5 - 仅在需要高级数据时使用。
"""

import logging
from typing import Optional, List, Dict, Set
from datetime import datetime
from threading import Lock

from ..base import DataProvider, StockData

logger = logging.getLogger(__name__)

# OpenBB 懒加载相关变量
_obb = None
_obb_lock = Lock()
_obb_available = None


def get_obb():
    """
    懒加载 OpenBB 实例

    Returns:
        OpenBB 实例或 None（如果未安装）
    """
    global _obb, _obb_available

    if _obb_available is not None:
        return _obb if _obb_available else None

    with _obb_lock:
        if _obb_available is not None:
            return _obb if _obb_available else None

        try:
            from openbb import obb
            _obb = obb

            # 配置 FMP API 密钥（用于估值和财报数据）
            fmp_api_key = "Ksb3Rh0djHF19N4ZlvUkMzg4qJVMVEPm"
            if fmp_api_key:
                _obb.user.credentials.fmp_api_key = fmp_api_key
                logger.info("[OpenBB] FMP API 密钥已配置")

            _obb_available = True
            logger.info("[OpenBB] 初始化成功")
            return _obb
        except ImportError as e:
            logger.warning(f"[OpenBB] 未安装，高级数据功能不可用: {e}")
            _obb_available = False
            return None
        except Exception as e:
            logger.error(f"[OpenBB] 初始化失败: {e}")
            _obb_available = False
            return None


def _convert_symbol_for_openbb(symbol: str, normalized_code: str, market: str) -> str:
    """
    将内部股票代码格式转换为 OpenBB 格式

    内部格式:
    - A股: sh600000, sz000001, bj832000
    - 美股: AAPL (直接使用)

    OpenBB 格式 (Yahoo Finance 格式):
    - A股上海: 600000.SHA
    - A股深圳: 000001.SZE
    - 北交所: 可能不支持
    - 美股: AAPL (直接使用)

    Args:
        symbol: 原始股票代码
        normalized_code: 规范化后的代码
        market: 市场类型

    Returns:
        OpenBB 格式的股票代码
    """
    if market == "us":
        # 美股直接使用原始代码
        return symbol.upper()

    # A股转换
    if normalized_code.startswith("sh"):
        # 上海交易所: sh600000 -> 600000.SHA
        return f"{normalized_code[2:]}.SHA"
    elif normalized_code.startswith("sz"):
        # 深圳交易所: sz000001 -> 000001.SZE
        return f"{normalized_code[2:]}.SZE"
    elif normalized_code.startswith("bj"):
        # 北交所: 暂时尝试使用 BJ 后缀
        # 注意: OpenBB 可能不支持北交所
        return f"{normalized_code[2:]}.BJ"
    else:
        # 未知格式，返回原始代码
        return symbol


class OpenBBProvider(DataProvider):
    """
    OpenBB 数据源提供者 (L5 - 高级数据专用)

    提供以下能力:
    - realtime_price: 实时价格（有延迟）
    - kline_data: K线数据
    - financial_report: 财报数据（核心能力）
    - valuation_metrics: 估值指标（核心能力）
    - macro_indicators: 宏观经济指标（核心能力）
    """

    PRIORITY = 5
    NAME = "openbb"
    CAPABILITIES: Set[str] = {
        "realtime_price",
        "kline_data",
        "financial_report",
        "valuation_metrics",
        "macro_indicators",
    }

    def __init__(self):
        super().__init__()
        self._obb = None

    @property
    def obb(self):
        """获取 OpenBB 实例（懒加载）"""
        if self._obb is None:
            self._obb = get_obb()
        return self._obb

    def is_available(self) -> bool:
        """检查 OpenBB 是否可用"""
        return self.obb is not None and super().is_available()

    def get_realtime_price(self, symbol: str, normalized_code: str,
                           market: str) -> Optional[StockData]:
        """
        获取实时价格（有延迟，优先级低）

        注意: OpenBB 的实时价格可能有延迟，
        建议使用其他数据源获取实时价格。
        """
        if not self.is_available():
            return None

        obb_symbol = _convert_symbol_for_openbb(symbol, normalized_code, market)

        try:
            logger.info(f"[OpenBB] 获取价格 | 股票: {symbol} | OpenBB格式: {obb_symbol}")

            # 使用 OpenBB 获取价格数据
            result = self.obb.equity.price.quote(obb_symbol)

            if result is None:
                logger.warning(f"[OpenBB] 价格数据为空 | 股票: {symbol}")
                self.record_failure()
                return None

            # 解析结果
            df = result.to_dataframe() if hasattr(result, 'to_dataframe') else None

            if df is None or df.empty:
                logger.warning(f"[OpenBB] 价格数据解析失败 | 股票: {symbol}")
                self.record_failure()
                return None

            # 提取第一行数据
            row = df.iloc[0] if len(df) > 0 else None
            if row is None:
                self.record_failure()
                return None

            current_price = float(row.get('last_price', row.get('close', 0)))
            if current_price <= 0:
                logger.warning(f"[OpenBB] 价格无效 | 股票: {symbol} | 价格: {current_price}")
                self.record_failure()
                return None

            self.record_success()
            return StockData(
                symbol=symbol,
                name=str(row.get('name', row.get('symbol', ''))),
                current_price=current_price,
                open_price=float(row.get('open', 0)) if row.get('open') else None,
                close_price=float(row.get('previous_close', 0)) if row.get('previous_close') else None,
                high_price=float(row.get('high', 0)) if row.get('high') else None,
                low_price=float(row.get('low', 0)) if row.get('low') else None,
                volume=int(row.get('volume', 0)) if row.get('volume') else None,
                provider_name=self.NAME
            )

        except Exception as e:
            logger.error(f"[OpenBB] 价格获取异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
            return None

    def get_kline_data(self, symbol: str, normalized_code: str, market: str,
                       datalen: int = 30) -> Optional[List[Dict]]:
        """获取 K 线数据"""
        if not self.is_available():
            return None

        obb_symbol = _convert_symbol_for_openbb(symbol, normalized_code, market)

        try:
            logger.info(f"[OpenBB] 获取K线 | 股票: {symbol} | 数量: {datalen}")

            result = self.obb.equity.price.historical(
                obb_symbol,
                start_date=None,  # 使用默认
                end_date=None
            )

            if result is None:
                logger.warning(f"[OpenBB] K线数据为空 | 股票: {symbol}")
                self.record_failure()
                return None

            df = result.to_dataframe() if hasattr(result, 'to_dataframe') else None

            if df is None or df.empty:
                logger.warning(f"[OpenBB] K线数据解析失败 | 股票: {symbol}")
                self.record_failure()
                return None

            # 取最后 datalen 条数据
            df = df.tail(datalen)

            # 转换为统一格式
            kline_list = []
            for idx, row in df.iterrows():
                try:
                    date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                    kline_list.append({
                        "day": date_str,
                        "open": float(row.get('open', 0)),
                        "close": float(row.get('close', 0)),
                        "high": float(row.get('high', 0)),
                        "low": float(row.get('low', 0)),
                        "volume": int(float(row.get('volume', 0))),
                    })
                except (ValueError, TypeError) as e:
                    logger.debug(f"[OpenBB] 跳过无效K线数据: {e}")
                    continue

            if not kline_list:
                logger.warning(f"[OpenBB] K线数据转换后为空 | 股票: {symbol}")
                self.record_failure()
                return None

            self.record_success()
            logger.info(f"[OpenBB] K线数据获取成功 | 股票: {symbol} | 数量: {len(kline_list)}")
            return kline_list

        except Exception as e:
            logger.error(f"[OpenBB] K线获取异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
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
        if not self.is_available():
            return None

        obb_symbol = _convert_symbol_for_openbb(symbol, normalized_code, market)

        try:
            logger.info(f"[OpenBB] 获取财报 | 股票: {symbol} | 类型: {report_type} | 周期: {period}")

            # 根据报告类型选择 OpenBB API
            if report_type == "balance_sheet":
                result = self.obb.equity.fundamental.balance(
                    obb_symbol,
                    period=period
                )
            elif report_type == "income":
                result = self.obb.equity.fundamental.income(
                    obb_symbol,
                    period=period
                )
            elif report_type == "cash_flow":
                result = self.obb.equity.fundamental.cash(
                    obb_symbol,
                    period=period
                )
            else:
                logger.warning(f"[OpenBB] 不支持的报告类型: {report_type}")
                return None

            if result is None:
                logger.warning(f"[OpenBB] 财报数据为空 | 股票: {symbol}")
                self.record_failure()
                return None

            df = result.to_dataframe() if hasattr(result, 'to_dataframe') else None

            if df is None or df.empty:
                logger.warning(f"[OpenBB] 财报数据解析失败 | 股票: {symbol}")
                self.record_failure()
                return None

            # 取最新一期数据
            row = df.iloc[0] if len(df) > 0 else None
            if row is None:
                self.record_failure()
                return None

            # 转换为字典格式
            data = {
                "raw_data": row.to_dict(),
                "report_date": str(row.name) if hasattr(row, 'name') else None,
            }

            # 提取常用字段
            if report_type == "balance_sheet":
                data["total_assets"] = float(row.get('total_assets', 0) or 0)
                data["total_liabilities"] = float(row.get('total_liabilities', 0) or 0)
                data["total_equity"] = float(row.get('total_equity', 0) or 0)
                data["current_assets"] = float(row.get('current_assets', 0) or 0)
                data["current_liabilities"] = float(row.get('current_liabilities', 0) or 0)
            elif report_type == "income":
                data["revenue"] = float(row.get('revenue', row.get('total_revenue', 0)) or 0)
                data["net_income"] = float(row.get('net_income', 0) or 0)
                data["earnings_per_share"] = float(row.get('eps', row.get('earnings_per_share', 0)) or 0)
                data["gross_profit"] = float(row.get('gross_profit', 0) or 0)
                data["operating_income"] = float(row.get('operating_income', 0) or 0)
            elif report_type == "cash_flow":
                data["operating_cash_flow"] = float(row.get('operating_cash_flow', 0) or 0)
                data["investing_cash_flow"] = float(row.get('investing_cash_flow', 0) or 0)
                data["financing_cash_flow"] = float(row.get('financing_cash_flow', 0) or 0)

            self.record_success()
            logger.info(f"[OpenBB] 财报数据获取成功 | 股票: {symbol} | 类型: {report_type}")
            return data

        except Exception as e:
            logger.error(f"[OpenBB] 财报获取异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
            return None

    def get_valuation_metrics(self, symbol: str, normalized_code: str,
                             market: str) -> Optional[Dict]:
        """
        获取估值指标

        Returns:
            估值指标字典，包含 PE/PB/ROE 等
        """
        if not self.is_available():
            return None

        obb_symbol = _convert_symbol_for_openbb(symbol, normalized_code, market)

        try:
            logger.info(f"[OpenBB] 获取估值指标 | 股票: {symbol}")

            # 获取估值比率数据
            result = self.obb.equity.fundamental.ratios(obb_symbol)

            if result is None:
                logger.warning(f"[OpenBB] 估值数据为空 | 股票: {symbol}")
                self.record_failure()
                return None

            df = result.to_dataframe() if hasattr(result, 'to_dataframe') else None

            if df is None or df.empty:
                logger.warning(f"[OpenBB] 估值数据解析失败 | 股票: {symbol}")
                self.record_failure()
                return None

            # 取最新数据
            row = df.iloc[0] if len(df) > 0 else None
            if row is None:
                self.record_failure()
                return None

            # 提取估值指标
            metrics = {
                "raw_data": row.to_dict(),
                "pe_ratio": float(row.get('price_to_earnings', row.get('pe_ratio', 0)) or 0) or None,
                "pb_ratio": float(row.get('price_to_book', row.get('pb_ratio', 0)) or 0) or None,
                "ps_ratio": float(row.get('price_to_sales', row.get('ps_ratio', 0)) or 0) or None,
                "roe": float(row.get('return_on_equity', row.get('roe', 0)) or 0) or None,
                "roa": float(row.get('return_on_assets', row.get('roa', 0)) or 0) or None,
                "profit_margin": float(row.get('net_margin', row.get('profit_margin', 0)) or 0) or None,
                "gross_margin": float(row.get('gross_margin', 0) or 0) or None,
                "current_ratio": float(row.get('current_ratio', 0) or 0) or None,
                "debt_to_equity": float(row.get('debt_to_equity', 0) or 0) or None,
                "dividend_yield": float(row.get('dividend_yield', 0) or 0) or None,
            }

            # 尝试获取营收增长（可能需要额外调用）
            try:
                growth_result = self.obb.equity.fundamental.growth(obb_symbol)
                if growth_result:
                    growth_df = growth_result.to_dataframe() if hasattr(growth_result, 'to_dataframe') else None
                    if growth_df is not None and not growth_df.empty:
                        growth_row = growth_df.iloc[0]
                        metrics["revenue_growth"] = float(growth_row.get('revenue_growth', 0) or 0) or None
            except Exception:
                pass  # 增长数据获取失败不影响其他指标

            self.record_success()
            logger.info(f"[OpenBB] 估值指标获取成功 | 股票: {symbol}")
            return metrics

        except Exception as e:
            logger.error(f"[OpenBB] 估值指标获取异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
            return None

    def get_macro_indicators(self, market: str = "cn",
                            indicators: List[str] = None) -> Optional[Dict]:
        """
        获取宏观经济指标

        Args:
            market: 市场类型 (cn, us)
            indicators: 指标列表 (gdp, cpi, interest_rate 等)

        Returns:
            宏观指标字典
        """
        if not self.is_available():
            return None

        if indicators is None:
            indicators = ["gdp", "cpi", "interest_rate"]

        try:
            logger.info(f"[OpenBB] 获取宏观指标 | 市场: {market} | 指标: {indicators}")

            results = {}

            for indicator in indicators:
                try:
                    if indicator == "gdp":
                        # GDP 增长率 - 使用 real GDP
                        country = "united_states" if market == "us" else "china"
                        result = self.obb.economy.gdp.real(country=country)
                        if result:
                            df = result.to_dataframe() if hasattr(result, 'to_dataframe') else None
                            if df is not None and not df.empty:
                                row = df.iloc[-1]  # 最新数据
                                results["gdp"] = {
                                    "value": float(row.get('value', 0) or 0),
                                    "unit": "%",
                                    "period": str(row.name) if hasattr(row, 'name') else None,
                                }

                    elif indicator == "cpi":
                        # CPI
                        country = "united_states" if market == "us" else "china"
                        result = self.obb.economy.cpi(country=country)
                        if result:
                            df = result.to_dataframe() if hasattr(result, 'to_dataframe') else None
                            if df is not None and not df.empty:
                                row = df.iloc[-1]
                                results["cpi"] = {
                                    "value": float(row.get('value', 0) or 0),
                                    "unit": "index",
                                    "period": str(row.name) if hasattr(row, 'name') else None,
                                }

                    elif indicator == "interest_rate":
                        # 利率
                        country = "united_states" if market == "us" else "china"
                        result = self.obb.economy.interest_rates(country=country)
                        if result:
                            df = result.to_dataframe() if hasattr(result, 'to_dataframe') else None
                            if df is not None and not df.empty:
                                row = df.iloc[-1]
                                results["interest_rate"] = {
                                    "value": float(row.get('value', 0) or 0),
                                    "unit": "%",
                                    "period": str(row.name) if hasattr(row, 'name') else None,
                                }

                except Exception as e:
                    logger.warning(f"[OpenBB] 获取指标 {indicator} 失败: {e}")
                    results[indicator] = {"error": str(e), "value": None}

            if not results:
                logger.warning(f"[OpenBB] 宏观指标全部获取失败 | 市场: {market}")
                self.record_failure()
                return None

            self.record_success()
            logger.info(f"[OpenBB] 宏观指标获取成功 | 市场: {market} | 数量: {len(results)}")
            return results

        except Exception as e:
            logger.error(f"[OpenBB] 宏观指标获取异常 | 市场: {market} | 错误: {e}")
            self.record_failure()
            return None
