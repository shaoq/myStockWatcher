## Context

每日报告页面当前使用两套不同的展示逻辑：
- **未达标个股**：按 MA 分组，组内区分"新跌破"和"持续未达标"
- **达标个股**：使用简单的列表展示"新增达标"，且与下方的表格重复

这种不一致性导致用户需要在不同区域使用不同的认知模式，增加了理解成本。

### 当前数据流
```
后端 services.py
├── get_daily_report()
│   ├── 计算 reached_stocks（聚合所有达标股票）
│   ├── 计算 newly_reached（仅新增达标的指标）
│   └── 返回 report
│
前端 DailyReport.jsx
├── 概览卡片：显示 newly_reached 数量
├── 新增达标卡片：显示 newly_reached 列表
└── 今日达标个股表格：显示 reached_stocks 表格
```

## Goals / Non-Goals

**Goals:**
- 统一达标/未达标股票的展示模式，提供一致的用户体验
- 为每个达标指标提供状态分类，帮助用户识别趋势变化
- 移除重复的 UI 组件，简化页面结构
- 保持 API 向后兼容，避免破坏现有功能

**Non-Goals:**
- 不改变达标/未达标的判断逻辑（MA 计算规则保持不变）
- 不改变数据库 schema（不新增表或字段）
- 不修改其他页面（如股票列表页）

## Decisions

### 1. 数据结构设计：在现有 API 响应中添加字段

**决策**：在 `reached_indicators` 数组中添加 `reach_type` 字段，而不是创建新的 API 端点。

**理由**：
- 现有 `reached_stocks` 已经包含所有达标股票的聚合数据
- 添加字段比创建新端点更轻量，对前端改动最小
- 保持单一数据源，避免数据不一致

**替代方案**：
- ❌ 创建新的 `/reports/reached-status` 端点：增加维护成本，数据可能不同步
- ❌ 在前端计算 reach_type：需要前端持有昨日数据，增加状态管理复杂度

**数据结构示例**：
```json
{
  "stock_id": 1,
  "symbol": "600000",
  "name": "浦发银行",
  "current_price": 10.50,
  "max_deviation_percent": 2.5,
  "reached_indicators": [
    {
      "ma_type": "MA5",
      "ma_price": 10.20,
      "price_difference_percent": 2.5,
      "reach_type": "new_reach"
    },
    {
      "ma_type": "MA20",
      "ma_price": 10.10,
      "price_difference_percent": 3.96,
      "reach_type": "continuous_reach"
    }
  ]
}
```

### 2. 前端展示逻辑：复用未达标股票的分组渲染模式

**决策**：创建 `renderReachedStocksWithReachType` 函数，复用 `renderBelowStocksWithFallType` 的设计模式。

**理由**：
- 保持代码风格一致，降低维护成本
- 提供统一的用户体验，用户无需学习新的交互模式
- 已有的辅助函数（`groupByMA`, `getSortedGroupKeys`）可以直接复用

**实现策略**：
1. **展平数据**：`flattenReachedStocks()` - 将聚合的 `reached_stocks` 转换为扁平数组
2. **按 MA 分组**：复用 `groupByMA()` - 按指标类型分组
3. **按状态分类**：`groupByReachType()` - 区分 new_reach 和 continuous_reach
4. **渲染列表**：`renderReachedItem()` - 渲染单个达标股票项

### 3. UI 简化：移除冗余组件

**决策**：移除"今日达标个股"表格和概览卡片中的"新增达标"统计。

**理由**：
- 表格与"达标个股"卡片展示相同信息，属于冗余
- 概览卡片中的"新增达标"只是数字，无法提供详细信息
- 用户可以在"达标个股"卡片中查看详细的新增达标列表

**风险评估**：
- ⚠️ 用户可能习惯了表格的快速浏览方式
- ✅ 缓解：新的卡片视图支持折叠/展开，可以快速浏览所有 MA 分组

### 4. 颜色方案：使用不同深浅的绿色区分状态

**决策**：
- 新增达标：🟢 使用 `success` 颜色（亮绿色 #52c41a）
- 持续达标：🟢 使用 `#b7eb8f`（淡绿色）

**理由**：
- 保持绿色系，符合"达标"的语义（正向信号）
- 亮绿色更吸引注意力，适合"新增达标"（状态变化）
- 淡绿色表示稳定，适合"持续达标"

**替代方案**：
- ❌ 使用不同颜色（如绿色 vs 蓝色）：可能引起语义混淆

## Risks / Trade-offs

### Risk 1: 无昨日数据时的默认行为

**风险**：如果用户首次使用系统，或历史快照数据缺失，所有达标股票都会被标记为 `"new_reach"`。

**缓解**：
- 这符合直觉：第一次看到的数据都是"新"的
- 前端可以显示提示："首次生成报告，所有达标股票标记为新增"

### Risk 2: 前端兼容性

**风险**：旧版前端可能无法正确显示 `reach_type` 字段。

**缓解**：
- 前端代码中添加默认值：`reach_type = indicator.reach_type || "new_reach"`
- 这确保即使后端未返回字段，前端也能正常工作

### Risk 3: 用户习惯改变

**风险**：用户习惯了"今日达标个股"表格的快速浏览方式。

**缓解**：
- 新的卡片视图支持 Collapse，默认展开所有 MA 分组
- 用户可以快速浏览所有达标股票
- 如果反馈强烈，可以在未来版本中添加"切换视图"选项

## Migration Plan

### 阶段 1：后端更新（向后兼容）
1. 修改 `services.py` 中的 `get_daily_report` 函数
2. 在计算 `reached_indicators` 时添加 `reach_type` 字段
3. 测试 API 响应格式

### 阶段 2：前端更新
1. 修改 `DailyReport.jsx`：
   - 添加辅助函数（`flattenReachedStocks`, `groupByReachType`, `renderReachedItem`）
   - 修改"新增达标"卡片为"达标个股"，使用新的渲染函数
   - 移除"今日达标个股"表格
   - 移除概览卡片中的"新增达标"统计
2. 测试前端展示

### 阶段 3：清理与优化
1. 移除前端中未使用的代码（如 `renderMACollapsePanel` 中针对 "reached" 类型的逻辑）
2. 更新相关注释和文档

### 回滚策略
- 如果出现问题，可以快速回滚前端代码（恢复表格和概览卡片）
- 后端的 `reach_type` 字段是新增的，不影响现有功能
- 无数据库迁移，无需数据回滚

## Open Questions

1. **是否需要在概览卡片中显示"持续达标"数量？**
   - 当前方案：只显示"今日达标"总数，不细分
   - 可选方案：显示"新增达标 X + 持续达标 Y"
   - 决策：保持简洁，只显示总数，用户可以在详情卡片中查看分类

2. **是否需要为"持续达标"添加更详细的状态（如"连续3日达标"）？**
   - 当前方案：只区分"新增"和"持续"
   - 未来扩展：可以添加 `continuous_days` 字段
   - 决策：当前不实现，作为未来优化项
