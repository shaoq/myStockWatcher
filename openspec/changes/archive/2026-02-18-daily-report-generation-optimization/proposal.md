## Why

当前每日报告生成逻辑存在以下问题：
1. **缺少交易日判断**：非交易日（周末、节假日）也会触发报告生成，产生无效数据
2. **历史报告缺失**：用户无法为过去的交易日补充生成报告
3. **用户体验不佳**：非交易日访问时没有明确的"休市"提示

这些问题导致用户在非交易日看到空报告或困惑，且无法补全历史报告数据。

## What Changes

1. **新增交易日历服务**
   - 通过 AkShare API 获取中国 A 股交易日历
   - 缓存交易日历数据（年度缓存，自动刷新）
   - 提供交易日判断接口

2. **优化报告生成逻辑**
   - 交易日：用最新实时数据生成当天报告
   - 非交易日：提示"休市中"，不生成报告

3. **支持历史报告生成**
   - 用户可选择历史交易日生成报告
   - 历史数据使用 K 线收盘价
   - 自动判断是否需要重新获取数据

4. **前端交互优化**
   - 日期选择器提示交易日/非交易日
   - 非交易日显示"休市"状态
   - 历史报告生成按钮

## Capabilities

### New Capabilities

- `trading-calendar`: 交易日历服务，提供交易日判断、缓存管理功能
- `historical-snapshot`: 历史快照生成能力，支持为历史交易日生成快照数据

### Modified Capabilities

- `daily-report`: 扩展每日报告能力，增加交易日判断和历史报告生成支持

## Impact

### 后端
- `backend/app/services.py`: 新增交易日历服务、历史数据获取逻辑
- `backend/app/crud.py`: 新增交易日历缓存 CRUD
- `backend/app/models.py`: 新增 `TradingCalendar` 模型
- `backend/app/main.py`: 新增交易日历 API 端点
- `backend/requirements.txt`: 新增 `akshare` 依赖

### 前端
- `frontend/src/components/DailyReport.jsx`: 交易日提示、历史报告生成交互
- `frontend/src/services/api.js`: 新增交易日历 API 调用

### 数据库
- 新增 `trading_calendar` 表
