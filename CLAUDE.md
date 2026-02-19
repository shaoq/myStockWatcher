# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

### 快速启动 (全栈)
- **启动完整应用**: `./start.sh` (自动同时启动前后端，后端9000端口，前端3000端口)

### 后端 (Python/FastAPI)
- **启动开发服务器**: `cd backend && python3 -m uvicorn app.main:app --reload --port 9000`
- **安装依赖**: `cd backend && pip install -r requirements.txt`
- **查看 API 文档**: 启动后访问 `http://localhost:9000/docs`

### 前端 (React/Vite)
- **启动开发服务器**: `cd frontend && npm run dev`
- **安装依赖**: `cd frontend && npm install`
- **构建生产版本**: `cd frontend && npm run build`
- **代码规范检查**: `cd frontend && npm run lint`

## 项目架构

### 技术栈
- **后端**: FastAPI, SQLAlchemy (ORM), SQLite (数据库)
- **数据源**: 多数据源协调器（新浪/东方财富/腾讯/网易 + AKShare + OpenBB）
- **前端**: React 18+, Vite (构建工具), Ant Design (UI 框架), Axios (HTTP 客户端)

### 核心功能
基于移动平均线（MA）的股票价格预警系统，支持：
- 股票信息管理（CRUD）
- 实时价格查询（多数据源协调器：新浪→东方财富→腾讯→网易）
- 多移动平均线指标监控（MA5, MA20 等，逗号分隔）
- 股票分组管理（多对多关系）
- 趋势图 URL 生成
- 交易时间智能缓存（区分实时/缓存数据）
- 每日报告生成与历史报告查看
- 交易日历智能判断（多层数据源保障）
- 高级数据功能：
  - **A 股**（AKShare）：财报数据、估值指标（PE/PB）
  - **美股/全球**（OpenBB）：财报数据、估值指标、宏观经济指标（GDP/CPI/利率）

### 目录结构与核心逻辑
- **`backend/app/`**:
    - `main.py`: FastAPI 应用入口，定义所有 RESTful API 路由
    - `models.py`: 数据库模型（`Stock`, `Group`, `StockSnapshot`, `TradingCalendar`）
    - `schemas/`: Pydantic 模式目录
        - `__init__.py`: 基础模式
        - `advanced.py`: 高级数据模式（财报、估值、宏观）
    - `crud.py`: 封装底层数据库 CRUD 操作
    - `services/`: 业务逻辑层目录
        - `__init__.py`: 核心业务逻辑（交易日历、快照生成、报告计算、缓存）
        - `advanced/`: 高级数据服务
            - `financial.py`: 财报服务
            - `valuation.py`: 估值服务
            - `macro.py`: 宏观经济服务
    - `providers/`: 数据源提供者目录
        - `base.py`: 数据源基类和能力声明
        - `coordinator.py`: 多数据源协调器
        - `sina.py`, `eastmoney.py`, `tencent.py`, `netease.py`: 基础数据源
        - `akshare.py`: A 股高级数据源（财报、估值）
        - `openbb/`: OpenBB 高级数据源（美股、宏观）
    - `database.py`: 数据库连接配置（SQLite）
- **`frontend/src/`**:
    - `components/StockList.jsx`: 核心股票管理界面
    - `components/DailyReport.jsx`: 每日报告页面（简化版，支持点击查看趋势图）
    - `components/StockChart.jsx`: 股票趋势图组件（分时图、日K、周K、月K）
    - `services/api.js`: Axios 客户端封装，统一处理后端请求
    - `App.jsx`: 应用主布局与 Ant Design 全局主题配置

### 后端 API 架构
后端采用经典分层架构：
- **路由层** (`main.py`): 定义 API 端点，处理 HTTP 请求/响应
- **业务层** (`services.py`): 调用外部 API，计算均线状态
- **数据层** (`crud.py`): 数据库 CRUD 操作
- **模型层** (`models.py`, `schemas.py`): 数据库模型和数据验证

关键端点：
- `POST /stocks/` - 创建股票（自动获取股票名称）
- `GET /stocks/` - 获取所有股票（支持 `group_id` 和 `q` 参数过滤）
- `POST /stocks/symbol/{symbol}/update-price` - 刷新指定股票价格
- `POST /stocks/update-all-prices` - 批量刷新所有股票价格
- `GET /stocks/symbol/{symbol}/charts` - 获取股票趋势图 URL
- 分组管理端点：`/groups/` 系列接口
- 交易日历端点：`/trading-calendar/check`, `/trading-calendar/refresh`
- 快照管理端点：`/snapshots/generate`, `/snapshots/check-today`, `/snapshots/dates`
- 每日报告端点：`/reports/daily`（支持分页）
- 高级数据端点（多数据源）：
  - `GET /stocks/{symbol}/financial/report` - 获取财报数据（A股: AKShare, 美股: OpenBB）
  - `GET /stocks/{symbol}/valuation` - 获取估值指标（A股: AKShare, 美股: OpenBB）
  - `GET /macro/indicators` - 获取宏观经济指标（OpenBB，支持 us/cn 市场）
