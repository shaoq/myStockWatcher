## 1. DatePicker 组件修改

- [x] 1.1 创建 `renderDateCell` 函数，自定义日期单元格渲染
- [x] 1.2 在 DatePicker 组件上添加 `cellRender` 属性
- [x] 1.3 添加绿色小圆点样式（position: absolute, top-right）

## 2. 交易日判断（新增）

- [x] 2.1 后端新增 `/trading-calendar/monthly` API 获取指定月份交易日列表
- [x] 2.2 后端新增 `get_trading_days_in_range` CRUD 函数
- [x] 2.3 前端新增 `getMonthlyTradingDays` API 调用
- [x] 2.4 前端新增 `tradingDays` 状态和 `loadTradingDays` 函数
- [x] 2.5 在 `renderDateCell` 中使用交易日数据过滤非交易日
- [x] 2.6 添加 `onPanelChange` 处理月份切换时加载交易日数据

## 3. 测试验证

- [x] 3.1 验证有报告的交易日显示绿色小圆点 ✓ (6号, 10-13号显示角标)
- [x] 3.2 验证非交易日不显示角标 ✓ (16-19号无角标)
- [x] 3.3 验证周末不显示角标 ✓ (1,8,15,22,28号无角标)
- [x] 3.4 验证切换月份时正确加载交易日数据 ✓
