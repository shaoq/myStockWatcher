"""FastAPI应用主入口"""
import time
import uuid
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from . import models, schemas, crud, services
from .database import engine, get_db
from .logging_config import setup_logging, get_logger, request_id_context

# 初始化日志
setup_logging(log_level="INFO")
logger = get_logger()

# 创建数据库表
models.Base.metadata.create_all(bind=engine)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    功能：
    - 记录所有 API 请求（方法、路径、耗时、状态码）
    - 生成并追踪请求 ID
    - 结构化日志输出
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 生成请求 ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_context.set(request_id)

        # 记录请求开始
        start_time = time.time()

        logger.info(
            "请求开始",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", ""),
            }
        )

        # 处理请求
        try:
            response = await call_next(request)

            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 记录请求完成
            logger.info(
                "请求完成",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )

            # 添加请求 ID 到响应头
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 记录异常
            logger.error(
                f"请求异常: {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise


# 创建FastAPI应用实例
app = FastAPI(
    title="股票指标预警API",
    description="基于移动平均线(MA)的股票价格预警系统后端API",
    version="2.0.0"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

@app.get("/", tags=["根路径"])
def read_root():
    return {
        "message": "欢迎使用股票指标预警API",
        "docs": "/docs",
        "version": "2.0.0"
    }

@app.post("/stocks/", response_model=schemas.StockWithStatus, status_code=status.HTTP_201_CREATED, tags=["股票管理"])
def create_stock(stock: schemas.StockCreate, db: Session = Depends(get_db)):
    """创建并监控新股票（自动获取名称）"""
    db_stock = crud.get_stock_by_symbol(db, symbol=stock.symbol)
    if db_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"股票代码 {stock.symbol} 已存在"
        )

    # 自动获取股票名称
    fetched_name = services.fetch_stock_name(stock.symbol)
    if not fetched_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"无法识别股票代码 {stock.symbol}，请检查格式"
        )

    stock.name = fetched_name
    created_stock = crud.create_stock(db=db, stock=stock)
    # 新增股票，需要计算指标，设置 need_calc=True
    return services.enrich_stock_with_status(created_stock, db=db, need_calc=True)

