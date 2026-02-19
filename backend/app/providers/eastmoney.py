"""
东方财富数据源提供者

通过 AKShare 库获取东方财富数据。
稳定性好，作为 L2 备用数据源。
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime

from .base import DataProvider, StockData

logger = logging.getLogger(__name__)


class EastMoneyProvider(DataProvider):
    """东方财富数据源 (L2 - 通过 AKShare)"""

    PRIORITY = 2
    NAME = "eastmoney"
    CAPABILITIES = {"realtime_price", "kline_data"}

    def _get_akshare(self):
        """延迟导入 AKShare，避免未安装时报错"""
        try:
            import akshare as ak
            return ak
        except ImportError:
            logger.error("[东方财富] AKShare 库未安装")
            return None

    def get_realtime_price(self, symbol: str, normalized_code: str, market: str) -> Optional[StockData]:
        """
        获取实时价格

        使用 AKShare 的实时行情接口
        """
        if market != "cn":
            # AKShare 主要支持 A 股，美股暂不支持
            logger.debug(f"[东方财富] 不支持美股 | 股票: {symbol}")
            return None

        ak = self._get_akshare()
        if ak is None:
            return None

        try:
            # 使用新浪实时行情（AKShare 封装）
            # 注意: normalized_code 格式为 "sh600000" 或 "sz000001"
            df = ak.stock_zh_a_spot_em()

            # 解析代码，去掉市场前缀
            code = normalized_code[2:] if len(normalized_code) > 2 else normalized_code

            # 查找对应股票
            row = df[df['代码'] == code]
            if row.empty:
                logger.warning(f"[东方财富] 未找到股票 | 股票: {symbol} | 代码: {code}")
                self.record_failure()
                return None

            row = row.iloc[0]
            name = row.get('名称', '')
            current_price = row.get('最新价', None)

            if current_price is None or current_price <= 0:
                logger.warning(f"[东方财富] 价格无效 | 股票: {symbol} | 价格: {current_price}")
                self.record_failure()
                return None

            self.record_success()
            return StockData(
                symbol=symbol,
                name=name,
                current_price=float(current_price),
                open_price=row.get('今开'),
                close_price=row.get('昨收'),
                high_price=row.get('最高'),
                low_price=row.get('最低'),
                volume=row.get('成交量'),
                turnover=row.get('成交额'),
                provider_name=self.NAME
            )

        except Exception as e:
            logger.error(f"[东方财富] 获取实时价格异常 | 股票: {symbol} | 错误: {type(e).__name__}: {e}")
            self.record_failure()
            return None

    def get_kline_data(self, symbol: str, normalized_code: str, market: str,
                       datalen: int = 30) -> Optional[List[Dict]]:
        """
        获取 K 线数据

        使用 AKShare 的历史 K 线接口
        """
        if market != "cn":
            logger.debug(f"[东方财富] 不支持美股 K 线 | 股票: {symbol}")
            return None

        ak = self._get_akshare()
        if ak is None:
            return None

        try:
            # 解析代码，去掉市场前缀
            code = normalized_code[2:] if len(normalized_code) > 2 else normalized_code

            # 使用东方财富历史 K 线接口
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")

            if df is None or df.empty:
                logger.warning(f"[东方财富] K线数据为空 | 股票: {symbol}")
                self.record_failure()
                return None

            # 取最近的 datalen 条数据
            df = df.tail(datalen)

            # 转换为标准格式
            kline_list = []
            for _, row in df.iterrows():
                try:
                    kline_list.append({
                        "day": row['日期'].strftime('%Y-%m-%d') if hasattr(row['日期'], 'strftime') else str(row['日期']),
                        "open": float(row['开盘']),
                        "close": float(row['收盘']),
                        "high": float(row['最高']),
                        "low": float(row['最低']),
                        "volume": int(row['成交量']),
                    })
                except (ValueError, TypeError, KeyError) as e:
                    logger.debug(f"[东方财富] 跳过无效数据行 | 错误: {e}")
                    continue

            if not kline_list:
                logger.warning(f"[东方财富] K线数据解析后为空 | 股票: {symbol}")
                self.record_failure()
                return None

            self.record_success()
            logger.info(f"[东方财富] K线数据获取成功 | 股票: {symbol} | 数量: {len(kline_list)}")
            return kline_list

        except Exception as e:
            logger.error(f"[东方财富] 获取 K 线数据异常 | 股票: {symbol} | 错误: {type(e).__name__}: {e}")
            self.record_failure()
            return None
