## Why

`ReachedIndicator` schema 缺少 `reach_type` 字段，导致 API 响应中该字段被 Pydantic 过滤掉，前端无法区分"新增达标"和"持续达标"。

## What Changes

- 在 `backend/app/schemas.py` 的 `ReachedIndicator` 类中添加 `reach_type` 字段

## Capabilities

### Modified Capabilities
- `reached-stocks-display`: 修复 API 响应中 `reach_type` 字段缺失问题

## Impact

- `backend/app/schemas.py`: ReachedIndicator 类添加 reach_type 字段
