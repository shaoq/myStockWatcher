## 1. 后端实现

- [x] 1.1 修改 `backend/app/services.py` 中的 `get_daily_report` 函数，为 `reached_indicators` 添加 `reach_type` 字段
- [x] 1.2 测试后端 API 响应，确认 `reach_type` 字段正确返回（"new_reach" 或 "continuous_reach"）

## 2. 前端辅助函数

- [x] 2.1 在 `frontend/src/components/DailyReport.jsx` 中添加 `flattenReachedStocks` 函数
- [x] 2.2 添加 `groupByReachType` 函数，按 reach_type 分类
- [x] 2.3 添加 `renderReachedItem` 函数，渲染单个达标股票项

## 3. 前端组件修改

- [x] 3.1 添加 `renderReachedStocksWithReachType` 函数，按 MA 分组展示达标个股
- [x] 3.2 修改"新增达标"卡片为"达标个股"，使用新的渲染函数
- [x] 3.3 确保达标个股按 MA 数字升序排列，组内按 reach_type 分类，最后按偏离度降序

## 4. 移除冗余组件

- [x] 4.1 移除"今日达标个股"表格组件（第984-1075行）
- [x] 4.2 移除概览卡片中的"新增达标"统计卡片（第878-886行）
- [x] 4.3 清理相关的状态变量和分页逻辑

## 5. 测试与验证

- [x] 5.1 测试无昨日数据场景，所有达标股票应标记为 "new_reach"
- [x] 5.2 测试有昨日数据场景，验证 "new_reach" 和 "continuous_reach" 分类正确
- [x] 5.3 测试前端兼容性，确保后端未返回 `reach_type` 时使用默认值
- [x] 5.4 验证 UI 展示：颜色、分组、排序符合设计要求
