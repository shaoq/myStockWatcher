# API Error Interceptor

## Why

当前前端 API 客户端没有统一的错误处理机制。当网络请求失败时（网络超时、服务器错误、业务错误），错误会直接抛给调用方，导致：
- 每个调用点都需要重复编写 try-catch
- 用户看到的是原始错误信息，体验不佳
- 后端返回的错误详情（`detail` 字段）需要手动解析

## What Changes

- 为 axios 客户端添加响应拦截器
- 统一处理 HTTP 错误状态码（4xx, 5xx, 网络错误）
- 提取后端 FastAPI 返回的 `detail` 错误信息
- 将错误封装为一致的格式抛出

## Capabilities

### Modified Capabilities
- `api-client`: 增强错误处理能力，提供统一的错误格式

## Impact

- `frontend/src/services/api.js`: 添加响应拦截器（~20 行代码）
