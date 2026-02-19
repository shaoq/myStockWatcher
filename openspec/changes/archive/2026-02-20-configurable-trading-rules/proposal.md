## Why

当前买卖信号规则硬编码在 `signals.py` 中，用户无法根据自己的交易策略调整规则参数或添加新规则。用户需要能够：

1. 自定义买卖点计算规则（条件、价位、强度等）
2. 通过前端 UI 配置规则，无需修改代码
3. 配置生效后重新计算所有股票的买卖信号

## What Changes

- **规则配置存储**：新增 `TradingRule` 数据库模型，存储用户自定义的买卖规则
- **规则引擎**：新增规则解析和执行引擎，替代硬编码的信号生成逻辑
- **前端配置界面**：新增规则管理页面，支持表单式配置
- **批量重算**：支持配置变更后重新计算所有股票信号

## Capabilities

### New Capabilities

- `trading-rule-config`: 交易规则配置管理，支持 CRUD 操作、规则分组（买入/卖出）、表单式配置
- `rule-engine`: 规则引擎服务，解析 JSON 格式规则配置，执行条件判断，计算价位

### Modified Capabilities

- `trading-signals`: 信号生成逻辑从硬编码改为调用规则引擎，信号数据结构保持不变

## Impact

- **后端代码**:
  - `backend/app/models.py` - 新增 `TradingRule` 模型
  - `backend/app/schemas/` - 新增规则相关 Schema
  - `backend/app/services/rule_engine.py` - 新增规则引擎
  - `backend/app/services/signals.py` - 重构为调用规则引擎
  - `backend/app/main.py` - 新增规则 CRUD API + 批量重算 API
- **前端代码**:
  - `frontend/src/components/TradingRules.jsx` - 新增规则配置页面
  - `frontend/src/components/RuleEditor.jsx` - 规则编辑表单组件
  - `frontend/src/services/api.js` - 新增规则 API 调用
  - `frontend/src/App.jsx` - 添加路由入口
- **数据库**:
  - 新增 `trading_rules` 表
  - 初始化 8 条默认规则（4 买 4 卖）
