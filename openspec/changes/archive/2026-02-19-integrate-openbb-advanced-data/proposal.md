## Why

当前股票监控系统仅支持实时价格、K线数据和 MA 指标计算，无法获取财报、估值指标、宏观经济等深度投研数据。用户在进行股票分析时缺乏基本面数据支撑，限制了系统的投研价值。

OpenBB 是一个开源的金融数据平台，提供 100+ 数据源整合、统一 API 接口，支持财报、估值、宏观等多种数据类型。通过集成 OpenBB 作为高级数据源，可以在保持现有 A 股实时数据优势的同时，为用户提供更丰富的投研功能。

## What Changes

### 新增功能
- 新增 OpenBB Provider 数据源提供者（L5 优先级，用于高级数据）
- 扩展 DataProvider 基类，支持声明数据能力（CAPABILITIES）
- 新增财报数据服务：资产负债表、利润表、现金流量表
- 新增估值指标服务：PE/PB/ROE/营收增长/利润率等
- 新增宏观经济指标服务：GDP/CPI/利率等
- 新增 API 端点：`/stocks/{symbol}/financial/*`、`/stocks/{symbol}/valuation`、`/macro/*`
- 新增分层缓存策略：财报 24h、估值 1h、宏观 24h

### 架构变更
- 扩展 DataSourceCoordinator，支持按能力路由到合适的 Provider
- 新增 `providers/openbb/` 模块目录
- 新增 `services/advanced/` 高级数据服务目录

### 依赖变更
- 新增 `openbb>=4.0.0` 依赖
- 可选依赖 `openbb-akshare` 用于增强 A 股数据支持

## Capabilities

### New Capabilities

- `financial-data`: 财报数据获取能力，支持资产负债表、利润表、现金流量表的季度和年度数据查询
- `valuation-metrics`: 估值指标计算能力，支持 PE/PB/ROE/营收增长/利润率/负债率等关键指标
- `macro-indicators`: 宏观经济指标能力，支持 GDP/CPI/利率/汇率等宏观指标查询
- `data-source-capabilities`: 数据源能力声明系统，允许 Provider 声明支持的数据类型

### Modified Capabilities

（无现有能力变更，本次为纯新增功能）

## Impact

### 代码影响
- `backend/app/providers/base.py` - 扩展基类，新增 CAPABILITIES 属性和高级数据方法
- `backend/app/providers/coordinator.py` - 扩展协调器，新增按能力路由方法
- `backend/app/providers/__init__.py` - 更新导出
- `backend/app/main.py` - 新增 API 路由
- `backend/app/schemas/` - 新增高级数据 Schema

### 新增文件
- `backend/app/providers/openbb/__init__.py`
- `backend/app/providers/openbb/provider.py`
- `backend/app/providers/openbb/extensions.py`
- `backend/app/services/advanced/__init__.py`
- `backend/app/services/advanced/financial.py`
- `backend/app/services/advanced/valuation.py`
- `backend/app/services/advanced/macro.py`
- `backend/app/schemas/advanced.py`

### 依赖影响
- `backend/requirements.txt` - 新增 openbb 依赖

### API 影响
- 新增 `GET /stocks/{symbol}/financial/report` - 财报数据
- 新增 `GET /stocks/{symbol}/valuation` - 估值指标
- 新增 `GET /macro/indicators` - 宏观指标

### 兼容性
- 完全向后兼容，现有功能不受影响
- OpenBB 为可选依赖，安装失败时高级功能优雅降级
