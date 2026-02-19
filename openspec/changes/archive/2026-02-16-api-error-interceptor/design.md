# API Error Interceptor Design

## Context

当前 `frontend/src/services/api.js` 中的 axios 客户端仅配置了 baseURL 和 headers，没有响应拦截器。所有 API 调用方需要自行处理错误。

## Goals / Non-Goals

**Goals:**
- 统一处理 HTTP 错误，减少调用方代码重复
- 提取后端 FastAPI 返回的 `detail` 字段
- 保持现有 API 函数签名不变（调用方无需修改）

**Non-Goals:**
- 不添加请求重试逻辑（复杂度高，暂不需要）
- 不添加全局错误提示（由调用方决定如何展示）

## Decisions

### Decision 1: 使用 axios 响应拦截器

在 `apiClient` 上添加 `interceptors.response.use()` 的错误处理回调。

**理由：** axios 拦截器是标准做法，代码集中在一处，易于维护。

### Decision 2: 错误对象格式

```javascript
{
  message: string,    // 用户友好的错误消息
  status?: number,    // HTTP 状态码（网络错误时无）
  detail?: any        // 后端原始错误详情
}
```

**理由：** 简单实用，包含足够信息供调用方使用。

### Decision 3: 消息优先级

1. 后端 `response.data.detail`（如果存在）
2. 通用错误消息（根据状态码）
3. 网络错误消息

**理由：** 优先展示后端返回的具体错误，其次使用通用提示。
