## Why

每日报告页面信息过载，用户反馈核心关注的只是"哪些股票达标"和"哪些股票未达标"，概览统计卡片、达标率卡片和趋势图表增加了页面复杂度但实际使用价值不高。

简化页面结构，聚焦核心功能，提升用户体验和页面加载速度。

## What Changes

### 移除内容

- **概览卡片**：移除4个统计卡片（监控总数、今日达标、跌破均线、持续未达标）
- **达标率卡片**：移除达标率和较昨日变化的展示
- **趋势图表**：移除近7日趋势柱状图

### 保留内容

- **达标个股板块**：按MA分组展示，区分新增达标/持续达标
- **未达标个股板块**：按MA分组展示，区分新跌破/持续未达标
- **日期导航**：日期选择器、前后日期切换
- **交易日状态**：显示交易日/休市状态

## Capabilities

### New Capabilities

无新增能力。

### Modified Capabilities

- `daily-report`: 移除趋势数据要求，移除概览统计卡片要求，简化报告页面为只展示达标/未达标个股列表

## Impact

### 前端 (frontend/src/components/DailyReport.jsx)

- 移除概览卡片渲染代码（约40行）
- 移除达标率卡片渲染代码（约40行）
- 移除趋势图表渲染代码（约110行）
- 移除 `trendData` state 和 `setTrendData`
- 移除 `renderTrendChart()` 函数
- 移除 `stockApi.getTrendData()` API 调用

### 前端 API (frontend/src/services/api.js)

- 移除 `getTrendData()` 方法

### 后端 (backend/app/main.py)

- 移除 `/reports/trend` API 端点

### 后端 Schema (backend/app/schemas.py)

- 移除 `TrendDataPoint` 模型
- 移除 `TrendDataResponse` 模型

### 后端 Services (backend/app/services.py)

- 移除 `get_trend_data()` 函数（约40行）
