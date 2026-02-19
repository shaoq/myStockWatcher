## 1. 依赖更新

- [x] 1.1 在 `requirements.txt` 中添加 `exchange_calendars>=4.2.0`
- [x] 1.2 安装新依赖

## 2. 日期格式解析修复

- [x] 2.1 创建 `parse_date_flexible` 函数，支持多种日期格式
- [x] 2.2 修改 `fetch_trading_calendar_from_akshare` 使用新的解析函数

## 3. 多层数据源实现

- [x] 3.1 实现 `fetch_trading_calendar_from_exchange_calendars` 备用数据源函数
- [x] 3.2 修改 `is_trading_day` 函数，添加多层数据源 fallback 逻辑
- [x] 3.3 添加基础规则兜底（周末判断）

## 4. 测试验证

- [x] 4.1 测试日期格式解析：`2026-01-05` 格式 ✓ 通过
- [x] 4.2 测试日期格式解析：`20260105` 格式 ✓ 通过
- [x] 4.3 测试多层数据源 fallback ✓ AkShare + exchange_calendars 都工作
- [x] 4.4 测试交易日在各种异常情况下的稳定性 ✓ 通过
