"""
新浪财经数据源提供者

使用新浪财经 API 获取股票数据。
速度快但容易被封禁，作为 L1 主数据源。
"""

import re
import json
import logging
import time
import requests
from typing import Optional, List, Dict
from datetime import datetime

from .base import DataProvider, StockData

logger = logging.getLogger(__name__)

# 创建带有 User-Agent 的 session
_session = requests.Session()
_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'http://finance.sina.com.cn'
})


class SinaProvider(DataProvider):
    """新浪财经数据源 (L1 - 最高优先级)"""

    PRIORITY = 1
    NAME = "sina"
    CAPABILITIES = {"realtime_price", "kline_data"}

    def _http_get(self, url: str, timeout: int = 5) -> Optional[requests.Response]:
        """
        统一的 HTTP GET 请求

        Args:
            url: 请求 URL
            timeout: 超时时间（秒）

        Returns:
            Response 或 None
        """
        try:
            response = _session.get(url, timeout=timeout)
            elapsed_ms = (response.elapsed.total_seconds()) * 1000

            # 检测封禁状态
            if response.status_code == 429:
                logger.warning(f"[新浪] 请求过于频繁 (429) | URL: {url}")
                self.mark_banned()
                return None
            elif response.status_code == 403:
                logger.warning(f"[新浪] 访问被拒绝 (403) | URL: {url}")
                self.mark_banned()
                return None
            elif response.status_code != 200:
                logger.warning(f"[新浪] 请求失败 | 状态码: {response.status_code} | URL: {url}")
                return None

            logger.debug(f"[新浪] 请求成功 | 耗时: {elapsed_ms:.0f}ms")
            return response

        except requests.exceptions.Timeout:
            logger.error(f"[新浪] 请求超时 | URL: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[新浪] 请求异常 | 错误: {e} | URL: {url}")
            return None

    def get_realtime_price(self, symbol: str, normalized_code: str, market: str) -> Optional[StockData]:
        """
        获取实时价格

        新浪实时行情接口:
        - A股: http://hq.sinajs.cn/list=sh600000
        - 美股: http://hq.sinajs.cn/list=gb_aapl
        """
        if market == "cn":
            url = f"http://hq.sinajs.cn/list={normalized_code}"
        else:
            # 美股需要小写并加 gb_ 前缀
            url = f"http://hq.sinajs.cn/list=gb_{normalized_code.lower()}"

        response = self._http_get(url)
        if response is None:
            self.record_failure()
            return None

        try:
            # 解析返回数据: var hq_str_sh600000="浦发银行,10.50,10.40,10.55,..."
            match = re.search(r'="([^"]+)"', response.text)
            if not match:
                logger.warning(f"[新浪] 数据格式异常 | 股票: {symbol}")
                self.record_failure()
                return None

            data = match.group(1).split(',')
            if len(data) < 4:
                logger.warning(f"[新浪] 数据字段不足 | 股票: {symbol}")
                self.record_failure()
                return None

            if market == "cn":
                # A股: 名称,今开,昨收,当前,最高,最低,买一,卖一,成交量,成交额,...
                name = data[0]
                current_price = float(data[3]) if data[3] else None
                open_price = float(data[1]) if data[1] else None
                close_price = float(data[2]) if data[2] else None
                high_price = float(data[4]) if data[4] else None
                low_price = float(data[5]) if data[5] else None
                volume = int(float(data[8])) if data[8] else None
                turnover = float(data[9]) if data[9] else None
            else:
                # 美股: 名称,当前价格,...
                name = data[0]
                current_price = float(data[1]) if len(data) > 1 and data[1] else None
                open_price = None
                close_price = None
                high_price = None
                low_price = None
                volume = None
                turnover = None

            # 价格为 0 表示无效数据（停牌、退市等）
            if current_price is None or current_price <= 0:
                logger.warning(f"[新浪] 价格无效 | 股票: {symbol} | 价格: {current_price}")
                self.record_failure()
                return None

            self.record_success()
            return StockData(
                symbol=symbol,
                name=name,
                current_price=current_price,
                open_price=open_price,
                close_price=close_price,
                high_price=high_price,
                low_price=low_price,
                volume=volume,
                turnover=turnover,
                provider_name=self.NAME
            )

        except (ValueError, IndexError) as e:
            logger.error(f"[新浪] 数据解析异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
            return None

    def get_kline_data(self, symbol: str, normalized_code: str, market: str,
                       datalen: int = 30) -> Optional[List[Dict]]:
        """
        获取 K 线数据

        新浪 K 线接口:
        - A股: http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh600000&scale=240&ma=no&datalen=30
        - 美股: https://stock.finance.sina.com.cn/usstock/api/jsonp.php/IO.Direct.Quotes.getKLineData?symbol=AAPL&scale=240&ma=no&datalen=30
        """
        if market == "cn":
            url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={normalized_code}&scale=240&ma=no&datalen={datalen}"
        else:
            url = f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/IO.Direct.Quotes.getKLineData?symbol={normalized_code.upper()}&scale=240&ma=no&datalen={datalen}"

        response = self._http_get(url)
        if response is None:
            self.record_failure()
            return None

        try:
            if market == "us":
                # 美股返回 JSONP 格式，需要提取 JSON 部分
                match = re.search(r'\[.*\]', response.text)
                data = json.loads(match.group()) if match else []
            else:
                data = response.json()

            if not data or not isinstance(data, list):
                logger.warning(f"[新浪] K线数据为空 | 股票: {symbol}")
                self.record_failure()
                return None

            # 规范化 K 线数据格式
            kline_list = []
            for item in data:
                try:
                    kline_list.append({
                        "day": item.get("day", ""),
                        "open": float(item.get("open", 0)),
                        "close": float(item.get("close", 0)),
                        "high": float(item.get("high", 0)),
                        "low": float(item.get("low", 0)),
                        "volume": int(float(item.get("volume", 0))),
                    })
                except (ValueError, TypeError):
                    continue

            if not kline_list:
                logger.warning(f"[新浪] K线数据解析后为空 | 股票: {symbol}")
                self.record_failure()
                return None

            self.record_success()
            logger.info(f"[新浪] K线数据获取成功 | 股票: {symbol} | 数量: {len(kline_list)}")
            return kline_list

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[新浪] K线数据解析异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
            return None
