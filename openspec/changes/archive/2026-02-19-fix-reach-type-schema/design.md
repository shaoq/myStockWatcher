## Context

后端 `services.py` 已正确计算 `reach_type` 字段，但 `schemas.py` 中的 Pydantic 模型未定义该字段，导致序列化时被过滤。

## Decisions

直接在 `ReachedIndicator` 类中添加 `reach_type` 字段。

## Risks / Trade-offs

无风险，字段已存在于数据中，只是 schema 未定义。
