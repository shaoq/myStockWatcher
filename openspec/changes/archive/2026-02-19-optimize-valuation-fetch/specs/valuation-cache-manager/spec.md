## ADDED Requirements

### Requirement: 全量数据共享缓存

系统 SHALL 提供全量 A 股实时数据的共享缓存，供 EastMoney 和 AKShare Provider 共同使用。

#### Scenario: 首次获取数据时创建缓存
- **WHEN** 任意 Provider 请求全量数据且缓存不存在
- **THEN** 系统下载全量数据并存入缓存
- **AND** 记录获取时间

#### Scenario: 缓存存在时直接使用
- **WHEN** 任意 Provider 请求全量数据且缓存有效
- **THEN** 系统直接返回缓存数据
- **AND** 不重新下载

### Requirement: 智能缓存时效控制

系统 SHALL 根据交易时间智能判断缓存是否有效。

#### Scenario: 交易时间内缓存 5 分钟有效
- **WHEN** 当前处于交易时间（工作日 9:30-15:00）
- **AND** 缓存时间在 5 分钟内
- **THEN** 缓存有效，使用缓存数据

#### Scenario: 交易时间内缓存超时
- **WHEN** 当前处于交易时间
- **AND** 缓存时间超过 5 分钟
- **THEN** 缓存无效，重新下载数据

#### Scenario: 非交易时间缓存到次日开盘
- **WHEN** 当前处于非交易时间（收盘后、周末、节假日）
- **AND** 缓存是当日收盘后获取的
- **THEN** 缓存有效，使用缓存数据

### Requirement: 缓存数据结构

缓存 SHALL 包含以下信息：
- `data`: 全量股票 DataFrame
- `fetched_at`: 数据获取时间
- `source`: 数据来源（eastmoney）

#### Scenario: 缓存结构验证
- **WHEN** 缓存被创建或更新
- **THEN** 缓存包含有效的 DataFrame
- **AND** fetched_at 记录当前时间
- **AND** source 记录数据来源

### Requirement: 从缓存提取单股估值

系统 SHALL 从缓存的全量数据中提取指定股票的估值指标。

#### Scenario: 提取估值指标
- **WHEN** 请求指定股票的估值数据
- **THEN** 从缓存 DataFrame 中筛选目标股票
- **AND** 提取 PE、PB、市值等估值指标
- **AND** 返回格式化的估值数据

#### Scenario: 股票不在缓存中
- **WHEN** 请求的股票代码在缓存中不存在
- **THEN** 返回 None 或空数据
- **AND** 记录警告日志
