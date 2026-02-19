## Why

用户在每日报告页面选择日期时，无法直观地知道哪些日期已有报告数据，需要逐个点击查看。通过在日历上为有报告的日期添加视觉标志，用户可以快速识别有数据的日期，提升使用体验。

## What Changes

- 在日期选择器的日历面板中，为有报告数据的日期添加绿色小圆点标志
- 无报告的日期保持原样显示
- 标志使用现有的 `availableDates` 数据，无需新增 API 请求

## Capabilities

### New Capabilities

无新增能力，属于现有功能的体验优化。

### Modified Capabilities

- `daily-report`: 日期选择器增加报告存在性视觉标志

## Impact

- **前端**: `frontend/src/components/DailyReport.jsx` - 添加 `cellRender` 属性到 DatePicker 组件
- **后端**: 无需修改，复用现有 `/snapshots/dates` API
- **依赖**: 使用 Ant Design DatePicker 的 `cellRender` API
