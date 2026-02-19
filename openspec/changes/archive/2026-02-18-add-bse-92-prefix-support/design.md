## Context

当前 `normalize_symbol_for_sina()` 函数在处理 6 位纯数字股票代码时，使用 `startswith()` 方法判断市场：

```python
# 当前实现
if len(symbol) == 6:
    if symbol.startswith(('6', '9')): return f"sh{symbol}", "cn"  # 上海
    if symbol.startswith(('0', '3')): return f"sz{symbol}", "cn"  # 深圳
    if symbol.startswith(('8', '4')): return f"bj{symbol}", "cn"  # 北交所
```

问题：`9` 开头会被优先匹配到上交所，但北交所新启用的 **92** 开头代码应该归到北交所。

## Goals / Non-Goals

**Goals:**
- 正确识别北交所 92 开头的股票代码
- 保持对现有股票代码（43/83/87/88/6/0/3/其他9）的兼容

**Non-Goals:**
- 不修改 API 接口或前端代码
- 不修改数据库模型

## Decisions

### 决策 1：修改判断顺序

**方案**: 先检查北交所特有的前缀（4, 8, 92），再处理其他情况

```python
# 修改后
if len(symbol) == 6:
    # 先检查北交所（更具体的条件优先）
    if symbol.startswith(('4', '8')): return f"bj{symbol}", "cn"
    if symbol.startswith('92'): return f"bj{symbol}", "cn"
    # 再检查上海和深圳
    if symbol.startswith('6'): return f"sh{symbol}", "cn"
    if symbol.startswith('9'): return f"sh{symbol}", "cn"  # 其他9开头
    if symbol.startswith(('0', '3')): return f"sz{symbol}", "cn"
```

**备选方案**: 合并北交所判断条件
```python
if symbol.startswith(('4', '8')) or symbol.startswith('92'):
    return f"bj{symbol}", "cn"
```

**选择方案1**，代码更清晰，便于后续维护。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 新浪 API 不支持 bj92 前缀 | 已测试验证：`bj920493` 可正确返回数据 |
| 未来北交所可能新增其他前缀 | 代码结构清晰，易于扩展 |
