# api-client Specification

## Purpose
TBD - created by archiving change api-error-interceptor. Update Purpose after archive.
## Requirements
### Requirement: HTTP Error Interception

The API client SHALL intercept all HTTP error responses and extract backend error information in a consistent format.

#### Scenario: 后端返回 4xx 客户端错误

- **WHEN** 后端返回 400/404/422 等 4xx 错误
- **THEN** 拦截器 MUST 提取 `response.data.detail` 作为错误消息
- **AND** 抛出包含 `message` 和 `status` 的错误对象

#### Scenario: 后端返回 5xx 服务器错误

- **WHEN** 后端返回 500/502/503 等 5xx 错误
- **THEN** 拦截器 MUST 使用通用消息"服务器错误，请稍后重试"
- **AND** 抛出包含 `message` 和 `status` 的错误对象

#### Scenario: 网络连接失败

- **WHEN** 网络请求无法到达服务器（断网、超时）
- **THEN** 拦截器 MUST 使用消息"网络连接失败，请检查网络"
- **AND** 抛出包含 `message` 的错误对象

