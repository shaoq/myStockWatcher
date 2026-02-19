## 1. Frontend - DailyReport.jsx 清理

- [x] 1.1 移除 `trendData` state 和 `setTrendData`
- [x] 1.2 移除 `renderTrendChart()` 函数（约110行）
- [x] 1.3 移除 `loadReport()` 中的 `getTrendData` API 调用
- [x] 1.4 移除概览卡片渲染代码（4个统计卡片，约40行）
- [x] 1.5 移除达标率卡片渲染代码（约40行）
- [x] 1.6 移除趋势图表渲染代码（`<Card title="近 7 日趋势">` 部分）
- [x] 1.7 清理不再使用的导入（Statistic 等）

## 2. Frontend - API 服务层清理

- [x] 2.1 移除 `api.js` 中的 `getTrendData()` 方法

## 3. Backend - API 端点清理

- [x] 3.1 移除 `main.py` 中的 `/reports/trend` 端点

## 4. Backend - Schema 清理

- [x] 4.1 移除 `schemas.py` 中的 `TrendDataPoint` 模型
- [x] 4.2 移除 `schemas.py` 中的 `TrendDataResponse` 模型

## 5. Backend - Services 清理

- [x] 5.1 移除 `services.py` 中的 `get_trend_data()` 函数

## 6. 验证

- [x] 6.1 验证前端页面正常加载，只显示达标/未达标个股列表
- [x] 6.2 验证日期导航功能正常
- [x] 6.3 验证交易日状态显示正常
- [x] 6.4 验证后端 `/reports/daily` API 正常返回数据
