## Context

当前交易日历获取只依赖 AkShare API，存在单点故障风险。AkShare 返回的日期格式可能变化（当前是 `2026-01-05`），导致解析失败。

## Goals / Non-Goals

**Goals:**
- 修复日期格式解析，支持多种格式
- 实现多层数据源 fallback 机制
- 确保交易日判断 100% 可用

**Non-Goals:**
- 不修改前端逻辑
- 不改变数据库模型
- 不添加用户配置界面

## Decisions

### Decision 1: 日期格式解析

**选择**: 创建 `parse_date_flexible` 函数，支持多种格式

**实现**:
```python
def parse_date_flexible(date_str: str) -> Optional[date]:
    """支持多种日期格式的解析"""
    date_str = str(date_str).strip()
    formats = ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None
```

### Decision 2: 多层数据源

**选择**: 3 层 fallback 策略

```
┌─────────────────────────────────────────┐
│ Layer 1: AkShare (主数据源)             │
│ - 修复格式解析                          │
│ - 最准确的节假日数据                    │
└────────────────┬────────────────────────┘
                 │ 失败
                 ▼
┌─────────────────────────────────────────┐
│ Layer 2: exchange_calendars (备用)      │
│ - 纯本地计算，无网络依赖                │
│ - 覆盖主要市场规则                      │
└────────────────┬────────────────────────┘
                 │ 失败
                 ▼
┌─────────────────────────────────────────┐
│ Layer 3: 基础规则兜底                   │
│ - 周末判断（周六/周日）                 │
│ - 数据库缓存数据                        │
└─────────────────────────────────────────┘
```

### Decision 3: exchange_calendars 库

**选择**: 使用 `exchange_calendars` 作为备用数据源

**理由**:
- 活跃维护，支持中国A股市场
- 纯 Python 实现，无外部 API 依赖
- 安装简单，无额外系统依赖

**使用方式**:
```python
import exchange_calendars as xcals
xshg = xcals.get_calendar("XSHG")  # 上海证券交易所
is_trading = xshg.is_session(date_str)
```

## Risks / Trade-offs

### Risk: exchange_calendars 可能不包含特殊节假日
→ **Mitigation**: AkShare 作为主数据源会优先获取官方节假日；即使备用源有误差，第 3 层兜底确保不会崩溃

### Trade-off: 增加了依赖
→ **接受**: exchange_calendars 是轻量级纯 Python 库，影响可忽略
