## 1. 数据模型

- [x] 1.1 在 `models.py` 中添加 `Signal` 模型
- [x] 1.2 在 `schemas/` 中添加 Signal 相关的 Pydantic 模型

## 2. 技术指标计算服务

- [x] 2.1 创建 `services/indicators.py` 指标计算模块
- [x] 2.2 实现 `calc_ma()` MA 移动平均线计算
- [x] 2.3 实现 `calc_macd()` MACD 指标计算
- [x] 2.4 实现 `calc_rsi()` RSI 指标计算
- [x] 2.5 实现 `calc_kdj()` KDJ 指标计算
- [x] 2.6 实现 `calc_bollinger()` 布林带计算

## 3. 买卖信号服务

- [x] 3.1 创建 `services/signals.py` 信号生成模块
- [x] 3.2 实现买入信号检测（MA 金叉、RSI 超卖、布林下轨）
- [x] 3.3 实现卖出信号检测（MA 死叉、RSI 超买、布林上轨）
- [x] 3.4 实现价位计算（买点、卖点、止损、目标价）
- [x] 3.5 实现综合信号整合逻辑

## 4. API 端点

- [x] 4.1 添加 `GET /stocks/{symbol}/signal` 获取单个股票信号
- [x] 4.2 添加 `POST /signals/generate` 批量生成信号
- [x] 4.3 添加 `GET /signals/` 获取所有信号列表

## 5. 前端展示

- [x] 5.1 在 `StockList.jsx` 中添加信号标签展示
- [x] 5.2 在 `StockChart.jsx` 中添加信号详情卡片
- [x] 5.3 添加 `api.js` 中的信号 API 封装

## 6. 测试验证

- [x] 6.1 测试技术指标计算准确性
- [x] 6.2 测试信号生成逻辑
- [x] 6.3 测试前端信号展示
