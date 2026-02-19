## 1. Schema 修复

- [x] 1.1 在 `backend/app/schemas.py` 的 `ReachedIndicator` 类中添加 `reach_type: str` 字段

## 2. 验证

- [x] 2.1 重启后端服务，验证 API 响应中包含 `reach_type` 字段
