## MODIFIED Requirements

### Requirement: 信号生成使用规则引擎
系统 SHALL 使用可配置的规则引擎生成买卖信号，而非硬编码逻辑。

#### Scenario: 调用规则引擎生成信号
- **WHEN** 需要为股票生成信号
- **THEN** 系统加载所有启用的交易规则
- **AND** 依次评估每条规则的条件
- **AND** 返回匹配的信号列表

#### Scenario: 无匹配规则时返回 hold
- **WHEN** 没有任何规则的条件被满足
- **THEN** 系统返回 signal_type="hold" 的默认信号

### Requirement: 信号数据结构保持不变
系统 SHALL 保持现有 Signal 模型结构不变，确保向后兼容。

#### Scenario: 信号字段完整性
- **WHEN** 生成新信号
- **THEN** 信号包含以下字段：stock_id, signal_date, signal_type, current_price, entry_price, stop_loss, take_profit, strength, triggers, indicators
