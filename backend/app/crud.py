"""数据库CRUD操作"""
import json
from datetime import date
from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional, Dict


def get_stock(db: Session, stock_id: int) -> Optional[models.Stock]:
    """根据ID获取股票"""
    return db.query(models.Stock).filter(models.Stock.id == stock_id).first()


def get_stock_by_symbol(db: Session, symbol: str) -> Optional[models.Stock]:
    """根据股票代码获取股票"""
    return db.query(models.Stock).filter(models.Stock.symbol == symbol.upper()).first()


def get_stocks(
    db: Session,
    group_id: Optional[int] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.Stock]:
    """获取股票列表，支持按分组过滤和关键词搜索"""
    query = db.query(models.Stock)

    # 关键词搜索 (匹配代码或名称)
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            (models.Stock.symbol.ilike(search_filter)) |
            (models.Stock.name.ilike(search_filter))
        )

    if group_id:
        query = query.join(models.Stock.groups).filter(models.Group.id == group_id)

    return query.offset(skip).limit(limit).all()


def batch_delete_stocks(db: Session, stock_ids: List[int]) -> int:
    """批量从数据库中删除股票记录"""
    count = db.query(models.Stock).filter(models.Stock.id.in_(stock_ids)).delete(synchronize_session=False)
    db.commit()
    return count


def batch_update_stock_groups(db: Session, stock_ids: List[int], group_ids: List[int]) -> int:
    """批量更新多只股票的分组归属"""
    stocks = db.query(models.Stock).filter(models.Stock.id.in_(stock_ids)).all()
    groups = db.query(models.Group).filter(models.Group.id.in_(group_ids)).all()

    for stock in stocks:
        stock.groups = groups

    db.commit()
    return len(stocks)


def create_stock(db: Session, stock: schemas.StockCreate) -> models.Stock:
    """创建新股票"""
    db_stock = models.Stock(
        symbol=stock.symbol.upper(),
        name=stock.name,
        ma_types=",".join(stock.ma_types)
    )

    # 关联分组
    if stock.group_ids:
        groups = db.query(models.Group).filter(models.Group.id.in_(stock.group_ids)).all()
        db_stock.groups = groups

    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock


def update_stock(
    db: Session,
    stock_id: int,
    stock_update: schemas.StockUpdate
) -> Optional[models.Stock]:
    """更新股票信息"""
    db_stock = get_stock(db, stock_id)
    if db_stock is None:
        return None

    update_data = stock_update.model_dump(exclude_unset=True)

    # 处理 ma_types 列表转换为字符串
    if "ma_types" in update_data:
        ma_types_list = update_data.pop("ma_types")
        if ma_types_list is not None:
            db_stock.ma_types = ",".join(ma_types_list)

    # 特殊处理 group_ids
    if "group_ids" in update_data:
        group_ids = update_data.pop("group_ids")
        if group_ids is not None:
            groups = db.query(models.Group).filter(models.Group.id.in_(group_ids)).all()
            db_stock.groups = groups

    for field, value in update_data.items():
        setattr(db_stock, field, value)

    db.commit()
    db.refresh(db_stock)
    return db_stock


# --- 分组相关操作 ---

def get_groups(db: Session) -> List[models.Group]:
    """获取所有分组"""
    return db.query(models.Group).all()


def get_group(db: Session, group_id: int) -> Optional[models.Group]:
    """根据ID获取分组"""
    return db.query(models.Group).filter(models.Group.id == group_id).first()


