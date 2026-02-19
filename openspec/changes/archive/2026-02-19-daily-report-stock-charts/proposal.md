## Why

用户在每日报告页面查看达标/未达标个股时，想要快速查看个股的日线图等趋势数据，目前需要切换到股票列表页面才能查看，操作不便。

在每日报告中直接支持点击个股名称或编码查看趋势图，与股票列表的交互体验保持一致。

## What Changes

### 新增功能

- **点击查看趋势图**：在达标个股和未达标个股列表中，点击股票代码或名称时弹出趋势图Modal
- **趋势图Modal**：复用 `StockChart` 组件，展示分时图、日K线、周K线、月K线

### 交互细节

- 鼠标悬停在股票代码/名称上时显示手型光标
- 点击后弹出Modal，展示该股票的趋势图
- Modal样式和交互与股票列表页面保持一致

## Capabilities

### New Capabilities

- `daily-report-stock-charts`: 在每日报告页面支持点击个股查看趋势图

### Modified Capabilities

- `daily-report`: 扩展报告页面交互，支持个股趋势图查看

## Impact

### 前端 (frontend/src/components/DailyReport.jsx)

- 新增 `chartModalVisible` state
- 新增 `selectedSymbol` state
- 新增 `showChartModal` 函数
- 新增趋势图 Modal 组件
- 导入 `StockChart` 组件
- 修改 `renderReachedItem` 和 `renderBelowItem` 函数，添加点击事件
