"""
网易财经数据源提供者

使用网易财经 API 获取股票数据。
稳定性好，作为 L4 兜底数据源。
"""

import logging
import requests
import json
from typing import Optional, List, Dict
from datetime import datetime

from .base import DataProvider, StockData

logger = logging.getLogger(__name__)

# 创建带有 User-Agent 的 session
_session = requests.Session()
_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})


class NeteaseProvider(DataProvider):
    """网易财经数据源 (L4 - 兜底)"""

    PRIORITY = 4
    NAME = "netease"
    CAPABILITIES = {"realtime_price", "kline_data"}

    def _http_get(self, url: str, timeout: int = 5) -> Optional[requests.Response]:
        """统一的 HTTP GET 请求"""
        try:
            response = _session.get(url, timeout=timeout)

            if response.status_code == 429 or response.status_code == 403:
                logger.warning(f"[网易] 访问受限 ({response.status_code}) | URL: {url}")
                self.mark_banned()
                return None
            elif response.status_code != 200:
                logger.warning(f"[网易] 请求失败 | 状态码: {response.status_code}")
                return None

            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"[网易] 请求异常 | 错误: {e}")
            return None

    def get_realtime_price(self, symbol: str, normalized_code: str, market: str) -> Optional[StockData]:
        """
        获取实时价格

        网易实时行情接口:
        - A股: http://api.money.126.net/data/feed/600000.money.json
        """
        if market != "cn":
            logger.debug(f"[网易] 不支持美股 | 股票: {symbol}")
            return None

        # 解析代码，去掉市场前缀
        code = normalized_code[2:] if len(normalized_code) > 2 else normalized_code

        url = f"http://api.money.126.net/data/feed/{code}.money.json"

        response = self._http_get(url)
        if response is None:
            self.record_failure()
            return None

        try:
            # 网易返回 JSONP 格式: _ntes_quote_callback({"600000":{"code":"600000",...}});
            text = response.text
            match = json.loads(text[text.index('{'):text.rindex('}')+1])

            if not match:
                logger.warning(f"[网易] 数据格式异常 | 股票: {symbol}")
                self.record_failure()
                return None

            # 获取第一个键对应的数据
            data = list(match.values())[0]

            name = data.get('name', '')
            current_price = data.get('price')

            if current_price is None or current_price <= 0:
                logger.warning(f"[网易] 价格无效 | 股票: {symbol} | 价格: {current_price}")
                self.record_failure()
                return None

            self.record_success()
            return StockData(
                symbol=symbol,
                name=name,
                current_price=float(current_price),
                open_price=data.get('open'),
                close_price=data.get('yestclose'),
                high_price=data.get('high'),
                low_price=data.get('low'),
                volume=data.get('volume'),
                provider_name=self.NAME
            )

        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            logger.error(f"[网易] 数据解析异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
            return None

    def get_kline_data(self, symbol: str, normalized_code: str, market: str,
                       datalen: int = 30) -> Optional[List[Dict]]:
        """
        获取 K 线数据

        网易 K 线接口:
        http://quotes.money.163.com/service/chddata.html?code=sh600000&fields=TCLOSE;HIGH;LOW;TOPEN;VOLUME
        """
        if market != "cn":
            logger.debug(f"[网易] 不支持美股 K 线 | 股票: {symbol}")
            return None

        code = normalized_code[2:] if len(normalized_code) > 2 else normalized_code
        market_prefix = normalized_code[:2]  # sh 或 sz

        # 网易代码格式: 0+code (深圳) 或 1+code (上海)
        netease_code = f"1{code}" if market_prefix == "sh" else f"0{code}"

        url = f"http://quotes.money.163.com/service/chddata.html?code={netease_code}&fields=TCLOSE;HIGH;LOW;TOPEN;VOLUME&count={datalen}"

        response = self._http_get(url)
        if response is None:
            self.record_failure()
            return None

        try:
            # 网易返回 CSV 格式
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                logger.warning(f"[网易] K线数据为空 | 股票: {symbol}")
                self.record_failure()
                return None

            # 解析 CSV，跳过标题行
            kline_list = []
            for line in lines[1:]:
                parts = line.split(',')
                if len(parts) < 6:
                    continue
                try:
                    kline_list.append({
                        "day": parts[0],  # 日期
                        "close": float(parts[3]) if parts[3] else 0,  # 收盘价
                        "high": float(parts[4]) if parts[4] else 0,   # 最高价
                        "low": float(parts[5]) if parts[5] else 0,    # 最低价
                        "open": float(parts[6]) if parts[6] else 0,   # 开盘价
                        "volume": int(float(parts[7])) if parts[7] else 0,  # 成交量
                    })
                except (ValueError, IndexError):
                    continue

            if not kline_list:
                logger.warning(f"[网易] K线数据解析后为空 | 股票: {symbol}")
                self.record_failure()
                return None

            # 按日期排序（从旧到新）
            kline_list.reverse()

            self.record_success()
            logger.info(f"[网易] K线数据获取成功 | 股票: {symbol} | 数量: {len(kline_list)}")
            return kline_list

        except Exception as e:
            logger.error(f"[网易] K线数据解析异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
            return None
