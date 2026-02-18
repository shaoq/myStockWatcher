"""Pydantic模式定义,用于API请求和响应验证"""
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Dict


class MAResult(BaseModel):
    """单个指标的计算结果"""
    ma_price: Optional[float] = Field(None, description="计算出的均线价格")
    reached_target: bool = Field(False, description="是否达到均线价格")
    price_difference: Optional[float] = Field(None, description="与均线价格的差额")
    price_difference_percent: Optional[float] = Field(None, description="与均线价格的差额百分比")


class StockBase(BaseModel):
    """股票基础模式"""
    symbol: str = Field(..., description="股票代码", example="AAPL")
    name: Optional[str] = Field(None, description="股票名称", example="苹果公司")
    ma_types: List[str] = Field(["MA5"], description="预警指标类型列表", example=["MA5", "MA20"])
    group_ids: List[int] = Field([], description="所属分组ID列表")


class StockCreate(StockBase):
    """创建股票的请求模式"""
    pass


class StockUpdate(BaseModel):
    """更新股票的请求模式"""
    name: Optional[str] = Field(None, description="股票名称")
    ma_types: Optional[List[str]] = Field(None, description="预警指标类型列表")
    group_ids: Optional[List[int]] = Field(None, description="所属分组ID列表")


class StockInDB(StockBase):
    """数据库中的股票模式"""
    id: int
    current_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GroupBase(BaseModel):
    """分组基础模式"""
    name: str = Field(..., description="分组名称", example="科技股")


class GroupCreate(GroupBase):
    """创建分组的请求模式"""
    pass


class GroupInDB(GroupBase):
    """数据库中的分组模式"""
    id: int
    stock_count: int = Field(0, description="分组内股票数量")

    class Config:
        from_attributes = True


class GroupWithStocks(GroupInDB):
    """包含股票列表的分组模式"""
    stocks: List[StockInDB] = []


class StockWithStatus(StockInDB):
    """带有价格状态的股票模式"""
    ma_results: Dict[str, MAResult] = Field({}, description="各指标的计算结果")
    # 保留以下字段以兼容旧前端或作为主要指标汇总（可选）
    ma_price: Optional[float] = Field(None, description="首个指标的均线价格")
    reached_target: bool = Field(False, description="首个指标是否达到均线价格")
    price_difference: Optional[float] = Field(None, description="首个指标的差额")
    price_difference_percent: Optional[float] = Field(None, description="首个指标的差额百分比")
    group_names: List[str] = Field([], description="所属分组名称列表")
    group_ids: List[int] = Field([], description="所属分组ID列表")
    is_realtime: bool = Field(False, description="数据是否为实时获取（非缓存）")


class PriceUpdateResponse(BaseModel):
    """价格更新响应"""
    symbol: str
    current_price: float
    ma_results: Dict[str, MAResult]
    message: str
    is_realtime: bool = Field(False, description="数据是否为实时获取")


# ============ 快照相关模式 ============

class StockSnapshotBase(BaseModel):
    """股票快照基础模式"""
    stock_id: int = Field(..., description="股票ID")
    snapshot_date: date = Field(..., description="快照日期")
    price: Optional[float] = Field(None, description="当日价格")
    ma_results: Dict[str, MAResult] = Field({}, description="MA指标结果")


class StockSnapshotCreate(StockSnapshotBase):
    """创建快照的请求模式"""
    pass


class StockSnapshotInDB(StockSnapshotBase):
    """数据库中的快照模式"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 报告相关模式 ============

class StockChangeItem(BaseModel):
    """股票变化项"""
    stock_id: int
    symbol: str
    name: str
    ma_type: str = Field(..., description="发生变化的MA类型")
    current_price: float
    ma_price: float
    price_difference_percent: float


class DailyReportSummary(BaseModel):
    """每日报告摘要"""
    total_stocks: int = Field(..., description="监控股票总数")
    reached_count: int = Field(..., description="达标股票数")
    newly_reached: int = Field(..., description="新增达标数")
    newly_below: int = Field(..., description="跌破均线数")
    reached_rate: float = Field(..., description="达标率(%)")
    reached_rate_change: float = Field(..., description="达标率变化(百分点)")


class ReachedIndicator(BaseModel):
    """单个达标指标"""
    ma_type: str = Field(..., description="MA类型，如MA5、MA20")
    ma_price: float = Field(..., description="均线价格")
    price_difference_percent: float = Field(..., description="偏离百分比")


class ReachedStockItem(BaseModel):
    """达标股票项（聚合多个达标指标）"""
    stock_id: int = Field(..., description="股票ID")
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    current_price: float = Field(..., description="当前价格")
    max_deviation_percent: float = Field(..., description="最大偏离百分比")
    reached_indicators: List[ReachedIndicator] = Field(default_factory=list, description="所有达标的指标列表")


class DailyReportResponse(BaseModel):
    """每日报告响应"""
    report_date: date = Field(..., description="报告日期")
    has_yesterday: bool = Field(..., description="是否有昨日数据")
    summary: DailyReportSummary
    newly_reached: List[StockChangeItem] = Field(default_factory=list, description="新增达标的股票")
    newly_below: List[StockChangeItem] = Field(default_factory=list, description="跌破均线的股票")
    reached_stocks: List[ReachedStockItem] = Field(default_factory=list, description="今日达标个股列表（分页）")
    total_reached: int = Field(0, description="达标个股总数")


class TrendDataPoint(BaseModel):
    """趋势数据点"""
    date: str = Field(..., description="日期标签")
    reached_count: int = Field(..., description="达标数")
    reached_rate: float = Field(..., description="达标率(%)")


class TrendDataResponse(BaseModel):
    """趋势数据响应"""
    data: List[TrendDataPoint] = Field(default_factory=list, description="趋势数据点列表")


class SnapshotCheckResponse(BaseModel):
    """快照检查响应"""
    has_snapshots: bool = Field(..., description="今日是否有快照")
    snapshot_count: int = Field(..., description="快照数量")
    total_stocks: int = Field(..., description="监控股票总数")
    snapshot_date: Optional[date] = Field(None, description="快照日期")


class GenerateSnapshotsResponse(BaseModel):
    """生成快照响应"""
    message: str
    created_count: int = Field(..., description="新建快照数")
    updated_count: int = Field(..., description="更新快照数")
