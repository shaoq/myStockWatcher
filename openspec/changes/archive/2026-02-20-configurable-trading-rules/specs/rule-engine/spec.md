## ADDED Requirements

### Requirement: 规则引擎解析条件配置
系统 SHALL 解析 JSON 格式的条件配置，支持以下操作符：

| 类别 | 操作符 | 说明 |
|------|--------|------|
| 比较 | gt | 大于 |
| 比较 | lt | 小于 |
| 比较 | gte | 大于等于 |
| 比较 | lte | 小于等于 |
| 比较 | eq | 等于 |
| 交叉 | cross_above | 上穿（需前一日和当日数据） |
| 交叉 | cross_below | 下穿（需前一日和当日数据） |
| 阈值 | below_threshold | 低于阈值 |
| 阈值 | above_threshold | 高于阈值 |

#### Scenario: 解析比较条件
- **WHEN** 条件为 `{indicator: "RSI", field: "RSI", operator: "lt", target_type: "value", target_value: 30}`
- **AND** 当前 RSI 值为 25
- **THEN** 条件判断结果为 true

#### Scenario: 解析交叉条件
- **WHEN** 条件为 `{indicator: "MA", field: "MA5", operator: "cross_above", target_type: "indicator", target_indicator: "MA", target_field: "MA20"}`
- **AND** 前一日 MA5=10, MA20=11，当日 MA5=12, MA20=11.5
- **THEN** 条件判断结果为 true

### Requirement: 规则引擎计算价位
系统 SHALL 根据价格配置计算入场价、止损价、止盈价。

#### Scenario: 计算指标型入场价
- **WHEN** 入场价配置为 `{type: "indicator", indicator: "MA", field: "MA20"}`
- **AND** 当前 MA20 = 100
- **THEN** 入场价计算为 100

#### Scenario: 计算百分比止损
- **WHEN** 止损配置为 `{type: "percentage", base: "entry", value: -0.05}`
- **AND** 入场价为 100
- **THEN** 止损价计算为 95

#### Scenario: 计算指标型止盈
- **WHEN** 止盈配置为 `{type: "indicator", indicator: "Bollinger", field: "middle"}`
- **AND** 布林中轨 = 110
- **THEN** 止盈价计算为 110

### Requirement: 规则引擎生成信号
系统 SHALL 根据规则配置生成买卖信号，输出格式与现有 Signal 模型兼容。

#### Scenario: 生成买入信号
- **WHEN** 规则类型为 buy 且所有条件满足
- **THEN** 生成信号包含 signal_type="buy", entry_price, stop_loss, take_profit, strength, triggers

#### Scenario: 生成卖出信号
- **WHEN** 规则类型为 sell 且所有条件满足
- **THEN** 生成信号包含 signal_type="sell", entry_price, take_profit, strength, triggers

#### Scenario: 条件不满足不生成信号
- **WHEN** 规则的任一条件不满足
- **THEN** 不生成该规则对应的信号

### Requirement: 多条件 AND 组合
系统 SHALL 支持多个条件的 AND 组合，所有条件都满足才触发信号。

#### Scenario: 多条件全部满足
- **WHEN** 规则有 2 个条件，都满足
- **THEN** 生成信号

#### Scenario: 多条件部分满足
- **WHEN** 规则有 2 个条件，只有 1 个满足
- **THEN** 不生成信号

### Requirement: 批量信号计算
系统 SHALL 支持为所有股票批量计算信号。

#### Scenario: 批量计算
- **WHEN** 调用批量计算接口
- **THEN** 系统遍历所有股票，使用启用的规则计算信号
- **AND** 更新 Signal 表（覆盖旧信号）

### Requirement: 规则优先级
系统 SHALL 按优先级从高到低评估规则，同一股票同类型信号取优先级最高的。

#### Scenario: 多规则匹配
- **WHEN** 股票 A 同时触发规则1（优先级3）和规则2（优先级2）
- **THEN** 最终信号使用规则1的配置