@app.get("/stocks/", response_model=List[schemas.StockWithStatus], tags=["股票管理"])
def read_stocks(
    group_id: Optional[int] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取所有监控股票及其MA状态（支持按分组过滤和关键词搜索）"""
    # 使用 joinedload 预加载 groups 关联，避免 N+1 查询
    query = db.query(models.Stock).options(joinedload(models.Stock.groups))

    # 关键词搜索 (匹配代码或名称)
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            (models.Stock.symbol.ilike(search_filter)) |
            (models.Stock.name.ilike(search_filter))
        )

    if group_id:
        query = query.join(models.Stock.groups).filter(models.Group.id == group_id)

    # 按添加时间降序排列（最近添加的在最前面）
    stocks = query.order_by(models.Stock.created_at.desc()).offset(skip).limit(limit).all()

    # 使用并发处理批量富化股票数据（普通查询不需要强制计算）
    return services.enrich_stocks_batch(stocks, force_refresh=False, db=db, need_calc=False)


@app.post("/stocks/batch-delete", tags=["股票管理"])
def batch_delete_stocks(stock_ids: List[int], db: Session = Depends(get_db)):
    """批量删除股票"""
    count = crud.batch_delete_stocks(db, stock_ids)
    return {"message": f"成功删除 {count} 只股票记录"}


@app.post("/stocks/batch-remove-from-group", tags=["股票管理"])
def batch_remove_from_group(stock_ids: List[int], group_id: int, db: Session = Depends(get_db)):
    """从指定分组中批量移出股票"""
    stocks = db.query(models.Stock).filter(models.Stock.id.in_(stock_ids)).all()
    count = 0
    for stock in stocks:
        # 过滤掉当前要移除的 group_id
        stock.groups = [g for g in stock.groups if g.id != group_id]
        count += 1
    db.commit()
    return {"message": f"成功从当前分组移出 {count} 只股票"}


@app.post("/stocks/batch-assign-groups", response_model=schemas.BatchAssignGroupsResponse, tags=["股票管理"])
def batch_assign_groups(
    request: schemas.BatchAssignGroupsRequest,
    db: Session = Depends(get_db)
):
    """
    批量将股票归属到分组

    - 采用追加模式（保留原有分组）
    - 分组不存在时自动创建
    - 已在分组内的股票自动跳过
    """
    if not request.stock_ids:
        raise HTTPException(status_code=400, detail="股票ID列表不能为空")

    if not request.group_names:
        raise HTTPException(status_code=400, detail="分组名称列表不能为空")

    result = crud.batch_assign_groups_to_stocks(
        db,
        stock_ids=request.stock_ids,
        group_names=request.group_names
    )

    return schemas.BatchAssignGroupsResponse(**result)


@app.get("/groups/", response_model=List[schemas.GroupInDB], tags=["分组管理"])
def read_groups(db: Session = Depends(get_db)):
    """获取所有分组"""
    groups = crud.get_groups(db)
    # 为每个分组添加股票数量
    return [
        schemas.GroupInDB(id=g.id, name=g.name, stock_count=len(g.stocks))
        for g in groups
    ]


@app.post("/groups/", response_model=schemas.GroupInDB, status_code=status.HTTP_201_CREATED, tags=["分组管理"])
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db)):
    """创建新分组"""
    return crud.create_group(db, group)


@app.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["分组管理"])
def delete_group(group_id: int, db: Session = Depends(get_db)):
    """删除分组"""
    if not crud.delete_group(db, group_id=group_id):
        raise HTTPException(status_code=404, detail="未找到该分组")
    return None

@app.get("/stocks/{stock_id}", response_model=schemas.StockWithStatus, tags=["股票管理"])
def read_stock(stock_id: int, db: Session = Depends(get_db)):
    db_stock = crud.get_stock(db, stock_id=stock_id)
    if db_stock is None:
        raise HTTPException(status_code=404, detail="未找到该股票")
    return services.enrich_stock_with_status(db_stock)

@app.put("/stocks/{stock_id}", response_model=schemas.StockWithStatus, tags=["股票管理"])
def update_stock(stock_id: int, stock_update: schemas.StockUpdate, db: Session = Depends(get_db)):
    """更新股票信息（修改指标时需要重新计算，设置 need_calc=True）"""
    updated_stock = crud.update_stock(db, stock_id=stock_id, stock_update=stock_update)
    if updated_stock is None:
        raise HTTPException(status_code=404, detail="未找到该股票")
    # 修改指标需要重新计算，设置 need_calc=True
    return services.enrich_stock_with_status(updated_stock, db=db, need_calc=True)

@app.delete("/stocks/{stock_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["股票管理"])
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    if not crud.delete_stock(db, stock_id=stock_id):
        raise HTTPException(status_code=404, detail="未找到该股票")
    return None

@app.post("/stocks/symbol/{symbol}/update-price", response_model=schemas.PriceUpdateResponse, tags=["价格查询"])
@app.get("/stocks/symbol/{symbol}/update-price", response_model=schemas.PriceUpdateResponse, tags=["价格查询"])
def update_stock_price_by_symbol(symbol: str, db: Session = Depends(get_db)):
    """刷新指定股票的均线价格（智能缓存：交易时间内实时获取，非交易时间使用缓存）"""
    db_stock = crud.get_stock_by_symbol(db, symbol=symbol)
    if db_stock is None:
        raise HTTPException(status_code=404, detail="数据库中未找到该股票")

    # 使用智能缓存模式（非强制刷新，普通刷新不需要重新计算）
    enriched = services.enrich_stock_with_status(db_stock, force_refresh=False, db=db, need_calc=False)

    if enriched.current_price is None:
        raise HTTPException(
            status_code=503,
            detail=f"股票 {symbol} 数据获取失败，可能已停牌、退市或代码变更，请检查股票代码"
        )

    # 只有实时获取的数据才更新数据库
    if enriched.is_realtime:
        crud.update_stock_price(db, db_stock.id, enriched.current_price)

    # 构造响应消息，包含所有指标状态
    status_parts = []
    for ma, res in enriched.ma_results.items():
        tag = "✅" if res.reached_target else "⏳"
        status_parts.append(f"{ma}:{res.ma_price:.2f} {tag}")

    realtime_tag = "🔴实时" if enriched.is_realtime else "📦缓存"
    message = f"{db_stock.symbol} 当前:{enriched.current_price:.2f} | " + " ".join(status_parts) + f" | {realtime_tag}"

    return schemas.PriceUpdateResponse(
        symbol=db_stock.symbol,
        current_price=enriched.current_price,
        ma_results=enriched.ma_results,
        message=message,
        is_realtime=enriched.is_realtime
    )

@app.post("/stocks/update-all-prices", tags=["价格查询"])
def update_all_prices(db: Session = Depends(get_db)):
    """批量刷新所有监控指标（智能缓存：交易时间内实时获取，非交易时间使用缓存）"""
    # 使用 joinedload 预加载 groups 关联，避免 N+1 查询
    stocks = db.query(models.Stock).options(joinedload(models.Stock.groups)).all()

    # 使用智能缓存模式（非强制刷新，全量刷新也不需要重新计算）
    enriched_stocks = services.enrich_stocks_batch(stocks, force_refresh=False, db=db, need_calc=False)

    # 批量更新数据库中的价格
    count = 0
    for enriched in enriched_stocks:
        if enriched.current_price is not None:
            crud.update_stock_price(db, enriched.id, enriched.current_price)
            count += 1

    return {"message": f"已成功更新 {count} 只股票的均线指标数据"}


@app.post("/stocks/clear-cache-and-refresh", tags=["价格查询"])
def clear_cache_and_refresh(db: Session = Depends(get_db)):
    """清理所有缓存并强制刷新所有股票数据"""
    # 1. 清理内存缓存
    cleared = services.clear_all_caches()

    # 2. 使用 joinedload 预加载 groups 关联
    stocks = db.query(models.Stock).options(joinedload(models.Stock.groups)).all()

    # 3. 强制刷新所有股票数据（force_refresh=True）
    enriched_stocks = services.enrich_stocks_batch(stocks, force_refresh=True, db=db, need_calc=False)

    # 4. 批量更新数据库中的价格
    count = 0
    for enriched in enriched_stocks:
        if enriched.current_price is not None:
            crud.update_stock_price(db, enriched.id, enriched.current_price)
            count += 1

    return {
        "message": f"已清理缓存并刷新 {count} 只股票数据",
        "cleared_cache": cleared,
        "refreshed_stocks": count
    }


@app.get("/stocks/symbol/{symbol}/charts", tags=["价格查询"])
def get_stock_charts(symbol: str):
    """获取股票趋势图 URL 池"""
    return services.get_stock_chart_urls(symbol)


# ============ 交易日历 API ============

@app.get("/trading-calendar/check", tags=["交易日历"])
def check_trading_day(
    target_date: Optional[date] = Query(None, description="要检查的日期，默认为今天"),
    db: Session = Depends(get_db)
):
    """检查指定日期是否为交易日"""
    if target_date is None:
        target_date = date.today()

    is_trading, reason = services.is_trading_day(db, target_date)

    return {
        "date": target_date.isoformat(),
        "is_trading_day": is_trading,
        "reason": reason
    }


@app.post("/trading-calendar/refresh", tags=["交易日历"])
def refresh_trading_calendar(
    year: Optional[int] = Query(None, description="要刷新的年份，默认为当前年份"),
    db: Session = Depends(get_db)
):
    """刷新交易日历缓存"""
    created, message = services.refresh_trading_calendar(db, year)

    return {
        "success": True,
        "created_count": created,
        "message": message
    }


@app.get("/trading-calendar/monthly", tags=["交易日历"])
def get_monthly_trading_days(
    year: int = Query(..., description="年份"),
    month: int = Query(..., description="月份 (1-12)"),
    db: Session = Depends(get_db)
):
    """获取指定月份的交易日列表"""
    from calendar import monthrange
    from datetime import date as date_type
    from . import crud

    # 获取该月的天数
    _, days_in_month = monthrange(year, month)

    # 构建日期范围
    start_date = date_type(year, month, 1)
    end_date = date_type(year, month, days_in_month)

    # 从数据库获取交易日历
    trading_days = crud.get_trading_days_in_range(db, start_date, end_date)

    return {
        "year": year,
        "month": month,
        "trading_days": [d.isoformat() for d in trading_days]
    }


# ============ 快照和报告 API ============

@app.post("/snapshots/generate", response_model=schemas.GenerateSnapshotsResponse, tags=["快照管理"])
def generate_snapshots(
    target_date: Optional[date] = Query(None, description="目标日期，默认为今天"),
    force: bool = Query(False, description="是否强制覆盖已有快照"),
    db: Session = Depends(get_db)
):
    """
    生成快照（为所有监控的股票保存状态）

    触发规则:
    - 历史日期: 用户选择即可触发，已有数据不重复生成（除非 force=True）
    - 当日: 只有收盘后(>15:00)才能触发
    - 非交易日: 返回错误提示

    数据来源:
    - 交易日收盘后: 使用实时数据
    - 历史交易日: 使用 K 线收盘价
    """
    from datetime import datetime as dt
    from zoneinfo import ZoneInfo

    if target_date is None:
        target_date = date.today()

    # 检查是否为交易日
    is_trading, reason = services.is_trading_day(db, target_date)

    if not is_trading:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": f"该日期为非交易日（{reason}）",
                "is_trading_day": False,
                "reason": reason,
                "date": target_date.isoformat()
            }
        )

    # 当日快照：检查是否已收盘
    if target_date == date.today():
        beijing_tz = ZoneInfo("Asia/Shanghai")
        now_beijing = dt.now(beijing_tz)
        current_time = now_beijing.time()

        # A股收盘时间为 15:00
        from datetime import time as t
        if current_time <= t(15, 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "当日快照请在收盘后（15:00后）生成",
                    "is_trading_day": True,
                    "current_time": now_beijing.strftime("%H:%M"),
                    "hint": "当前仍在交易时间内，请等待收盘后再生成快照"
                }
            )

    created, updated, message = services.generate_daily_snapshots(db, force=force, target_date=target_date)
    return schemas.GenerateSnapshotsResponse(
        message=message,
        created_count=created,
        updated_count=updated
    )


@app.get("/snapshots/check-today", response_model=schemas.SnapshotCheckResponse, tags=["快照管理"])
def check_today_snapshots(db: Session = Depends(get_db)):
    """检查今日是否有快照"""
    from datetime import date as date_type
    today = date_type.today()

    total_stocks = db.query(models.Stock).count()
    snapshot_count = crud.count_today_snapshots(db, today)

    return schemas.SnapshotCheckResponse(
        has_snapshots=snapshot_count > 0,
        snapshot_count=snapshot_count,
        total_stocks=total_stocks,
        snapshot_date=today if snapshot_count > 0 else None
    )


@app.get("/snapshots/dates", tags=["快照管理"])
def get_snapshot_dates(db: Session = Depends(get_db)):
    """获取所有有快照的日期列表"""
    from datetime import date as date_type

    dates = crud.get_all_snapshot_dates(db)
    today = date_type.today()

    # 获取今日的相邻日期
    adjacent = crud.get_adjacent_snapshot_dates(db, today)

    return {
        "dates": [d.isoformat() for d in dates],
        "prev_date": adjacent["prev"].isoformat() if adjacent["prev"] else None,
        "next_date": adjacent["next"].isoformat() if adjacent["next"] else None
    }


@app.get("/reports/daily", response_model=schemas.DailyReportResponse, tags=["每日报告"])
def get_daily_report(
    target_date: Optional[date] = None,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=50, description="每页条数，默认10，最大50"),
    db: Session = Depends(get_db)
):
    """
    获取每日报告（支持指定日期和分页）

    - 交易日：返回报告数据
    - 非交易日：返回错误，提示休市
    - page/page_size：用于达标个股列表的分页
    """
    if target_date is None:
        target_date = date.today()

    # 检查是否为交易日
    is_trading, reason = services.is_trading_day(db, target_date)

    if not is_trading:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": f"该日期为非交易日（{reason}）",
                "is_trading_day": False,
                "reason": reason,
                "date": target_date.isoformat()
            }
        )

    report = services.get_daily_report(db, target_date, page=page, page_size=page_size)

    return schemas.DailyReportResponse(
        report_date=report["date"],
        has_yesterday=report["has_yesterday"],
        summary=schemas.DailyReportSummary(**report["summary"]),
        newly_reached=[schemas.StockChangeItem(**item) for item in report["newly_reached"]],
        newly_below=[schemas.StockChangeItem(**item) for item in report["newly_below"]],
        all_below_stocks=[schemas.BelowStockItem(**item) for item in report["all_below_stocks"]],
        reached_stocks=[schemas.ReachedStockItem(**item) for item in report["reached_stocks"]],
        total_reached=report["total_reached"]
    )


# ============ 高级数据 API（财报、估值、宏观） ============

@app.get("/stocks/{symbol}/financial/report", tags=["高级数据"])
def get_financial_report(
    symbol: str,
    report_type: str = Query("balance_sheet", description="报告类型: balance_sheet, income, cash_flow"),
    period: str = Query("quarterly", description="周期: annual, quarterly"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    db: Session = Depends(get_db)
):
    """
    获取股票财报数据

    支持的财报类型:
    - balance_sheet: 资产负债表
    - income: 利润表
    - cash_flow: 现金流量表

    支持的周期:
    - annual: 年报
    - quarterly: 季报
    """
    from .services.advanced import get_financial_report as fetch_financial
    from .services import normalize_symbol_for_sina

    # 获取股票信息
    db_stock = crud.get_stock_by_symbol(db, symbol=symbol)
    if db_stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"股票 {symbol} 不存在"
        )

    # 规范化代码
    normalized_code, market = normalize_symbol_for_sina(symbol)

    # 获取财报数据
    result = fetch_financial(
        symbol=symbol,
        normalized_code=normalized_code,
        market=market,
        name=db_stock.name,
        report_type=report_type,
        period=period,
        use_cache=use_cache
    )

    # 检查是否有错误
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )

    return result


@app.get("/stocks/{symbol}/valuation", tags=["高级数据"])
def get_valuation_metrics(
    symbol: str,
    use_cache: bool = Query(True, description="是否使用缓存"),
    db: Session = Depends(get_db)
):
    """
    获取股票估值指标

    返回指标包括:
    - PE (市盈率)
    - PB (市净率)
    - ROE (净资产收益率)
    - 营收增长率
    - 利润率
    - 负债权益比
    等
    """
    from .services.advanced import get_valuation_metrics as fetch_valuation
    from .services import normalize_symbol_for_sina

    # 获取股票信息
    db_stock = crud.get_stock_by_symbol(db, symbol=symbol)
    if db_stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"股票 {symbol} 不存在"
        )

    # 规范化代码
    normalized_code, market = normalize_symbol_for_sina(symbol)

    # 获取估值数据
    result = fetch_valuation(
        symbol=symbol,
        normalized_code=normalized_code,
        market=market,
        name=db_stock.name,
        current_price=db_stock.current_price,
        use_cache=use_cache
    )

    # 检查是否有错误
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )

    return result


@app.get("/macro/indicators", tags=["高级数据"])
def get_macro_indicators(
    market: str = Query("cn", description="市场: cn (中国), us (美国)"),
    indicators: str = Query("gdp,cpi,interest_rate", description="指标列表，逗号分隔"),
    use_cache: bool = Query(True, description="是否使用缓存")
):
    """
    获取宏观经济指标

    支持的市场:
    - cn: 中国
    - us: 美国

    支持的指标:
    - gdp: GDP增长率
    - cpi: 消费者物价指数
    - interest_rate: 基准利率
    """
    from .services.advanced import get_macro_indicators as fetch_macro

    # 解析指标列表
    indicator_list = [ind.strip() for ind in indicators.split(",") if ind.strip()]

    # 获取宏观指标数据
    result = fetch_macro(
        market=market,
        indicators=indicator_list,
        use_cache=use_cache
    )

    # 检查是否有错误
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )

    return result


@app.get("/providers/capabilities", tags=["数据源管理"])
def get_providers_capabilities():
    """
    获取所有数据源的能力映射

    返回各数据源支持的数据类型:
    - realtime_price: 实时价格
    - kline_data: K线数据
    - financial_report: 财报数据
    - valuation_metrics: 估值指标
    - macro_indicators: 宏观经济指标
    """
    from .providers import get_coordinator
    coordinator = get_coordinator()
    return coordinator.get_capabilities()


# ============ 数据源管理 API ============

@app.get("/providers/health", tags=["数据源管理"])
def get_providers_health():
    """
    获取所有数据源的健康状态

    返回各数据源的:
    - 优先级
    - 当前状态 (healthy/degraded/cooling/disabled)
    - 连续失败次数
    - 是否可用
    - 冷却结束时间（如在冷却中）
    """
    from .providers import get_coordinator
    coordinator = get_coordinator()
    return coordinator.get_health_status()


@app.post("/providers/reset", tags=["数据源管理"])
def reset_provider(provider_name: str = Query(..., description="数据源名称: sina, eastmoney, tencent, netease")):
    """
    重置指定数据源的状态

    用于手动恢复被封禁的数据源
    """
    from .providers import get_coordinator
    coordinator = get_coordinator()

    success = coordinator.reset_provider(provider_name)
    if success:
        return {"success": True, "message": f"数据源 {provider_name} 状态已重置"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到数据源: {provider_name}"
        )


@app.post("/providers/reset-all", tags=["数据源管理"])
def reset_all_providers():
    """重置所有数据源的状态"""
    from .providers import get_coordinator
    coordinator = get_coordinator()
    coordinator.reset_all_providers()
    return {"success": True, "message": "所有数据源状态已重置"}
