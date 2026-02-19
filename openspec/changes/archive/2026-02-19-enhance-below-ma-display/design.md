## Context

当前每日报告的"跌破均线"列表仅显示状态变化的股票（昨天达标 → 今天不达标）。用户反馈这与股票列表显示的"未达标"数量不一致，需要看到完整的未达标图景。

**现有实现**：
- `services.py` 的 `get_daily_report()` 函数
- `newly_below_list` 只收集 `not today_reached and yesterday_reached` 的股票
- 前端 `DailyReport.jsx` 直接展示 `newly_below` 列表

## Goals / Non-Goals

**Goals:**
- 显示所有当日未达标的股票
- 区分标注"新跌破"（🔴）和"持续未达标"（🟡）
- 保持 API 向后兼容

**Non-Goals:**
- 不修改快照生成逻辑
- 不修改 MA 计算逻辑
- 不添加新的 API 端点

## Decisions

### Decision 1: API 响应结构扩展

**选择**：在现有响应中新增 `all_below_stocks` 字段，保留 `newly_below` 向后兼容

**理由**：
- 现有前端依赖 `newly_below`，直接修改会破坏兼容性
- 新增字段允许渐进式迁移

**响应结构**：
```json
{
  "summary": {
    "total_stocks": 10,
    "reached_count": 6,
    "newly_reached": 2,
    "newly_below": 2,
    "continuous_below": 2,  // 新增
    "reached_rate": 60.0,
    "reached_rate_change": 5.0
  },
  "newly_below": [...],  // 保留，仅状态变化
  "all_below_stocks": [  // 新增，所有未达标
    {
      "stock_id": 1,
      "symbol": "600000",
      "name": "浦发银行",
      "current_price": 10.50,
      "ma_type": "MA5",
      "ma_price": 11.20,
      "price_difference_percent": -6.25,
      "fall_type": "new_fall"  // 或 "continuous_below"
    }
  ]
}
```

### Decision 2: 前端显示策略

**选择**：折叠面板分组，先显示"新跌破"，再显示"持续未达标"

**理由**：
- 用户更关注刚跌破的股票（需要决策）
- 持续未达标的股票可能已被关注

**UI 设计**：
```
┌─ MA5 (4只) ────────────────────────────────────────┐
│ 🔴 新跌破 (2只)                                     │
│   ├─ 600000 浦发银行  偏离: -6.25%                  │
│   └─ 000001 平安银行  偏离: -3.91%                  │
│                                                    │
│ 🟡 持续未达标 (2只)                                 │
│   ├─ 601398 工商银行  偏离: -5.45%                  │
│   └─ 601939 建设银行  偏离: -4.23%                  │
└────────────────────────────────────────────────────┘
```

### Decision 3: 判断逻辑

**fall_type 判断规则**：
- `new_fall`: 昨日快照存在 AND 昨日达标 AND 今日不达标
- `continuous_below`: 昨日快照不存在 OR (昨日不达标 AND 今日不达标)

## Risks / Trade-offs

### Risk: 数据量增加
- **风险**：未达标股票较多时，API 响应变大
- **缓解**：暂不分页，因为单用户监控数量通常 < 100 只

### Risk: 前端改动范围
- **风险**：需要修改显示逻辑和统计卡片
- **缓解**：保持组件结构，仅修改数据源和渲染逻辑

## Open Questions

无。实现方案已明确。
