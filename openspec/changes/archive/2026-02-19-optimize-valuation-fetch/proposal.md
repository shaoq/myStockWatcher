## Why

当前估值数据获取存在性能问题：
1. 每次请求都会调用 `stock_zh_a_spot_em()` 下载全量 A 股数据（5000+ 只股票）
2. 用户看到进度条，误以为在安装什么
3. 同一时间段内多次请求会重复下载相同数据

## What Changes

- **共享全量数据缓存**：EastMoney 和 AKShare Provider 共享同一份全量数据缓存
- **智能缓存时效控制**：
  - 交易时间内：缓存有效期 5 分钟（可配置）
  - 非交易时间：缓存有效期到下一交易日开盘
- **统一估值获取入口**：优先从缓存获取，缓存过期或不存在时才重新下载

## Capabilities

### New Capabilities

- `valuation-cache-manager`: 估值数据缓存管理器，提供全量数据共享缓存和时效控制

### Modified Capabilities

- `valuation-metrics-fetch`: 修改估值数据获取逻辑，使用缓存管理器

## Impact

- **后端代码**:
  - `backend/app/providers/eastmoney.py` - 添加估值获取能力，使用缓存
  - `backend/app/providers/akshare.py` - 修改估值获取逻辑，使用缓存
  - `backend/app/providers/` - 新增缓存管理模块
