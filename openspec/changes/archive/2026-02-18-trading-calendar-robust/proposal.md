## Why

交易日历获取功能存在稳定性问题：
1. **日期格式解析错误** - AkShare API 返回 `2026-01-05` 格式，但代码期望 `%Y%m%d` 格式，导致解析失败
2. **单一数据源风险** - 只依赖 AkShare，当 API 不可用时无备用方案
3. **缺乏兜底机制** - 网络异常时完全无法判断交易日

## What Changes

### 修复日期格式解析
- 支持多种日期格式：`%Y-%m-%d`、`%Y%m%d`、`%Y/%m/%d`
- 增加格式自动检测

### 多重保障策略
- **第 1 层**：AkShare（主数据源，修复格式问题）
- **第 2 层**：exchange_calendars 库（备用数据源，纯本地计算）
- **第 3 层**：基础规则兜底（周末判断 + 已缓存数据）

## Capabilities

### New Capabilities

无新能力引入，仅增强现有功能。

### Modified Capabilities

- `trading-calendar`: 增强交易日历获取的稳定性和可靠性
  - 修复日期格式解析问题
  - 添加多层数据源 fallback 机制
  - 确保在任何情况下都能返回有效的交易日判断

## Impact

### 代码影响

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `backend/app/services.py` | 修改 | 多层数据源 + 格式修复 |
| `backend/requirements.txt` | 修改 | 添加 exchange_calendars 依赖 |

### 依赖影响

新增依赖：
- `exchange_calendars>=4.2.0` - 备用交易日历库
