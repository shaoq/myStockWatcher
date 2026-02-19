## 1. 数据库模型

- [x] 1.1 在 models.py 中新增 TradingRule 模型（id, name, rule_type, enabled, priority, strength, conditions, price_config, description_template, created_at, updated_at）
- [x] 1.2 创建数据库迁移脚本，添加 trading_rules 表

## 2. 后端 Schema

- [x] 2.1 在 schemas/ 目录新增 TradingRuleCreate Schema（用于创建规则）
- [x] 2.2 新增 TradingRuleUpdate Schema（用于更新规则）
- [x] 2.3 新增 TradingRuleResponse Schema（用于返回规则详情）
- [x] 2.4 新增条件配置的 Schema（ConditionConfig, PriceConfig）

## 3. 规则引擎服务

- [x] 3.1 创建 services/rule_engine.py 文件
- [x] 3.2 实现 ConditionParser 类 - 解析条件 JSON
- [x] 3.3 实现操作符评估函数（gt, lt, gte, lte, eq, cross_above, cross_below, below_threshold, above_threshold）
- [x] 3.4 实现 PriceCalculator 类 - 计算入场价、止损价、止盈价
- [x] 3.5 实现 RuleEngine.evaluate() 方法 - 评估单条规则
- [x] 3.6 实现 RuleEngine.evaluate_all() 方法 - 评估所有规则并返回信号

## 4. 重构信号服务

- [x] 4.1 修改 services/signals.py，移除硬编码的信号检测逻辑
- [x] 4.2 改为调用 RuleEngine 生成信号
- [x] 4.3 保持 generate_signal() 函数签名不变，确保向后兼容

## 5. 后端 API

- [x] 5.1 新增 GET /rules/ 接口 - 获取所有规则（支持按 rule_type 过滤）
- [x] 5.2 新增 POST /rules/ 接口 - 创建新规则
- [x] 5.3 新增 PUT /rules/{id} 接口 - 更新规则
- [x] 5.4 新增 DELETE /rules/{id} 接口 - 删除规则
- [x] 5.5 新增 POST /rules/recalculate 接口 - 批量重新计算所有股票信号

## 6. 默认规则初始化

- [x] 6.1 创建默认规则数据（8 条：4 买 4 卖）
- [x] 6.2 在 main.py startup 事件中检查并初始化默认规则

## 7. 前端 API 服务

- [x] 7.1 在 services/api.js 中新增 getRules() 函数
- [x] 7.2 新增 createRule() 函数
- [x] 7.3 新增 updateRule() 函数
- [x] 7.4 新增 deleteRule() 函数
- [x] 7.5 新增 recalculateSignals() 函数

## 8. 前端规则配置页面

- [x] 8.1 创建 components/TradingRules.jsx - 规则列表页面
- [x] 8.2 实现买入/卖出分组展示
- [x] 8.3 实现启用/禁用切换
- [x] 8.4 实现编辑/删除操作
- [x] 8.5 添加批量重算按钮

## 9. 前端规则编辑表单

- [x] 9.1 创建 components/RuleEditor.jsx - 规则编辑表单组件
- [x] 9.2 实现基本信息表单项（名称、类型、优先级、强度）
- [x] 9.3 实现触发条件配置表单（指标、字段、操作符、目标值选择器）
- [x] 9.4 实现价位配置表单（入场价、止损价、止盈价）
- [x] 9.5 实现描述模板输入
- [x] 9.6 添加表单验证逻辑

## 10. 前端交互优化

- [x] 10.1 保存规则后弹窗询问是否重算
- [x] 10.2 批量重算时显示进度提示
- [x] 10.3 在 App.jsx 中添加路由入口

## 11. 测试与验证

- [x] 11.1 验证默认规则初始化正常
- [x] 11.2 验证规则 CRUD 操作正常
- [x] 11.3 验证规则引擎条件评估正确
- [x] 11.4 验证信号生成结果与旧逻辑一致
- [x] 11.5 验证批量重算功能正常
