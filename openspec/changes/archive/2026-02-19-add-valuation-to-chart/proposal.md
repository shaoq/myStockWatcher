## Why

用户在查看股票趋势图时，无法同时看到该股票的估值指标（PE、PB、ROE等），需要额外去其他平台查询，体验不连贯。

将估值指标集成到趋势图对话框中，可以让用户在一个界面内完成技术面（趋势图）和基本面（估值指标）的综合分析。

## What Changes

- **StockChart 组件增强**：在趋势图对话框中添加估值指标展示
  - 顶部显示核心估值卡片（PE/PB/ROE/利润率/营收增长）
  - 新增"估值详情"Tab，展示完整估值数据分组（估值/盈利/成长/财务/每股）
- **前端 API 扩展**：封装 `/stocks/{symbol}/valuation` 接口调用
- **错误状态处理**：估值数据获取失败时显示友好提示

## Capabilities

### New Capabilities

- `chart-valuation-display`: 趋势图对话框中的估值指标展示能力，包括顶部核心指标卡片和详情Tab

### Modified Capabilities

无。这是新增功能，不改变现有 spec 的需求。

## Impact

- **前端代码**:
  - `frontend/src/components/StockChart.jsx` - 添加估值卡片和Tab
  - `frontend/src/services/api.js` - 封装估值API
- **后端代码**: 无变更（估值API已存在）
- **数据源**: 复用现有 `/stocks/{symbol}/valuation` 端点（AKShare/OpenBB）
