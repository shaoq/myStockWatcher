## ADDED Requirements

### Requirement: MA 移动平均线计算

系统 SHALL 支持计算任意周期的移动平均线（MA）。

#### Scenario: 计算 MA5/MA10/MA20
- **WHEN** 传入 K 线数据（至少 20 条）
- **THEN** 系统返回 MA5、MA10、MA20 数值
- **AND** 返回最近一条数据的 MA 值

### Requirement: MACD 指标计算

系统 SHALL 支持 MACD 指标计算（DIF、DEA、MACD 柱）。

#### Scenario: 计算 MACD
- **WHEN** 传入 K 线数据（至少 34 条）
- **THEN** 系统返回 DIF、DEA、MACD 柱状图数值
- **AND** 返回金叉/死叉信号

### Requirement: RSI 指标计算

系统 SHALL 支持 RSI 相对强弱指标计算。

#### Scenario: 计算 RSI
- **WHEN** 传入 K 线数据（至少 14 条）
- **THEN** 系统返回 RSI 数值（0-100）
- **AND** 返回超买/超卖状态（>70 超买，<30 超卖）

### Requirement: KDJ 指标计算

系统 SHALL 支持 KDJ 随机指标计算。

#### Scenario: 计算 KDJ
- **WHEN** 传入 K 线数据（至少 9 条）
- **THEN** 系统返回 K、D、J 数值
- **AND** 返回金叉/死叉信号

### Requirement: 布林带计算

系统 SHALL 支持布林带指标计算（上轨、中轨、下轨）。

#### Scenario: 计算布林带
- **WHEN** 传入 K 线数据（至少 20 条）
- **THEN** 系统返回上轨、中轨、下轨数值
- **AND** 返回突破上轨/跌破下轨信号