- 数据源管理端点：`/providers/health`, `/providers/capabilities`

### 数据流向
1. 用户在前端输入股票代码 → `createStock()` → 后端 `/stocks/`
2. 后端通过 `services.fetch_stock_name()` 获取股票名称
3. 用户点击刷新价格 → `updateStockPriceBySymbol()` → 后端计算 MA 并更新数据库
4. 前端调用 `getAllStocks()` → 后端 `enrich_stock_with_status()` 富化数据（包含 MA 达标状态）

### 股票代码规范
用户输入的代码会通过 `services.normalize_symbol_for_sina()` 转换为新浪接口格式：

**转换规则**（按优先级）：
1. **带后缀格式**（如 `600000.SH`, `000001.SZ`）：
   - `.SS` / `.SH` → 上海 (`sh` 前缀，如 `sh600000`)
   - `.SZ` → 深圳 (`sz` 前缀，如 `sz000001`)
   - `.BJ` → 北交所 (`bj` 前缀，如 `bj832000`)
2. **6位纯数字**：
   - `6` 或 `9` 开头 → 上海 (`sh` 前缀，如 `sh600000`)
   - `0` 或 `3` 开头 → 深圳 (`sz` 前缀，如 `sz000001`)
   - `8` 或 `4` 开头 → 北交所 (`bj` 前缀，如 `bj832000`)
3. **非数字且无点号** → 美股，直接使用（如 `AAPL`）

**示例输入与转换结果**：
| 用户输入 | 新浪接口格式 | 市场 |
|---------|------------|-----|
| `600000` / `600000.SH` | `sh600000` | A股上海 |
| `000001` / `000001.SZ` | `sz000001` | A股深圳 |
| `832000` / `832000.BJ` | `bj832000` | 北交所 |
| `AAPL` | `gb_aapl` | 美股 |

### 开发规范
- **语言偏好**: 始终使用**中文**进行回复和代码注释
- **通信协议**: 前后端通过 RESTful API 进行交互，JSON 格式
- **错误处理**: 后端使用 `HTTPException` 返回标准错误，前端通过 Ant Design 的 `message` 组件提示用户
- **数据源**: 实时价格从新浪财经 API 获取（`hq.sinajs.cn`），K 线数据从新浪财经 K 线接口获取

## 交易时间智能缓存

### 功能概述
系统根据股票所属市场的交易时间，智能判断数据是实时获取还是使用缓存，避免非交易时间不必要的 API 请求。

### 后端实现 (`services.py`)

**交易时间判断函数**：
- `is_cn_trading_time()`: A股交易时间判断
  - 工作日 9:30-11:30, 13:00-15:00（北京时间）
- `is_us_trading_time()`: 美股交易时间判断
  - 周一至周五 9:30-16:00（美东时间）
- `is_trading_time(market)`: 统一接口，根据市场类型调用对应判断函数
- `should_refresh_price(stock, market)`: 智能判断是否需要刷新数据

**API 响应增强**：
- `is_realtime`: boolean 字段，标识数据来源
  - `true`: 交易时间内实时获取的数据
  - `false`: 非交易时间使用的缓存数据

### 前端实现 (`StockList.jsx`)

**数据来源标识**：
- 实时数据：显示 🟢 实时 标识
- 缓存数据：显示 🕐 缓存 标识

**自动刷新逻辑**：
- 交易时间内：30 秒间隔自动刷新价格
- 非交易时间：暂停自动刷新，节省 API 请求

**交易状态显示**：
- 标题区域显示当前市场状态："交易中" 或 "休市"

### 市场类型识别
根据股票代码自动识别市场类型：
- **A股**: 6/9/0/3/8/4 开头的 6 位数字代码
- **美股**: 字母代码（如 AAPL, TSLA）

## 每日报告功能

### 功能概述
每日报告页面展示股票指标达标状态，支持查看历史报告和交易日判断。

### 前端实现 (`DailyReport.jsx`)

**主要功能**：
- **达标个股列表**：按MA分组展示，区分新增达标/持续达标
- **未达标个股列表**：按MA分组展示，区分新跌破/持续未达标
- **点击查看趋势图**：点击股票代码/名称弹出趋势图Modal（分时图、日K、周K、月K）
- **历史报告**：日期选择器支持查看历史报告
- **交易日判断**：显示"交易日"或"休市"状态

**MA分组展示**：
- 按MA数值升序排列（MA5 → MA10 → MA20 → MA60）
- 组内按偏离度排序（达标降序，未达标升序）
- 支持折叠面板交互

**点击查看趋势图**：
- 股票代码显示为蓝色可点击样式
- 点击后弹出Modal，复用 `StockChart` 组件
- 支持分时图、日K线、周K线、月K线切换

