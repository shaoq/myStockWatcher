## Why

当前每日报告页面只展示"变化"的股票（新增达标、跌破均线），但用户无法查看**当日所有达标的股票详情**。当用户看到"今日达标 12 只"的统计数据时，无法知道具体是哪 12 只股票、各自达标的指标是什么、偏离程度如何。

这个问题在用户需要快速了解当前达标股票全貌时尤为突出，需要手动切换到股票列表页逐个查看。

## What Changes

- 新增"今日达标个股"展示区域，展示当日所有达标的股票及其达标指标
- 支持按偏离度降序排序（偏离越大越靠前）
- 支持分页浏览（默认每页 10 条）
- 同一股票的多个达标指标聚合为一行展示（用 Tag 形式显示所有达标的指标）
- 后端 API 扩展：`/reports/daily` 接口新增 `reached_stocks` 和 `total_reached` 字段

## Capabilities

### New Capabilities

- `reached-stocks-display`: 每日报告页面展示今日达标个股的能力，包括数据获取、聚合展示、排序和分页

### Modified Capabilities

- `daily-report`: 扩展每日报告 API 响应结构，新增 `reached_stocks`（达标股票列表）和 `total_reached`（总数）字段

## Impact

**后端修改**:
- `schemas.py`: 新增 `ReachedIndicator`、`ReachedStockItem` 模式，扩展 `DailyReportResponse`
- `services.py`: 修改 `get_daily_report()` 函数，增加达标股票的聚合、排序、分页逻辑
- `main.py`: 修改 `/reports/daily` 端点，支持 `page`、`page_size` 查询参数

**前端修改**:
- `DailyReport.jsx`: 新增"今日达标个股"表格组件、分页器、相关状态管理
- `api.js`: 扩展 `getDailyReport` 支持分页参数
