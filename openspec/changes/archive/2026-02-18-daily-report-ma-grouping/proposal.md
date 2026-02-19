## Why

每日报告页面的"新增达标"和"跌破均线"列表目前采用扁平展示方式，当同一只股票多个指标同时达标或跌破时，会出现多条重复记录，用户难以快速聚焦特定指标维度的变化。

通过按 MA 指标分组展示，用户可以更直观地查看每个指标维度的股票变化情况，便于分析不同周期均线的市场表现。

## What Changes

- 将"新增达标"和"跌破均线"列表从扁平展示改为按 MA 指标分组展示
- 每个分组使用折叠/展开面板（Collapse），支持用户按需查看
- 分组标题显示 MA 类型和数量（如 "MA5 (3只)"）
- MA 分组按数字大小升序排列（MA5 → MA10 → MA20 → MA60）
- 组内个股按偏离度降序排列（偏离越大越靠前）
- 空分组不显示

## Capabilities

### New Capabilities

无新增能力，属于现有功能的体验优化。

### Modified Capabilities

- `daily-report`: 优化报告页面的变化列表展示方式，从扁平列表改为按 MA 指标分组展示

## Impact

- **前端**: `frontend/src/components/DailyReport.jsx` - 修改 `renderChangeItem` 和变化列表渲染逻辑
- **后端**: 无需修改，现有 API 返回数据已包含 `ma_type` 字段
- **依赖**: 使用 Ant Design 的 `Collapse` 组件
