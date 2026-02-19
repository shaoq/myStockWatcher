"""
腾讯财经数据源提供者

使用腾讯财经 API 获取股票数据。
稳定性较好，作为 L3 备用数据源。
"""

import re
import logging
import requests
from typing import Optional, List, Dict
from datetime import datetime

from .base import DataProvider, StockData

logger = logging.getLogger(__name__)

# 创建带有 User-Agent 的 session
_session = requests.Session()
_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})


class TencentProvider(DataProvider):
    """腾讯财经数据源 (L3 - 备用)"""

    PRIORITY = 3
    NAME = "tencent"
    CAPABILITIES = {"realtime_price", "kline_data"}

    def _http_get(self, url: str, timeout: int = 5) -> Optional[requests.Response]:
        """统一的 HTTP GET 请求"""
        try:
            response = _session.get(url, timeout=timeout)

            if response.status_code == 429 or response.status_code == 403:
                logger.warning(f"[腾讯] 访问受限 ({response.status_code}) | URL: {url}")
                self.mark_banned()
                return None
            elif response.status_code != 200:
                logger.warning(f"[腾讯] 请求失败 | 状态码: {response.status_code}")
                return None

            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"[腾讯] 请求异常 | 错误: {e}")
            return None

    def get_realtime_price(self, symbol: str, normalized_code: str, market: str) -> Optional[StockData]:
        """
        获取实时价格

        腾讯实时行情接口:
        - A股: https://web.sqt.gtimg.cn/q=r_sh600000
        - 美股: https://web.sqt.gtimg.cn/q=r_gb_aapl
        """
        if market == "cn":
            # 腾讯使用 r_ 前缀
            code = f"r_{normalized_code}"
        else:
            # 美股使用 r_gb_ 前缀，小写
            code = f"r_gb_{normalized_code.lower()}"

        url = f"https://web.sqt.gtimg.cn/q={code}"

        response = self._http_get(url)
        if response is None:
            self.record_failure()
            return None

        try:
            # 解析返回数据: v_r_sh600000="1~浦发银行~600000~10.50~..."
            text = response.text
            match = re.search(r'="([^"]+)"', text)
            if not match:
                logger.warning(f"[腾讯] 数据格式异常 | 股票: {symbol}")
                self.record_failure()
                return None

            data = match.group(1).split('~')
            if len(data) < 5:
                logger.warning(f"[腾讯] 数据字段不足 | 股票: {symbol}")
                self.record_failure()
                return None

            # 腾讯格式: ~名称~代码~当前价格~昨收~今开~...
            name = data[1]
            current_price = float(data[3]) if data[3] else None

            if current_price is None or current_price <= 0:
                logger.warning(f"[腾讯] 价格无效 | 股票: {symbol} | 价格: {current_price}")
                self.record_failure()
                return None

            self.record_success()
            return StockData(
                symbol=symbol,
                name=name,
                current_price=current_price,
                open_price=float(data[5]) if len(data) > 5 and data[5] else None,
                close_price=float(data[4]) if len(data) > 4 and data[4] else None,
                high_price=float(data[33]) if len(data) > 33 and data[33] else None,
                low_price=float(data[34]) if len(data) > 34 and data[34] else None,
                provider_name=self.NAME
            )

        except (ValueError, IndexError) as e:
            logger.error(f"[腾讯] 数据解析异常 | 股票: {symbol} | 错误: {e}")
            self.record_failure()
            return None

    def get_kline_data(self, symbol: str, normalized_code: str, market: str,
                       datalen: int = 30) -> Optional[List[Dict]]:
        """
        获取 K 线数据

        腾讯 K 线接口暂不实现，返回 None 让协调器尝试下一个数据源
        """
        logger.debug(f"[腾讯] K线接口暂不支持 | 股票: {symbol}")
        return None
