## Why

当前的每日报告页面中，"新增达标"展示方式不够直观：
1. 无法区分哪些指标是今天新达标的，哪些是持续达标的
2. 与"未达标个股"的展示方式不一致（未达标个股已区分"新跌破"和"持续未达标"）
3. "今日达标个股"表格与"新增达标"卡片重复展示相同信息
4. 概览卡片中的"新增达标"统计只是一个数字，无法快速了解详情

用户需要在查看报告时，能够快速识别达标股票的状态变化趋势。

## What Changes

### 新增功能
- 为每个达标指标添加状态分类：
  - **新增达标 (new_reach)**: 昨日未达标 → 今日达标
  - **持续达标 (continuous_reach)**: 昨日达标 → 今日继续达标
- "达标个股"卡片按 MA 分组展示，组内按状态分类（类似"未达标个股"）
- 使用不同颜色标识：
  - 🟢 新增达标（亮绿色）
  - 🟢 持续达标（淡绿色）

### 修改功能
- 将"新增达标"卡片重命名为"达标个股"
- 后端 API 返回数据中，为 `reached_indicators` 添加 `reach_type` 字段

### 移除功能
- 移除"今日达标个股"表格（与"达标个股"卡片重复）
- 移除概览卡片中的"新增达标"统计

## Capabilities

### New Capabilities
<!-- 无新增 capability，这是对现有 daily-report 和 reached-stocks-display 的改进 -->

### Modified Capabilities
- `daily-report`: 每日报告页面展示逻辑优化，移除重复组件
- `reached-stocks-display`: 达标股票展示增加状态分类（新增达标/持续达标）

## Impact

### 前端
- `frontend/src/components/DailyReport.jsx`:
  - 移除"今日达标个股"表格组件（第984-1075行）
  - 移除概览卡片中的"新增达标"统计（第878-886行）
  - 修改"新增达标"卡片为"达标个股"（第949-961行）
  - 新增函数：`renderReachedStocksWithReachType`
  - 新增函数：`flattenReachedStocks`
  - 新增函数：`groupByReachType`
  - 新增函数：`renderReachedItem`

### 后端
- `backend/app/services.py`:
  - 修改 `get_daily_report` 函数（第1084行附近）
  - 在计算 `reached_indicators` 时，对比昨日数据
  - 为每个达标指标添加 `reach_type` 字段

### 数据结构
- `GET /reports/daily` 响应中，`reached_stocks[].reached_indicators[]` 新增字段：
  ```json
  {
    "ma_type": "MA5",
    "ma_price": 10.20,
    "price_difference_percent": 2.5,
    "reach_type": "new_reach"  // 新增字段: "new_reach" | "continuous_reach"
  }
  ```

### 兼容性
- 前端向后兼容：如果后端未返回 `reach_type`，默认视为 `"new_reach"`
- 后端向前兼容：新增字段不影响现有 API 调用
