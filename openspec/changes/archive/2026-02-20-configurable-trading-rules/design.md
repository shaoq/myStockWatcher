## Context

当前买卖信号规则硬编码在 `signals.py` 中，包括：
- 触发条件（如 MA5 上穿 MA20、RSI < 30）
- 价位计算（如止损 -5%、止盈 +8%）
- 信号强度（1-5 级）

用户需要通过前端 UI 自定义这些规则，无需修改代码。

**约束条件**：
- 规则存储在数据库中，支持动态生效
- 前端采用表单式配置，不需要可视化构建器
- 配置变更后可选择重新计算所有股票信号

## Goals / Non-Goals

**Goals:**
- 规则完全可配置：条件、价位、强度、优先级
- 前端表单式配置界面
- 规则按买入/卖出分类管理
- 支持启用/禁用单条规则
- 配置保存后弹窗询问是否重算
- 额外提供手动触发批量重算按钮
- 系统初始化时自动创建 8 条默认规则

**Non-Goals:**
- 不支持复杂的 AND/OR 条件组合（V1 版本只支持多条件 AND）
- 不支持规则版本历史
- 不支持规则导入/导出

## Decisions

### 1. 规则配置数据结构

**选择 JSON 存储规则条件**：
- 灵活，支持复杂嵌套结构
- SQLite 的 Text 字段直接存储
- 前端 JSON 序列化/反序列化简单

```python
# conditions JSON 结构
{
    "conditions": [
        {
            "indicator": "MA",           # 指标类型
            "field": "MA5",              # 字段名
            "operator": "cross_above",   # 操作符
            "target_type": "indicator",  # 目标类型
            "target_indicator": "MA",
            "target_field": "MA20"
        }
    ]
}

# price_config JSON 结构
{
    "entry": {
        "type": "indicator",   # indicator / percentage / current
        "indicator": "MA",
        "field": "MA20"
    },
    "stop_loss": {
        "type": "percentage",
        "base": "entry",       # entry / current
        "value": -0.05
    },
    "take_profit": {
        "type": "percentage",
        "base": "entry",
        "value": 0.08
    }
}
```

### 2. 规则引擎架构

**选择解释器模式**：
- 规则引擎解析 JSON 配置
- 运行时执行条件判断
- 易于扩展新操作符

```
┌─────────────────────────────────────────────────────────────────┐
│                        RuleEngine                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  evaluate(rule, indicators, price_history) → Signal             │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ ConditionParser │  │ PriceCalculator │  │ SignalBuilder   │ │
│  │ (条件解析)       │  │ (价位计算)       │  │ (信号构建)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3. 支持的操作符

| 类别 | 操作符 | 说明 |
|------|--------|------|
| 比较 | gt, lt, gte, lte, eq | 大于、小于、等于等 |
| 交叉 | cross_above, cross_below | 上穿、下穿（需历史数据） |
| 阈值 | below_threshold, above_threshold | RSI 超买超卖等 |

### 4. 批量重算策略

**选择同步执行**：
- 规则变更后立即生效
- 前端显示重算进度
- 股票数量不多（预计 < 100），同步执行可接受

### 5. 默认规则初始化

**选择启动时自动检测**：
- 应用启动时检查 `trading_rules` 表是否为空
- 空则插入 8 条默认规则
- 使用 migration 脚本确保数据一致性

## Risks / Trade-offs

- **规则配置复杂** → 提供表单式 UI，隐藏 JSON 细节
- **批量重算耗时** → 显示进度条，支持取消
- **规则语法错误** → 保存前验证 JSON 格式和必填字段
- **向后兼容** → 保留现有 Signal 模型结构不变

## Migration Plan

1. 创建 `TradingRule` 表
2. 插入 8 条默认规则
3. 部署规则引擎和 API
4. 部署前端配置页面
5. 验证信号生成逻辑正常
6. 可选：删除旧硬编码逻辑
