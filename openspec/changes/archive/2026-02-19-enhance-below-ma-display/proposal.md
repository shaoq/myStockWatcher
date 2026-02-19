## Why

当前每日报告的"跌破均线"仅统计状态变化的股票（昨天达标 → 今天不达标），导致与股票列表显示的"未达标"数量不一致，用户无法看到完整的未达标图景。用户需要看到所有未达标的股票，同时能快速识别哪些是刚跌破的（需重点关注）。

## What Changes

- **每日报告"跌破/未达标"区域**：从仅显示"状态变化"改为显示"所有未达标股票"
- **新增分类标注**：区分"新跌破"（🔴 昨天达标→今天不达标）和"持续未达标"（🟡 连续不达标）
- **统计卡片调整**：展示完整的未达标统计，包括新跌破数量和持续未达标数量
- **API 响应扩展**：返回所有未达标股票列表，每项包含 `fall_type` 字段标识类型

## Capabilities

### New Capabilities

无新增能力，这是对现有每日报告功能的增强。

### Modified Capabilities

- `daily-report`: 扩展"跌破均线"展示逻辑，从"状态变化"改为"所有未达标 + 分类标注"

## Impact

- **后端**：`services.py` 的 `get_daily_report` 函数需要修改
  - 新增 `all_below_stocks` 列表（所有未达标股票）
  - 每项增加 `fall_type` 字段（`new_fall` / `continuous_below`）
  - 新增统计字段：`newly_below_count`、`continuous_below_count`
- **前端**：`DailyReport.jsx` 需要修改
  - 折叠面板分组显示（新跌破优先）
  - 不同颜色标签区分类型
  - 统计卡片更新
- **API 兼容**：现有 `newly_below` 字段保持不变（向后兼容），新增 `all_below_stocks` 字段
