## ADDED Requirements

### Requirement: 买入信号生成

系统 SHALL 基于技术指标生成买入信号，包含具体价位建议。

#### Scenario: MA 金叉买入信号
- **WHEN** MA5 上穿 MA20（前一日 MA5 < MA20，当日 MA5 > MA20）
- **THEN** 生成买入信号
- **AND** 建议买点价位 = MA20 价格
- **AND** 止损价位 = MA20 * 0.95
- **AND** 目标价位 = MA20 * 1.08
- **AND** 信号强度 = 3

#### Scenario: RSI 超卖买入信号
- **WHEN** RSI < 30
- **THEN** 生成买入信号
- **AND** 建议买点价位 = 当前价 * 0.98
- **AND** 信号强度 = 2

#### Scenario: 布林带下轨买入信号
- **WHEN** 价格跌破布林带下轨
- **THEN** 生成买入信号
- **AND** 建议买点价位 = 布林下轨
- **AND** 信号强度 = 3

### Requirement: 卖出信号生成

系统 SHALL 基于技术指标生成卖出信号，包含具体价位建议。

#### Scenario: MA 死叉卖出信号
- **WHEN** MA5 下穿 MA20（前一日 MA5 > MA20，当日 MA5 < MA20）
- **THEN** 生成卖出信号
- **AND** 建议卖点价位 = MA20 价格
- **AND** 信号强度 = 3

#### Scenario: RSI 超买卖出信号
- **WHEN** RSI > 70
- **THEN** 生成卖出信号
- **AND** 建议卖点价位 = 当前价 * 1.02
- **AND** 信号强度 = 2

### Requirement: 综合信号整合

系统 SHALL 整合多个指标的信号，输出综合建议。

#### Scenario: 多信号整合
- **WHEN** 多个指标同时触发买入/卖出信号
- **THEN** 综合信号强度 = 各信号强度之和（上限 5）
- **AND** 汇总所有触发条件
- **AND** 取最优价位作为建议

### Requirement: 信号持久化

系统 SHALL 将生成的信号存储到数据库。

#### Scenario: 保存信号
- **WHEN** 生成新的买卖信号
- **THEN** 信号保存到 signals 表
- **AND** 记录股票ID、日期、信号类型、价位、强度、触发条件
