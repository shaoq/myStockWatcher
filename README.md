# 股票指标预警系统 (myStockWatcher)

## 项目简介
本项目是一个基于移动平均线（MA）的股票价格预警系统，帮助用户管理股票并实时监控价格是否达到均线目标。系统支持 A股（含北交所）和美股市场，提供智能缓存和交易时间感知功能。

## 核心功能

### 股票管理
- **股票信息管理**: 增删改查股票信息
- **自动名称识别**: 输入股票代码自动获取股票名称
- **分组管理**: 多对多关系的股票分组，灵活组织监控列表
- **批量操作**: 支持批量删除、批量分组移动

### 指标监控
- **多均线支持**: MA5/MA10/MA20/MA30/MA60/MA120/MA250（日线）
- **同时监控**: 单只股票可同时监控多个均线指标
- **实时计算**: 动态计算均线值，包含当日实时数据
- **偏离度显示**: 显示当前价格与均线的偏离百分比

### 数据来源
- **实时行情**: 新浪财经 API（hq.sinajs.cn）
- **K线数据**: 新浪财经 K 线接口
- **趋势图表**: 分时图/日K/周K/月K（GIF 格式）

### 智能缓存
- **交易时间感知**: 自动识别 A股/美股交易时间
- **智能刷新**: 交易时间内实时获取，非交易时间使用缓存
- **数据标识**: 前端显示数据来源（实时/缓存）
- **自动刷新**: 交易时间内 30 秒间隔自动刷新

### 用户体验
- **友好界面**: Ant Design 现代化 UI
- **状态概览**: 全达标/部分达标/全低于 统计卡片
- **颜色标识**: 达标股票绿色背景，未达标红色背景
- **搜索过滤**: 支持按代码/名称搜索，按达标状态筛选

## 技术栈

### 后端
| 组件 | 技术 |
|------|------|
| 框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | SQLite |
| 数据源 | 新浪财经 API |
| 缓存 | cachetools (TTLCache) |
| 并发 | ThreadPoolExecutor |
| 语言 | Python 3.8+ |

### 前端
| 组件 | 技术 |
|------|------|
| 框架 | React 18 |
| 构建工具 | Vite |
| UI 库 | Ant Design |
| HTTP 客户端 | Axios |
| 语言 | JavaScript/JSX |

## 项目结构

```
myStockWatcher/
├── backend/                      # 后端应用
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口、API 路由
│   │   ├── models.py            # 数据库模型（Stock, Group）
│   │   ├── schemas.py           # Pydantic 请求/响应模式
│   │   ├── crud.py              # 数据库 CRUD 操作
│   │   ├── services.py          # 业务逻辑层（API调用、均线计算）
│   │   ├── database.py          # 数据库连接配置
│   │   └── logging_config.py    # 日志配置
│   ├── requirements.txt         # Python 依赖
│   └── run.sh                   # 后端启动脚本
│
├── frontend/                    # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── StockList.jsx    # 核心股票管理界面
│   │   │   └── StockChart.jsx   # 趋势图组件
│   │   ├── services/
│   │   │   └── api.js           # Axios API 封装
│   │   ├── App.jsx              # 主应用组件
│   │   └── main.jsx             # 应用入口
│   ├── package.json             # Node 依赖
│   └── vite.config.js           # Vite 配置
│
├── start.sh                     # 一键启动脚本
├── CLAUDE.md                    # 开发者指南
└── README.md                    # 项目说明
```

## 快速开始

### 前置要求
- Python 3.8+
- Node.js 16+
- Conda（可选，推荐）

### 方式一：一键启动（推荐）

```bash
./start.sh
```

启动后访问：
- **前端界面**: http://localhost:3000
- **API 文档**: http://localhost:9000/docs

### 方式二：分别启动

#### 启动后端
```bash
cd backend
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 9000
```

#### 启动前端
```bash
cd frontend
npm install
npm run dev
```

## API 端点

### 股票管理
| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/stocks/` | 创建股票（自动获取名称） |
| GET | `/stocks/` | 获取所有股票（支持分组/关键词过滤） |
| GET | `/stocks/{id}` | 获取单个股票详情 |
| PUT | `/stocks/{id}` | 更新股票设置 |
| DELETE | `/stocks/{id}` | 删除股票 |
| POST | `/stocks/batch-delete` | 批量删除 |
| POST | `/stocks/batch-remove-from-group` | 从分组批量移出 |

### 价格查询
| 方法 | 端点 | 说明 |
|------|------|------|
| POST/GET | `/stocks/symbol/{symbol}/update-price` | 刷新单只股票价格 |
| POST | `/stocks/update-all-prices` | 批量刷新所有股票 |
| GET | `/stocks/symbol/{symbol}/charts` | 获取趋势图 URL |

### 分组管理
| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/groups/` | 获取所有分组 |
| POST | `/groups/` | 创建分组 |
| DELETE | `/groups/{id}` | 删除分组 |

## 股票代码格式

系统支持多种输入格式，会自动转换为新浪接口格式：

| 用户输入 | 新浪接口格式 | 市场 |
|---------|-------------|------|
| `600000` / `600000.SH` | `sh600000` | A股上海 |
| `000001` / `000001.SZ` | `sz000001` | A股深圳 |
| `832000` / `832000.BJ` | `bj832000` | 北交所 |
| `AAPL` | `gb_aapl` | 美股 |

## 架构设计

### 后端分层架构
```
┌─────────────────────────────────────┐
│           路由层 (main.py)           │  ← HTTP 请求处理
├─────────────────────────────────────┤
│           业务层 (services.py)       │  ← 外部 API、均线计算
├─────────────────────────────────────┤
│           数据层 (crud.py)           │  ← 数据库 CRUD
├─────────────────────────────────────┤
│    模型层 (models.py/schemas.py)    │  ← 数据结构定义
└─────────────────────────────────────┘
```

### 数据流向
1. 用户输入股票代码 → 后端自动获取名称
2. 用户设置监控指标（如 MA5, MA20）
3. 系统获取实时价格 + K线数据
4. 动态计算均线值，判断达标状态
5. 前端展示达标状态和偏离度

## 开发说明

详细的开发指南请参考 [CLAUDE.md](./CLAUDE.md)，包含：
- 常用命令
- API 架构详解
- 股票代码转换规则
- 交易时间智能缓存机制
- 开发规范

## 开发者

项目由 Claude Code 辅助开发
