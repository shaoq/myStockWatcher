## 1. 前端 API 封装

- [x] 1.1 在 `frontend/src/services/api.js` 中添加 `getValuation(symbol, useCache)` 方法
- [x] 1.2 测试 API 调用返回正确的估值数据结构

## 2. StockChart 组件 - 核心估值卡片

- [x] 2.1 添加估值数据状态（valuation, valuationLoading, valuationError）
- [x] 2.2 在 useEffect 中并行加载估值数据
- [x] 2.3 实现顶部核心估值卡片 UI（5个指标：PE/PB/ROE/净利润率/营收增长率）
- [x] 2.4 实现加载中状态（Skeleton）
- [x] 2.5 实现错误状态（显示"估值数据获取失败"提示）

## 3. StockChart 组件 - 估值详情 Tab

- [x] 3.1 添加"估值详情"Tab 到 Tabs 组件
- [x] 3.2 实现估值详情分组展示（估值/盈利/成长/财务/每股）
- [x] 3.3 实现估值详情错误状态（显示"暂无数据"）

## 4. 样式与交互优化

- [x] 4.1 调整 Modal 宽度以适应新增内容
- [x] 4.2 优化估值卡片响应式布局
- [x] 4.3 添加数据来源和更新时间显示

## 5. 测试与验证

- [x] 5.1 测试 A 股估值数据正常展示
- [x] 5.2 测试美股估值数据失败时的友好提示
- [x] 5.3 测试趋势图和估值数据并行加载
