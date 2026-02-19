## Context

### 当前状态

现有系统采用多数据源协调器架构，支持 4 层 fallback：

```
新浪财经(L1) → 东方财富(L2) → 腾讯财经(L3) → 网易财经(L4)
```

**现有能力**：
- A 股/美股实时价格获取
- K 线数据获取
- MA 指标计算
- 交易日历判断

**局限性**：
- 无法获取财报数据（资产负债表、利润表、现金流量表）
- 无法获取估值指标（PE/PB/ROE 等）
- 无法获取宏观经济数据
- 扩展新数据类型需要手写 Provider

### OpenBB 平台

OpenBB 是开源金融数据平台，特性：
- 100+ 数据源整合
- 统一 Python API
- 支持 A 股（通过 AKShare 扩展）
- 覆盖：股票、期权、加密货币、宏观、财报等

### 约束

- 必须保持现有 A 股实时数据能力（新浪最快）
- OpenBB 为可选依赖，安装失败不应影响核心功能
- 需要兼容现有 Provider 架构

## Goals / Non-Goals

**Goals:**
1. 集成 OpenBB 作为高级数据源（L5 优先级）
2. 实现财报数据获取（资产负债表、利润表、现金流量表）
3. 实现估值指标获取（PE/PB/ROE/营收增长等）
4. 实现宏观经济指标获取（GDP/CPI/利率等）
5. 扩展 Provider 基类支持能力声明
6. 实现分层缓存策略

**Non-Goals:**
1. 不替换现有的实时价格数据源（新浪仍然最快）
2. 不实现新闻舆情功能（本次迭代排除）
3. 不修改前端 UI（后续单独迭代）
4. 不实现 OpenBB 的付费功能（仅使用免费 API）

## Decisions

### D1: 混合架构模式

**决策**：采用混合架构，OpenBB 作为新增 Provider 接入现有协调器。

**理由**：
- 保留现有 A 股实时数据优势
- 复用现有的协调器、缓存、错误处理机制
- 渐进式扩展，风险可控

**备选方案**：
- ❌ 完全迁移到 OpenBB：会失去 A 股实时性优势，且 A 股支持有限
- ❌ 独立服务：增加运维复杂度，数据难以统一

### D2: Provider 能力声明系统

**决策**：扩展 DataProvider 基类，新增 `CAPABILITIES` 属性。

```python
class DataProvider(ABC):
    CAPABILITIES: Set[str] = set()  # 声明支持的能力

    # 示例
    # SinaProvider.CAPABILITIES = {"realtime_price", "kline_data"}
    # OpenBBProvider.CAPABILITIES = {"realtime_price", "kline_data", "financial_report", ...}
```

**理由**：
- 协调器可以根据请求类型智能路由
- 避免向不支持某能力的 Provider 发送请求
- 便于扩展更多 Provider

### D3: OpenBB 优先级

**决策**：OpenBB Provider 设置为 L5（最低优先级）。

**理由**：
- 实时价格：新浪 > 东方财富 > 腾讯 > 网易 > OpenBB（有延迟）
- 高级数据：仅 OpenBB 提供，直接使用
- 避免与现有数据源竞争

### D4: 懒加载 OpenBB

**决策**：OpenBB 采用懒加载，首次使用时才初始化。

```python
_obb = None

def get_obb():
    global _obb
    if _obb is None:
        try:
            from openbb import obb
            _obb = obb
        except ImportError:
            pass
    return _obb
```

**理由**：
- 减少启动时间
- OpenBB 未安装时不影响其他功能
- 节省内存（OpenBB 较大）

### D5: 分层缓存策略

**决策**：根据数据类型设置不同缓存时间。

| 数据类型 | 缓存时间 | 理由 |
|---------|---------|------|
| 实时价格 | 5s/24h | 交易时间实时，非交易时间缓存 |
| K 线 | 10min | 日内变化不大 |
| 财报数据 | 24h | 季报更新，日内不变 |
| 估值指标 | 1h | 价格变动影响估值 |
| 宏观指标 | 24h | 月度/季度更新 |

**理由**：
- 平衡实时性和性能
- 减少不必要的 API 调用
- 避免触发 OpenBB 限流

### D6: A 股代码转换

**决策**：在 OpenBB Provider 内部处理 A 股代码格式转换。

```python
def _convert_symbol_for_openbb(symbol: str) -> str:
    """将内部格式转换为 OpenBB 格式"""
    # sh600000 → 600000.SHA
    # sz000001 → 000001.SZE
    # bj832000 → 832000.BJB (北交所可能不支持)
```

**理由**：
- OpenBB 使用 Yahoo Finance 格式（如 600000.SHA）
- 转换逻辑封装在 Provider 内部
- 对外暴露统一的内部格式

## Risks / Trade-offs

### R1: OpenBB 安装失败

**风险**：OpenBB 依赖较多，可能安装失败或版本冲突。

**缓解**：
- 将 OpenBB 设为可选依赖
- 启动时检测，不可用时高级功能返回 "暂不可用"
- 提供安装文档和故障排查指南

### R2: A 股数据覆盖不全

**风险**：OpenBB 原生 A 股支持有限，部分股票可能无法获取数据。

**缓解**：
- 配置 AKShare 扩展增强 A 股支持
- 数据获取失败时返回明确错误信息
- 记录失败的股票代码，便于排查

### R3: API 请求超时

**风险**：OpenBB 需要访问多个外部数据源，可能响应较慢。

**缓解**：
- 设置合理超时时间（10s）
- 使用缓存减少重复请求
- 前端显示加载状态

### R4: OpenBB 版本更新

**风险**：OpenBB API 可能在版本更新时发生变化。

**缓解**：
- 锁定依赖版本（`openbb>=4.0.0,<5.0.0`）
- 添加 API 响应格式验证
- 定期测试兼容性

## Migration Plan

### 阶段 1: 基础设施（1-2 天）

1. 添加 OpenBB 依赖到 requirements.txt
2. 创建 `providers/openbb/` 目录结构
3. 扩展 DataProvider 基类
4. 实现 OpenBBProvider 基础框架

### 阶段 2: 核心功能（2-3 天）

1. 实现 `get_financial_report()` 方法
2. 实现 `get_valuation_metrics()` 方法
3. 配置 AKShare 扩展
4. 添加缓存层

### 阶段 3: API & 服务层（2-3 天）

1. 创建 advanced 数据服务
2. 添加新的 API 端点
3. 编写 Schema 定义
4. 单元测试

### 阶段 4: 集成测试（1-2 天）

1. 端到端测试
2. 错误处理验证
3. 性能测试

### 回滚策略

- OpenBB 为可选依赖，可直接移除
- 高级 API 端点返回 503 或移除路由
- 核心功能不受影响

## Open Questions

1. **北交所支持**：OpenBB 是否支持北交所股票？需要测试验证。
2. **美股高级数据**：是否需要支持美股的财报/估值数据？本次先聚焦 A 股。
3. **并发限制**：OpenBB 是否有请求频率限制？需要查阅文档或测试。
4. **数据存储**：是否需要持久化财报/估值数据？目前计划仅使用缓存。
