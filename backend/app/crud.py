"""数据库CRUD操作"""
from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional


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