def create_group(db: Session, group: schemas.GroupCreate) -> models.Group:
    """创建新分组"""
    db_group = models.Group(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


def delete_group(db: Session, group_id: int) -> bool:
    """删除分组"""
    db_group = get_group(db, group_id)
    if db_group is None:
        return False

    db.delete(db_group)
    db.commit()
    return True


def update_stock_price(
    db: Session,
    stock_id: int,
    current_price: float
) -> Optional[models.Stock]:
    """更新股票当前价格"""
    db_stock = get_stock(db, stock_id)
    if db_stock is None:
        return None

    db_stock.current_price = current_price
    db.commit()
    db.refresh(db_stock)
    return db_stock


def delete_stock(db: Session, stock_id: int) -> bool:
    """删除股票"""
    db_stock = get_stock(db, stock_id)
    if db_stock is None:
        return False

    db.delete(db_stock)
    db.commit()
    return True


# --- 快照相关操作 ---

def get_snapshot(db: Session, stock_id: int, snapshot_date: date) -> Optional[models.StockSnapshot]:
    """获取指定股票在指定日期的快照"""
    return db.query(models.StockSnapshot).filter(
        models.StockSnapshot.stock_id == stock_id,
        models.StockSnapshot.snapshot_date == snapshot_date
    ).first()


def get_snapshots_by_date(db: Session, snapshot_date: date) -> List[models.StockSnapshot]:
    """获取指定日期的所有快照"""
    return db.query(models.StockSnapshot).filter(
        models.StockSnapshot.snapshot_date == snapshot_date
    ).all()


def get_latest_snapshot_date(db: Session) -> Optional[date]:
    """获取最新的快照日期"""
    latest = db.query(models.StockSnapshot).order_by(
        models.StockSnapshot.snapshot_date.desc()
    ).first()
    return latest.snapshot_date if latest else None


def get_previous_trading_day_snapshots(db: Session, current_date: date) -> List[models.StockSnapshot]:
    """获取当前日期之前最近一个交易日的快照"""
    return db.query(models.StockSnapshot).filter(
        models.StockSnapshot.snapshot_date < current_date
    ).order_by(models.StockSnapshot.snapshot_date.desc()).limit(100).all()


def create_or_update_snapshot(
    db: Session,
    stock_id: int,
    snapshot_date: date,
    price: float,
    ma_results: Dict
) -> models.StockSnapshot:
    """创建或更新快照（每只股票每天只有一份快照）"""
    existing = get_snapshot(db, stock_id, snapshot_date)

    ma_results_json = json.dumps(ma_results, ensure_ascii=False)

    if existing:
        existing.price = price
        existing.ma_results = ma_results_json
        db.commit()
        db.refresh(existing)
        return existing
    else:
        db_snapshot = models.StockSnapshot(
            stock_id=stock_id,
            snapshot_date=snapshot_date,
            price=price,
            ma_results=ma_results_json
        )
        db.add(db_snapshot)
        db.commit()
        db.refresh(db_snapshot)
        return db_snapshot


def get_snapshots_for_trend(db: Session, days: int = 7) -> Dict[date, List[models.StockSnapshot]]:
    """获取最近 N 天的快照数据，按日期分组"""
    from datetime import timedelta

    end_date = date.today()
    start_date = end_date - timedelta(days=days + 7)  # 多取几天以包含非交易日

    snapshots = db.query(models.StockSnapshot).filter(
        models.StockSnapshot.snapshot_date >= start_date,
        models.StockSnapshot.snapshot_date <= end_date
    ).order_by(models.StockSnapshot.snapshot_date).all()

    # 按日期分组
    result = {}
    for snapshot in snapshots:
        if snapshot.snapshot_date not in result:
            result[snapshot.snapshot_date] = []
        result[snapshot.snapshot_date].append(snapshot)

    return result


def count_today_snapshots(db: Session, snapshot_date: date) -> int:
    """统计今日快照数量"""
    return db.query(models.StockSnapshot).filter(
        models.StockSnapshot.snapshot_date == snapshot_date
    ).count()


def get_all_snapshot_dates(db: Session) -> List[date]:
    """获取所有有快照的日期列表（降序）"""
    from sqlalchemy import distinct
    dates = db.query(distinct(models.StockSnapshot.snapshot_date)).order_by(
        models.StockSnapshot.snapshot_date.desc()
    ).all()
    return [d[0] for d in dates]


def get_adjacent_snapshot_dates(db: Session, current_date: date) -> Dict[str, Optional[date]]:
    """获取指定日期的前后相邻快照日期"""
    # 获取前一个日期
    prev_snapshot = db.query(models.StockSnapshot).filter(
        models.StockSnapshot.snapshot_date < current_date
    ).order_by(models.StockSnapshot.snapshot_date.desc()).first()

    # 获取后一个日期
    next_snapshot = db.query(models.StockSnapshot).filter(
        models.StockSnapshot.snapshot_date > current_date
    ).order_by(models.StockSnapshot.snapshot_date.asc()).first()

    return {
        "prev": prev_snapshot.snapshot_date if prev_snapshot else None,
        "next": next_snapshot.snapshot_date if next_snapshot else None
    }


# --- 交易日历相关操作 ---

def get_trading_calendar_by_date(db: Session, trade_date: date) -> Optional[models.TradingCalendar]:
    """获取指定日期的交易日历记录"""
    return db.query(models.TradingCalendar).filter(
        models.TradingCalendar.trade_date == trade_date
    ).first()


def get_trading_calendar_by_year(db: Session, year: int) -> List[models.TradingCalendar]:
    """获取指定年份的所有交易日历记录"""
    return db.query(models.TradingCalendar).filter(
        models.TradingCalendar.year == year
    ).all()


def is_year_cached(db: Session, year: int) -> bool:
    """检查指定年份的交易日历是否已缓存"""
    try:
        count = db.query(models.TradingCalendar).filter(
            models.TradingCalendar.year == year
        ).count()
        return count is not None and count > 0
    except Exception:
        return False


def batch_create_trading_calendar(db: Session, calendar_data: List[Dict]) -> int:
    """批量创建交易日历记录"""
    created_count = 0
    for item in calendar_data:
        # 检查是否已存在
        existing = get_trading_calendar_by_date(db, item["trade_date"])
        if existing:
            # 更新现有记录
            existing.is_trading_day = item["is_trading_day"]
        else:
            # 创建新记录
            db_calendar = models.TradingCalendar(
                trade_date=item["trade_date"],
                is_trading_day=item["is_trading_day"],
                year=item["trade_date"].year
            )
            db.add(db_calendar)
            created_count += 1
    db.commit()
    return created_count


def delete_trading_calendar_by_year(db: Session, year: int) -> int:
    """删除指定年份的交易日历缓存"""
    count = db.query(models.TradingCalendar).filter(
        models.TradingCalendar.year == year
    ).delete()
    db.commit()
    return count
