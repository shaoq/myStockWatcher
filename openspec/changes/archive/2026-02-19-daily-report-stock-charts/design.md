## Context

每日报告页面展示达标个股和未达标个股列表，用户希望能够直接点击个股查看其趋势图，无需切换到股票列表页面。

股票列表页面 (`StockList.jsx`) 已经实现了这个功能，使用 `StockChart` 组件展示趋势图。我们需要在每日报告页面复用相同的实现。

## Goals / Non-Goals

**Goals:**
- 在每日报告的达标/未达标个股列表中支持点击查看趋势图
- 复用现有的 `StockChart` 组件
- 交互体验与股票列表保持一致

**Non-Goals:**
- 不修改 `StockChart` 组件
- 不添加新的API端点

## Decisions

### Decision 1: 复用 StockChart 组件

**选择**: 直接导入并使用现有的 `StockChart` 组件

**原因**:
- 代码复用，避免重复实现
- 保持UI一致性
- `StockChart` 组件已经封装了图表获取逻辑和展示样式

### Decision 2: 点击区域设计

**选择**: 股票代码和名称都可点击

**原因**:
- 与股票列表的交互保持一致
- 提供更大的点击区域，提升用户体验

### Decision 3: Modal 样式

**选择**: 使用与股票列表相同的 Modal 配置

**原因**:
- 保持一致的用户体验
- Modal 宽度 650px，居中显示，支持关闭时销毁

## Risks / Trade-offs

### Risk: 性能影响

**缓解**: `StockChart` 组件内部已有加载状态处理，用户点击时才会加载数据

### Risk: 用户体验一致性

**缓解**: 完全复用 `StockChart` 组件，确保视觉效果一致

## Migration Plan

无需数据库迁移，纯前端改动：

1. 添加 state 变量
2. 添加 `showChartModal` 函数
3. 导入 `StockChart` 组件
4. 修改列表项渲染函数，添加点击事件
5. 添加 Modal 组件
