# Daily Report Design

## Context

当前系统存储股票的实时状态（current_price, updated_at），但无法回顾历史数据。用户希望：
- 查看今日达标状态变化（哪些新达标、哪些跌破）
- 对比历史趋势
- 获得每日总结报告

系统使用 SQLite 数据库，前端使用 React + Ant Design。

## Goals / Non-Goals

**Goals:**
- 实现股票快照存储，支持每日保存指标状态
- 提供每日报告生成能力，对比昨日和今日的达标变化
- 提供趋势数据 API，支持前端绘制折线图
- 新增独立的前端报告页面

**Non-Goals:**
- 不实现自动定时任务（如每天 15:05 自动保存快照）
- 不实现推送通知（邮件/微信/钉钉）
- 不实现自定义报告周期（目前仅支持日粒度）

## Decisions

### Decision 1: 数据库设计

使用独立的 `stock_snapshots` 表存储快照：

```sql
CREATE TABLE stock_snapshots (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    price REAL,
    ma_results TEXT,  -- JSON: {MA5: {...}, MA20: {...}}
    created_at DATETIME,
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(stock_id, snapshot_date)  -- 每只股票每天只有一份快照
);
```

**理由**：
- 独立表便于查询和扩展
- JSON 存储 ma_results 灵活，支持不同指标组合
- UNIQUE 约束防止重复快照

### Decision 2: 快照生成策略

采用"手动触发 + 自动检查"模式：
- 用户点击"保存今日快照"按钮手动保存
- 应用启动时检查今日是否有快照，无则提示用户

**理由**：
- 避免复杂的定时任务实现
- 用户可控，不会在非交易日生成无效快照

### Decision 3: 图表库选择

使用 **@ant-design/charts**（基于 AntV G2）

**理由**：
- 与现有 Ant Design UI 风格一致
- React 友好，API 简洁
- 体积适中，满足折线图需求

**备选方案**：ECharts（功能更全但体积更大）

### Decision 4: 报告数据结构

```javascript
// GET /reports/daily 响应
{
  "date": "2026-02-16",
  "summary": {
    "total_stocks": 12,
    "reached_count": 8,
    "newly_reached": 2,
    "newly_below": 1,
    "reached_rate": 66.7,
    "reached_rate_change": 5.2
  },
  "changes": {
    "newly_reached": [...],  // 新增达标的股票
    "newly_below": [...]     // 跌破均线的股票
  }
}

// GET /reports/trend 响应
{
  "dates": ["02/10", "02/11", ...],
  "series": [
    { "name": "达标数", "data": [5, 6, 6, 7, 7, 6, 8] },
    { "name": "达标率", "data": [41.6, 50.0, 50.0, 58.3, 58.3, 50.0, 66.7] }
  ]
}
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 数据量随时间增长 | 可添加清理策略，默认保留 90 天数据 |
| 新浪 API 不可用 | 快照生成时优雅失败，不影响现有功能 |
| 前端包体积增加 | 按需加载图表组件 |

## Open Questions

无（探索阶段已解决所有关键问题）
