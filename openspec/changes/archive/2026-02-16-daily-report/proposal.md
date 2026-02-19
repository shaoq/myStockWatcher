# Daily Report - 每日股票指标总结功能

## Why

当前系统只存储股票的实时状态，无法回顾历史指标变化。用户需要：
- 了解今日哪些股票达标状态发生了变化
- 对比历史数据，观察趋势
- 获得每日投资组合的总结报告

这个功能帮助用户更好地跟踪投资组合表现，及时发现买卖信号。

## What Changes

- 新增 `StockSnapshot` 数据表，存储每只股票的每日快照
- 新增快照生成 API，支持手动保存当前状态
- 新增每日报告 API，提供达标变化分析和趋势数据
- 新增前端 `/daily-report` 页面，展示报告和趋势图表
- 在应用启动时自动检查今日是否有快照

## Capabilities

### New Capabilities

- `stock-snapshot`: 股票快照存储能力，支持每日保存股票的指标状态
- `daily-report`: 每日报告生成能力，对比分析达标变化和历史趋势

### Modified Capabilities

无（这是新增功能，不修改现有行为）

## Impact

### 后端
- `backend/app/models.py`: 新增 `StockSnapshot` 模型
- `backend/app/schemas.py`: 新增快照和报告相关的 Pydantic 模式
- `backend/app/crud.py`: 新增快照 CRUD 操作
- `backend/app/services.py`: 新增快照生成和报告计算逻辑
- `backend/app/main.py`: 新增快照和报告 API 端点

### 前端
- `frontend/src/components/DailyReport.jsx`: 新增报告页面组件
- `frontend/src/services/api.js`: 新增快照和报告 API 调用
- `frontend/src/App.jsx`: 新增路由和侧边栏入口

### 依赖
- 前端可能需要引入图表库（如 @ant-design/charts 或 echarts）
