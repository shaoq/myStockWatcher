## Context

当前每日报告 API（`/reports/daily`）返回统计摘要和变化列表，但不返回完整的达标股票明细。前端无法展示"今日所有达标的股票"详情。

**现有数据流**：
```
StockSnapshot (ma_results JSON) → get_daily_report() → summary + changes only
```

**约束**：
- 快照数据已包含所有 MA 指标结果，无需额外 API 请求
- 需要保持 API 向后兼容（现有字段不变，只新增）
- 分页逻辑需在服务层实现，避免前端加载大量数据

## Goals / Non-Goals

**Goals:**
- 后端 API 返回达标股票明细，支持分页
- 同一股票的多个达标指标聚合为一行
- 按最大偏离度降序排序
- 前端表格展示 + Ant Design Pagination 组件

**Non-Goals:**
- 不支持按指标类型筛选（如"只看 MA5 达标的"）
- 不支持点击跳转到股票详情页
- 不改变现有 report 数据结构（只新增字段）

## Decisions

### D1: API 扩展方案
**决策**: 扩展现有 `/reports/daily` 接口，而非新建独立接口

**理由**:
- 减少前端请求次数
- 数据来源相同（同一快照），逻辑内聚
- 向后兼容（新增字段不影响现有消费者）

**备选方案**:
- 新建 `/reports/reached-stocks` 独立接口 → 拒绝：增加复杂度，数据来源相同

### D2: 聚合策略
**决策**: 同一股票的多个达标指标聚合为一行，用 Tag 展示

**理由**:
- 用户明确要求"一只股票一行"
- 避免重复行，提高可读性
- Tag 形式与现有"变化列表"风格一致

**实现**:
```
reached_indicators: [
  { ma_type: "MA5", ma_price: 10.20, price_difference_percent: 2.94 },
  { ma_type: "MA20", ma_price: 10.00, price_difference_percent: 5.00 }
]
```

### D3: 排序策略
**决策**: 按 `max_deviation_percent` 降序排序

**理由**:
- 用户明确要求"越偏离越前面"
- 最大偏离度反映该股票最显著的达标情况

### D4: 分页实现位置
**决策**: 服务层分页（后端）

**理由**:
- 避免传输大量数据
- 前端状态管理更简单
- 与现有 API 风格一致

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 分页参数缺失时返回过多数据 | 默认 page_size=10，最大限制 50 |
| 历史快照数据格式不一致 | 在服务层做防御性解析，缺失字段返回 null |
| 前端表格高度影响布局 | 使用 Ant Design Table 的 scroll.y 属性限制高度 |

## Migration Plan

无需迁移：
- 纯新增功能，不修改现有数据
- API 向后兼容，现有前端代码不受影响

部署步骤：
1. 部署后端 API 扩展
2. 部署前端新组件
3. 验证分页、排序功能

## Open Questions

无待解决问题。
