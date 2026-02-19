## Context

每日报告页面使用 Ant Design 的 DatePicker 组件选择日期。组件已有 `availableDates` 状态存储有快照的日期列表。需要在日历面板中为这些日期添加视觉标志。

## Goals / Non-Goals

**Goals:**
- 在日历上为有报告的日期添加绿色小圆点标志
- 复用现有数据，无额外 API 请求
- 标志清晰可见但不影响日期阅读

**Non-Goals:**
- 不改变日期选择逻辑
- 不添加点击交互（标志仅作为视觉提示）

## Decisions

### 1. 使用 cellRender API

**决策：使用 Ant Design DatePicker 的 `cellRender` 属性**

**理由：**
- Ant Design v5 推荐的官方 API
- 可以完全控制日期单元格的渲染
- 保持原有交互行为

### 2. 标志样式

**决策：右上角绿色小圆点（6px）**

```jsx
<span style={{
  position: 'absolute',
  top: 2,
  right: 2,
  width: 6,
  height: 6,
  borderRadius: '50%',
  background: '#52c41a'
}} />
```

**理由：**
- 绿色（#52c41a）表示"有数据/正常"，符合系统语义
- 6px 小圆点不遮挡日期数字
- 位于右上角，不干扰阅读

### 3. 数据匹配

**决策：使用日期字符串比较**

```jsx
const hasReport = availableDates.some(
  d => d.format('YYYY-MM-DD') === current.format('YYYY-MM-DD')
);
```

**理由：**
- 简单可靠，避免时区问题
- `availableDates` 已是 dayjs 对象数组

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 日历渲染性能 | `availableDates` 通常 < 100 条，性能影响可忽略 |
| 标志在某些主题下不清晰 | 使用系统主题色，与整体风格一致 |