**日期选择器功能**：
- 禁用未来日期（只能选择今天及之前的日期）
- 有报告的日期显示绿色小圆点标记
- 选择无快照的历史交易日时，弹出确认对话框询问是否生成报告

**关键状态**：
- `chartModalVisible`: 趋势图Modal可见性
- `selectedSymbol`: 选中的股票 {symbol, name}
- `checkingTradingDay`: 交易日检查的 loading 状态
- `isNonTradingDay`: 是否为非交易日
- `availableDates`: 有快照的日期列表

## 交易日历功能

### 功能概述
智能判断指定日期是否为交易日，支持周末和中国节假日判断。

### 数据源架构（3 层保障）

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: AkShare（主数据源）                                │
│  - 节假日数据最准确                                          │
│  - 支持多种日期格式：2026-01-05 / 20260105 / 2026/01/05     │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: exchange_calendars（备用数据源）                   │
│  - 纯本地计算，无网络依赖                                    │
│  - 使用上海证券交易所(XSHG)日历                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 周末判断（基础兜底）                               │
│  - 最终保障，确保任何情况都能返回有效判断                    │
└─────────────────────────────────────────────────────────────┘
```

### 后端实现 (`services.py`)

**关键函数**：
- `parse_date_flexible(date_str)`: 灵活的日期解析，支持多种格式
- `fetch_trading_calendar_from_akshare(year)`: 从 AkShare 获取交易日历
- `fetch_trading_calendar_from_exchange_calendars(year)`: 备用数据源
- `get_trading_dates_with_fallback(year)`: 多层数据源 fallback
- `is_trading_day(db, target_date)`: 判断指定日期是否为交易日

### 数据库模型 (`TradingCalendar`)
- `trade_date`: 日期
- `is_trading_day`: 是否为交易日 (0/1)
- `year`: 年份（用于批量查询缓存）

## 多数据源架构

### 数据源协调器

系统采用多数据源协调器架构，支持自动 fallback 和智能路由：

```
┌─────────────────────────────────────────────────────────────────┐
│                  DataSourceCoordinator                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  L1: 新浪财经 (最快，易封禁) - 实时价格/K线                  │ │
│  │  L2: 东方财富 (AKShare，稳定) - 实时价格/K线                 │ │
│  │  L3: 腾讯财经 (备用) - 实时价格/K线                          │ │
│  │  L4: 网易财经 (兜底) - 实时价格/K线                          │ │
│  │  L4: AKShare (A 股高级数据) - 财报/估值                      │ │
│  │  L5: OpenBB (美股/全球高级数据) - 财报/估值/宏观             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Provider 能力声明

每个数据源提供者通过 `CAPABILITIES` 属性声明支持的能力：
- `realtime_price`: 实时价格
- `kline_data`: K线数据
- `financial_report`: 财报数据
- `valuation_metrics`: 估值指标
- `macro_indicators`: 宏观经济指标

**各 Provider 能力对照表**：
| Provider | 实时价格 | K线 | 财报 | 估值 | 宏观 |
|----------|---------|-----|------|------|------|
| sina | ✅ | ✅ | - | - | - |
| eastmoney | ✅ | ✅ | - | - | - |
| tencent | ✅ | ✅ | - | - | - |
| netease | ✅ | ✅ | - | - | - |
| akshare | - | - | ✅ (A股) | ✅ (A股) | - |
| openbb | ✅ | ✅ | ✅ (美股) | ✅ (美股) | ✅ |

协调器根据请求的能力类型和市场，自动路由到支持该能力的 Provider。

### AKShare 集成（A 股高级数据）

AKShare 是开源财经数据接口库，提供 A 股财报和估值数据。

**已安装**：作为项目依赖，无需额外安装

**支持功能**：
- A 股财报数据（资产负债表、利润表、现金流量表）
- A 股估值指标（PE、PB、ROE、每股收益等）

**数据来源**：东方财富、同花顺等

### OpenBB 集成（美股/全球高级数据）

OpenBB 是开源金融数据平台，提供美股财报、估值、宏观等高级数据。

**安装依赖**：
```bash
cd backend
pip install openbb>=4.0.0
```

**FMP API 配置**（用于美股估值/财报）：
```python
# 在 app/providers/openbb/provider.py 中配置
obb.user.credentials.fmp_api_key = "your-api-key"
```

**A股代码转换**：
OpenBB 使用 Yahoo Finance 格式，系统自动转换：
- `sh600000` → `600000.SHA` (上海)
- `sz000001` → `000001.SZE` (深圳)

**缓存策略**：
| 数据类型 | 缓存时间 |
|---------|---------|
| 财报数据 | 24小时 |
| 估值指标 | 1小时 |
| 宏观指标 | 24小时 |

**错误处理**：
- OpenBB/AKShare 未安装时，高级数据端点返回 503 错误
- 数据获取失败时，返回详细错误信息

