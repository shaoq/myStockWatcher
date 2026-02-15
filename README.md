# 股票信息和价格检查应用

## 项目描述
本项目是一个股票信息和价格检查的应用,帮助用户管理股票并监控价格是否达到目标值。

## 项目功能
- ✅ 股票信息管理:增加、删除、查询、修改股票信息
- ✅ 实时价格查询:根据股票代码查询当前价格
- ✅ 目标价格监控:自动计算股票价格是否到达目标值
- ✅ 友好的用户界面:使用Ant Design提供现代化UI

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: SQLite + SQLAlchemy ORM
- **API数据源**: yfinance (Yahoo Finance)
- **语言**: Python 3.8+

### 前端
- **框架**: React 18
- **构建工具**: Vite
- **UI库**: Ant Design
- **路由**: React Router
- **HTTP客户端**: Axios
- **语言**: JavaScript/JSX

## 项目结构
```
mylearnapp/
├── backend/                # 后端应用
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py        # FastAPI应用入口
│   │   ├── models.py      # 数据库模型
│   │   ├── schemas.py     # Pydantic模式
│   │   ├── crud.py        # 数据库CRUD操作
│   │   ├── database.py    # 数据库配置
│   │   └── services.py    # 业务逻辑(股票价格查询)
│   ├── requirements.txt   # Python依赖
│   └── run.sh            # 启动脚本
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── components/   # React组件
│   │   ├── services/     # API服务
│   │   ├── App.jsx       # 主应用组件
│   │   └── main.jsx      # 应用入口
│   ├── package.json      # Node依赖
│   └── vite.config.js    # Vite配置
└── README.md             # 项目说明

```

## 快速开始

### 前置要求
- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 安装和运行

#### 1. 启动后端
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

#### 2. 启动前端
```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 即可使用应用

## API文档
后端启动后访问 http://localhost:8000/docs 查看自动生成的API文档

## 开发者
项目由 Claude Code 辅助开发, 3Q
