## ADDED Requirements

### Requirement: 用户可以查看规则列表
系统 SHALL 展示所有交易规则，按买入/卖出分组显示。

#### Scenario: 查看买入规则列表
- **WHEN** 用户进入规则配置页面
- **THEN** 系统显示所有 rule_type="buy" 的规则，按优先级降序排列

#### Scenario: 查看卖出规则列表
- **WHEN** 用户进入规则配置页面
- **THEN** 系统显示所有 rule_type="sell" 的规则，按优先级降序排列

### Requirement: 用户可以创建新规则
系统 SHALL 允许用户通过表单创建新的交易规则。

#### Scenario: 创建买入规则
- **WHEN** 用户填写规则名称、条件、价位配置、强度后点击保存
- **THEN** 系统创建新规则并显示保存成功提示
- **AND** 弹窗询问是否立即重新计算信号

#### Scenario: 规则名称必填
- **WHEN** 用户未填写规则名称就尝试保存
- **THEN** 系统显示错误提示"规则名称不能为空"

### Requirement: 用户可以编辑现有规则
系统 SHALL 允许用户修改已有规则的所有配置项。

#### Scenario: 编辑规则
- **WHEN** 用户点击规则列表中的"编辑"按钮
- **THEN** 系统显示规则编辑表单，预填充当前配置
- **AND** 保存后弹窗询问是否重新计算信号

### Requirement: 用户可以删除规则
系统 SHALL 允许用户删除不再需要的规则。

#### Scenario: 删除规则
- **WHEN** 用户点击规则列表中的"删除"按钮并确认
- **THEN** 系统删除该规则
- **AND** 弹窗询问是否重新计算信号

### Requirement: 用户可以启用/禁用规则
系统 SHALL 允许用户启用或禁用单条规则，禁用的规则不参与信号计算。

#### Scenario: 禁用规则
- **WHEN** 用户取消勾选规则的启用状态
- **THEN** 系统将该规则标记为 disabled
- **AND** 该规则不参与后续信号计算

### Requirement: 用户可以触发批量重算
系统 SHALL 提供手动触发批量重新计算所有股票信号的功能。

#### Scenario: 手动触发批量重算
- **WHEN** 用户点击"批量重算信号"按钮
- **THEN** 系统使用当前启用的规则重新计算所有股票的信号
- **AND** 显示重算进度

#### Scenario: 保存后选择立即重算
- **WHEN** 用户保存规则后点击弹窗中的"立即计算"
- **THEN** 系统触发批量重算

### Requirement: 规则配置包含完整字段
每条规则 SHALL 包含以下可配置字段：
- name: 规则名称
- rule_type: 规则类型（buy/sell）
- enabled: 是否启用
- priority: 优先级（整数，越大越优先）
- strength: 信号强度（1-5）
- conditions: 触发条件列表（JSON）
- price_config: 价位配置（JSON）
- description_template: 描述模板

#### Scenario: 表单展示所有配置项
- **WHEN** 用户打开规则编辑表单
- **THEN** 系统显示上述所有字段的输入控件

### Requirement: 触发条件表单式配置
系统 SHALL 提供表单式界面配置触发条件，支持：
- 指标类型选择（MA/MACD/RSI/KDJ/Bollinger）
- 字段选择（根据指标类型动态更新）
- 操作符选择（gt/lt/cross_above/cross_below 等）
- 目标值配置

#### Scenario: 配置 MA 交叉条件
- **WHEN** 用户选择指标"MA"、字段"MA5"、操作符"上穿"、目标"MA20"
- **THEN** 系统生成条件 `{indicator: "MA", field: "MA5", operator: "cross_above", target_type: "indicator", target_indicator: "MA", target_field: "MA20"}`

### Requirement: 价位配置表单式配置
系统 SHALL 提供表单式界面配置价位计算：
- 入场价：指标值/当前价
- 止损价：百分比/指标值
- 止盈价：百分比/指标值

#### Scenario: 配置百分比止损
- **WHEN** 用户选择止损类型"百分比"、基于"入场价"、值"-5%"
- **THEN** 系统生成配置 `{type: "percentage", base: "entry", value: -0.05}`

### Requirement: 系统初始化默认规则
系统 SHALL 在首次启动时自动创建 8 条默认规则（4 买 4 卖）。

#### Scenario: 空数据库初始化
- **WHEN** trading_rules 表为空
- **THEN** 系统自动插入 8 条默认规则

#### Scenario: 已有数据不重复初始化
- **WHEN** trading_rules 表已有数据
- **THEN** 系统不重复插入默认规则
