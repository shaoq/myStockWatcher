## Why

当前股票列表已支持多选和批量删除功能，但缺少批量将股票归属到分组的能力。用户需要逐个编辑股票才能修改分组归属，操作效率低下。特别是在整理股票分类时，用户希望能够快速将多只股票同时添加到一个或多个分组中。

## What Changes

- **新增** 批量归属股票到分组的功能
- **新增** 分组自动创建能力（输入不存在的分组名时自动创建）
- **新增** 后端 API 端点 `POST /stocks/batch-assign-groups`
- **新增** 前端批量归属弹窗 UI

### 关键行为

- 归属模式为**追加**（不替换原有分组）
- 已在分组内的股票自动跳过（不重复添加）
- 支持选择多个现有分组或输入新分组名
- 输入新分组名后回车确认创建

## Capabilities

### New Capabilities

- `batch-group-assignment`: 批量归属股票到分组的能力，支持追加模式、自动创建分组、去重处理

### Modified Capabilities

无。此功能是全新的能力，不修改现有 capabilities。

## Impact

### 后端

- `backend/app/schemas.py` - 新增 `BatchAssignGroupsRequest` 和 `BatchAssignGroupsResponse`
- `backend/app/crud.py` - 新增 `batch_assign_groups_to_stocks()` 函数
- `backend/app/main.py` - 新增 `POST /stocks/batch-assign-groups` 端点

### 前端

- `frontend/src/services/api.js` - 新增 `batchAssignGroups()` API 调用
- `frontend/src/components/StockList.jsx` - 新增批量归属按钮和弹窗 UI

### 数据库

无变更（复用现有的 `stock_group_association` 多对多关联表）
