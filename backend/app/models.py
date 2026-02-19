"""数据库模型定义"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Table, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


# 股票与分组的多对多关联表
stock_group_association = Table(
    "stock_group_association",
    Base.metadata,
    Column("stock_id", Integer, ForeignKey("stocks.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
)


class Group(Base):
    """股票分组模型"""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, comment="分组名称")

    # 建立与股票的多对多关系
    stocks = relationship("Stock", secondary=stock_group_association, back_populates="groups")

    def __repr__(self):
        return f"<Group {self.name}>"


class Stock(Base):
    """股票信息模型"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False, comment="股票代码")
    name = Column(String, nullable=False, comment="股票名称")
    ma_types = Column(String, nullable=False, default="MA5", comment="移动平均线类型(逗号分隔，如 MA5,MA20)")
    current_price = Column(Float, nullable=True, comment="当前价格")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 建立与分组的多对多关联
    groups = relationship("Group", secondary=stock_group_association, back_populates="stocks")

    def __repr__(self):
        return f"<Stock {self.symbol}: {self.name}>"


class StockSnapshot(Base):
    """股票快照模型 - 存储每日指标状态"""
    __tablename__ = "stock_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, comment="关联股票ID")
    snapshot_date = Column(Date, nullable=False, comment="快照日期")
    price = Column(Float, nullable=True, comment="当日价格")
    ma_results = Column(Text, nullable=True, comment="MA指标结果(JSON格式)")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 建立与股票的关联
    stock = relationship("Stock", backref="snapshots")

    def __repr__(self):
        return f"<StockSnapshot {self.stock_id}:{self.snapshot_date}>"


class TradingCalendar(Base):
    """交易日历缓存模型 - 存储中国A股交易日历"""
    __tablename__ = "trading_calendar"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, unique=True, nullable=False, index=True, comment="日期")
    is_trading_day = Column(Integer, nullable=False, default=0, comment="是否为交易日 (0:否, 1:是)")
    year = Column(Integer, index=True, comment="年份（用于批量查询缓存）")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        status = "交易日" if self.is_trading_day else "非交易日"
        return f"<TradingCalendar {self.trade_date}: {status}>"


class Signal(Base):
    """买卖信号模型 - 存储技术分析生成的信号"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, comment="关联股票ID")
    signal_date = Column(Date, nullable=False, index=True, comment="信号日期")
    signal_type = Column(String(10), nullable=False, comment="信号类型: buy/sell/hold")
    current_price = Column(Float, nullable=True, comment="当前价格")

    # 价位建议
    entry_price = Column(Float, nullable=True, comment="建议买入/卖出价位")
    stop_loss = Column(Float, nullable=True, comment="止损价位")
    take_profit = Column(Float, nullable=True, comment="目标价位")

    # 信号详情
    strength = Column(Integer, default=1, comment="信号强度 1-5")
    triggers = Column(Text, nullable=True, comment="触发条件列表(JSON)")
    indicators = Column(Text, nullable=True, comment="指标快照(JSON)")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 建立与股票的关联
    stock = relationship("Stock", backref="signals")

    def __repr__(self):
        return f"<Signal {self.stock_id}:{self.signal_date} [{self.signal_type}]>"


class TradingRule(Base):
    """交易规则配置模型 - 存储用户自定义的买卖规则"""
    __tablename__ = "trading_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="规则名称")
    rule_type = Column(String(10), nullable=False, comment="规则类型: buy/sell")
    enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级(越大越优先)")
    strength = Column(Integer, default=2, comment="信号强度1-5")

    # JSON 配置
    conditions = Column(Text, nullable=False, comment="触发条件(JSON)")
    price_config = Column(Text, nullable=False, comment="价位配置(JSON)")
    description_template = Column(String(500), comment="描述模板")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<TradingRule {self.id}: {self.name} [{self.rule_type}]>"
