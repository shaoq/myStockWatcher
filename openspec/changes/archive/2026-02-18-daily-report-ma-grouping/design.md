## Context

每日报告页面的"新增达标"和"跌破均线"列表目前使用 Ant Design 的 `List` 组件扁平展示。当同一只股票多个 MA 指标同时变化时，会出现多条记录，用户难以快速聚焦特定指标维度。

现有数据结构（后端 API 已返回）：
```javascript
newly_reached: [
  {stock_id, symbol, name, ma_type: "MA5", current_price, ma_price, price_difference_percent},
  {stock_id, symbol, name, ma_type: "MA10", current_price, ma_price, price_difference_percent},
  // ...
]
```

## Goals / Non-Goals

**Goals:**
- 前端按 MA 指标分组展示变化列表
- 支持折叠/展开功能
- 分组按数字大小升序排列
- 组内按偏离度降序排列
- 空分组不显示

**Non-Goals:**
- 不修改后端 API
- 不改变数据获取逻辑
- 不影响其他报告功能

## Decisions

### 1. 前端数据分组（vs 后端重组）

**决策：前端分组**

**理由：**
- 现有 API 已返回 `ma_type` 字段，前端可直接分组
- 无需后端改动，降低风险
- 数据量小（通常 < 50 条），前端计算性能无影响

**备选方案：后端重组数据结构**
- 优点：前端实现更简单
- 缺点：需要修改 API 响应格式，可能影响其他调用方

### 2. 使用 Collapse 组件

**决策：使用 Ant Design Collapse 组件**

**理由：**
- 项目已使用 Ant Design，风格一致
- 原生支持折叠/展开功能
- 可自定义面板头部显示 MA 类型和数量

### 3. 分组排序算法

**决策：提取 MA 数字后按数值升序排序**

```javascript
const getMANumber = (maType) => parseInt(maType.replace(/\D/g, ''), 10);
// MA5 → 5, MA10 → 10, MA20 → 20
```

**理由：**
- 简单可靠，支持任意 MA 命名格式
- 符合用户直觉（短周期在前）

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 数据量大时前端计算性能 | 预期数据量 < 100 条，性能无影响。如需优化可后续考虑虚拟滚动 |
| 折叠状态在日期切换时丢失 | 接受此行为，每次切换日期重置为默认展开状态 |
| 非标准 MA 命名导致排序异常 | 使用正则提取数字，非数字格式置于末尾 |
