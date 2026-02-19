## ADDED Requirements

### Requirement: 顶部核心估值卡片展示

系统 SHALL 在趋势图对话框顶部展示5个核心估值指标：PE（市盈率）、PB（市净率）、ROE（净资产收益率）、净利润率、营收增长率。

#### Scenario: 成功加载估值数据
- **WHEN** 用户打开趋势图对话框
- **THEN** 系统并行加载估值数据
- **AND** 顶部卡片显示5个核心指标数值
- **AND** 显示数据来源和更新时间

#### Scenario: 估值数据获取失败
- **WHEN** 估值数据获取失败（如美股暂不支持）
- **THEN** 顶部卡片显示"估值数据获取失败"提示
- **AND** 显示失败原因（如"美股暂不支持 AKShare 估值数据"）

#### Scenario: 估值数据加载中
- **WHEN** 估值数据正在加载
- **THEN** 顶部卡片显示加载状态（Skeleton 或 Spin）

### Requirement: 估值详情Tab展示

系统 SHALL 提供"估值详情"Tab，按分组展示完整估值数据。

#### Scenario: 查看估值详情
- **WHEN** 用户点击"估值详情"Tab
- **THEN** 系统展示分组估值数据：
  - 估值指标：PE、PB、PS、股息率
  - 盈利能力：ROE、ROA、净利润率、毛利率
  - 成长能力：营收增长率
  - 财务健康：负债权益比、流动比率
  - 每股指标：EPS、每股净资产

#### Scenario: 估值详情数据不可用
- **WHEN** 估值数据获取失败
- **THEN** 估值详情Tab显示"暂无数据"提示

### Requirement: 前端估值API封装

前端 SHALL 封装 `/stocks/{symbol}/valuation` API 调用。

#### Scenario: 调用估值API
- **WHEN** StockChart组件需要获取估值数据
- **THEN** 调用 `stockApi.getValuation(symbol)` 方法
- **AND** 支持 `use_cache` 参数（默认 true）

#### Scenario: API错误处理
- **WHEN** 估值API返回错误
- **THEN** 不抛出异常，返回错误信息对象
- **AND** 组件根据错误信息显示友好提示
