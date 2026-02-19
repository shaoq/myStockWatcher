## 1. 后端 - 交易日历服务

- [x] 1.1 添加 akshare 依赖到 requirements.txt
- [x] 1.2 创建 TradingCalendar 数据库模型 (models.py)
- [x] 1.3 实现交易日历 CRUD 操作 (crud.py)
- [x] 1.4 实现交易日历服务层 (services.py)
  - 从 AkShare 获取交易日历
  - 缓存管理逻辑
  - 交易日判断接口
- [x] 1.5 添加交易日历 API 端点 (main.py)
  - GET /trading-calendar/check
  - POST /trading-calendar/refresh

## 2. 后端 - 历史快照生成

- [x] 2.1 实现历史 K 线数据获取函数 (services.py)
- [x] 2.2 修改 generate_daily_snapshots 支持 date 参数
- [x] 2.3 添加历史数据来源标记 (data_source: kline_close)
- [x] 2.4 添加非交易日校验逻辑

## 3. 后端 - 报告生成优化

- [x] 3.1 修改 get_daily_report 添加交易日校验
- [x] 3.2 非交易日返回明确错误信息
- [x] 3.3 智能判断是否需要生成快照

## 4. 前端 - 交易日历集成

- [x] 4.1 添加交易日历 API 调用 (api.js)
- [x] 4.2 日期选择器集成交易日状态显示
- [x] 4.3 非交易日显示"休市"提示

## 5. 前端 - 历史报告生成

- [x] 5.1 添加历史报告生成按钮
- [x] 5.2 实现历史日期选择和确认流程
- [x] 5.3 显示数据来源标识（实时/历史K线）

## 6. 测试与验证

- [x] 6.1 测试交易日历 API
- [x] 6.2 测试历史快照生成
- [x] 6.3 测试非交易日报告请求
- [x] 6.4 端到端测试完整流程
