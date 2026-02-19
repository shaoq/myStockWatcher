## 1. 缓存管理器实现

- [x] 1.1 创建 `backend/app/providers/spot_cache.py` 缓存管理模块
- [x] 1.2 实现全局缓存数据结构（data, fetched_at, source）
- [x] 1.3 实现 `is_trading_time()` 交易时间判断函数
- [x] 1.4 实现 `is_cache_valid()` 缓存时效判断函数
- [x] 1.5 实现 `get_spot_data()` 获取全量数据（带缓存）

## 2. EastMoney Provider 集成

- [x] 2.1 在 `EastMoneyProvider` 中添加 `valuation_metrics` 能力声明
- [x] 2.2 实现 `get_valuation_metrics()` 方法，使用缓存管理器
- [x] 2.3 复用现有的 `stock_zh_a_spot_em()` 逻辑

## 3. AKShare Provider 优化

- [x] 3.1 修改 `AKShareProvider.get_valuation_metrics()` 使用缓存管理器
- [x] 3.2 移除原有的全量下载逻辑，改为调用缓存

## 4. Coordinator 调整

- [x] 4.1 更新 `DataSourceCoordinator.get_valuation_metrics()` 调用顺序
- [x] 4.2 EastMoney 优先，AKShare 作为备用

## 5. 测试验证

- [x] 5.1 测试首次请求触发缓存创建
- [x] 5.2 测试缓存有效时不重新下载
- [x] 5.3 测试交易时间和非交易时间缓存时效
