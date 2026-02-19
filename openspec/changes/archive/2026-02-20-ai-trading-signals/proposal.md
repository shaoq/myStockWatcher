## Why

当前系统只有 MA（移动平均线）指标监控，缺乏更全面的技术分析和买卖信号建议。用户需要：
- 具体的买点/卖点价位建议
- 多种技术指标综合分析
- 每日收盘后自动生成信号

## What Changes

- **技术指标计算服务**：新增 MACD、RSI、KDJ、布林带等指标计算
- **买卖信号生成服务**：基于技术指标生成买入/卖出信号，包含具体价位建议
- **信号存储模型**：记录每日信号及其触发条件
- **前端展示**：在股票列表和趋势图中展示信号

## Capabilities

### New Capabilities

- `technical-indicators`: 技术指标计算服务，支持 MA/MACD/RSI/KDJ/布林带
- `trading-signals`: 买卖信号生成服务，输出买点/卖点价位和操作建议

### Modified Capabilities

无。这是新增功能。

## Impact

- **后端代码**:
  - `backend/app/services/indicators.py` - 新增技术指标计算
  - `backend/app/services/signals.py` - 新增信号生成逻辑
  - `backend/app/models.py` - 新增 Signal 模型
  - `backend/app/main.py` - 新增信号 API 端点
- **前端代码**:
  - `frontend/src/components/StockList.jsx` - 展示信号标签
  - `frontend/src/components/StockChart.jsx` - 展示信号详情
