## 1. 后端 Schema 定义

- [x] 1.1 在 `backend/app/schemas.py` 中添加 `BatchAssignGroupsRequest` 模型
- [x] 1.2 在 `backend/app/schemas.py` 中添加 `BatchAssignGroupsResponse` 模型

## 2. 后端 CRUD 操作

- [x] 2.1 在 `backend/app/crud.py` 中添加 `batch_assign_groups_to_stocks()` 函数
- [x] 2.2 实现分组查找或创建逻辑
- [x] 2.3 实现追加模式归属逻辑（保留原有分组）
- [x] 2.4 实现已在分组内的跳过逻辑

## 3. 后端 API 端点

- [x] 3.1 在 `backend/app/main.py` 中添加 `POST /stocks/batch-assign-groups` 端点
- [x] 3.2 实现请求验证和响应格式化
- [x] 3.3 添加错误处理

## 4. 前端 API 服务

- [x] 4.1 在 `frontend/src/services/api.js` 中添加 `batchAssignGroups()` 方法

## 5. 前端 UI 组件

- [x] 5.1 在 `StockList.jsx` 中添加 `assignModalVisible` 状态
- [x] 5.2 在 `StockList.jsx` 中添加 `assignForm` 表单实例
- [x] 5.3 在批量操作区添加"批量归属"按钮
- [x] 5.4 创建批量归属弹窗组件（Modal + Select tags）
- [x] 5.5 实现 `handleBatchAssign()` 处理函数
- [x] 5.6 添加表单验证（至少选择一个分组）
- [x] 5.7 实现成功/失败反馈消息

## 6. 测试验证

- [x] 6.1 测试批量归属到现有分组 - 3只股票成功归属到"科技板块"
- [x] 6.2 测试自动创建新分组 - 新建"科技板块"和"白马股"分组
- [x] 6.3 测试追加模式（保留原有分组）- 股票920493同时属于"科技板块"和"白马股"
- [x] 6.4 测试已在分组内的跳过逻辑 - 2只跳过，1只成功归属
- [x] 6.5 测试表单验证（未选择分组时禁用提交）- 空参数返回400错误
- [x] 6.6 测试各种反馈消息显示 - 详细的成功/跳过消息
