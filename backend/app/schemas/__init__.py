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
    data_fetched_at: Optional[datetime] = Field(None, description="数据获取时间")
    signal: Optional["SignalBase"] = Field(None, description="最新买卖信号")


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
    newly_below: int = Field(..., description="跌破均线数(新跌破)")
    continuous_below: int = Field(0, description="持续未达标数")
    reached_rate: float = Field(..., description="达标率(%)")
    reached_rate_change: float = Field(..., description="达标率变化(百分点)")


class ReachedIndicator(BaseModel):
    """单个达标指标"""
    ma_type: str = Field(..., description="MA类型，如MA5、MA20")
    ma_price: float = Field(..., description="均线价格")
    price_difference_percent: float = Field(..., description="偏离百分比")
    reach_type: str = Field(..., description="达标类型：new_reach(新增达标) 或 continuous_reach(持续达标)")


class BelowStockItem(BaseModel):
    """未达标股票项（包含跌破类型分类）"""
    stock_id: int = Field(..., description="股票ID")
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    current_price: float = Field(..., description="当前价格")
    ma_type: str = Field(..., description="MA类型，如MA5、MA20")
    ma_price: float = Field(..., description="均线价格")
    price_difference_percent: float = Field(..., description="偏离百分比")
    fall_type: str = Field(..., description="跌破类型: new_fall(新跌破) 或 continuous_below(持续未达标)")


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
    newly_below: List[StockChangeItem] = Field(default_factory=list, description="跌破均线的股票(仅状态变化)")
    all_below_stocks: List[BelowStockItem] = Field(default_factory=list, description="所有未达标股票(含分类)")
    reached_stocks: List[ReachedStockItem] = Field(default_factory=list, description="今日达标个股列表（分页）")
    total_reached: int = Field(0, description="达标个股总数")


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


# ============ 批量归属分组相关模式 ============

class BatchAssignGroupsRequest(BaseModel):
    """批量归属分组请求"""
    stock_ids: List[int] = Field(..., description="股票ID列表")
    group_names: List[str] = Field(..., description="分组名称列表（不存在则自动创建）")


class BatchAssignGroupsResponse(BaseModel):
    """批量归属分组响应"""
    success: bool = Field(..., description="操作是否成功")
    assigned_count: int = Field(..., description="成功归属的股票数")
    skipped_count: int = Field(0, description="已在分组内跳过的股票数")
    created_groups: List[str] = Field(default_factory=list, description="新创建的分组名")
    message: str = Field(..., description="操作结果消息")


# ============ 买卖信号相关模式 ============

class SignalBase(BaseModel):
    """买卖信号基础模式"""
    signal_type: str = Field(..., description="信号类型: buy/sell/hold")
    current_price: Optional[float] = Field(None, description="当前价格")
    entry_price: Optional[float] = Field(None, description="建议买入/卖出价位")
    stop_loss: Optional[float] = Field(None, description="止损价位")
    take_profit: Optional[float] = Field(None, description="目标价位")
    strength: int = Field(0, ge=0, le=5, description="信号强度 0-5（0=持有观望）")
    triggers: List[str] = Field(default_factory=list, description="触发条件列表")
    indicators: Dict = Field(default_factory=dict, description="指标快照")


class SignalInDB(SignalBase):
    """数据库中的信号模式"""
    id: int
    stock_id: int
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    signal_date: date
    created_at: Optional[datetime] = Field(None, description="创建时间")

    class Config:
        from_attributes = True


class SignalResponse(SignalInDB):
    """信号响应模式（包含股票信息）"""
    pass


class SignalGenerateRequest(BaseModel):
    """生成信号请求"""
    stock_ids: Optional[List[int]] = Field(None, description="指定股票ID列表，为空则生成所有")
    target_date: Optional[date] = Field(None, description="目标日期，默认今天")


class SignalGenerateResponse(BaseModel):
    """生成信号响应"""
    message: str
    generated_count: int = Field(..., description="生成的信号数量")
    signals: List[SignalResponse] = Field(default_factory=list, description="生成的信号列表")


# 解决前向引用
StockWithStatus.model_rebuild()


# ============ 交易规则配置相关模式 ============

class ConditionConfig(BaseModel):
    """单个触发条件配置"""
    indicator: str = Field(..., description="指标类型: MA/MACD/RSI/KDJ/Bollinger")
    field: str = Field(..., description="字段名，如 MA5, RSI, DIF 等")
    operator: str = Field(..., description="操作符: gt/lt/gte/lte/eq/cross_above/cross_below/below_threshold/above_threshold")
    target_type: str = Field(..., description="目标类型: indicator/value")
    target_indicator: Optional[str] = Field(None, description="目标指标类型（当 target_type=indicator 时）")
    target_field: Optional[str] = Field(None, description="目标字段名（当 target_type=indicator 时）")
    target_value: Optional[float] = Field(None, description="目标值（当 target_type=value 时）")


class PriceEntryConfig(BaseModel):
    """入场价配置"""
    type: str = Field(..., description="类型: indicator/percentage/current")
    indicator: Optional[str] = Field(None, description="指标类型（当 type=indicator 时）")
    field: Optional[str] = Field(None, description="字段名（当 type=indicator 时）")
    value: Optional[float] = Field(None, description="百分比值（当 type=percentage 时）")


class PriceExitConfig(BaseModel):
    """止损/止盈价配置"""
    type: str = Field(..., description="类型: indicator/percentage")
    base: Optional[str] = Field(None, description="基准: entry/current（当 type=percentage 时）")
    value: Optional[float] = Field(None, description="百分比值（当 type=percentage 时）")
    indicator: Optional[str] = Field(None, description="指标类型（当 type=indicator 时）")
    field: Optional[str] = Field(None, description="字段名（当 type=indicator 时）")


class PriceConfig(BaseModel):
    """价位配置"""
    entry: PriceEntryConfig = Field(..., description="入场价配置")
    stop_loss: Optional[PriceExitConfig] = Field(None, description="止损价配置")
    take_profit: Optional[PriceExitConfig] = Field(None, description="止盈价配置")


class TradingRuleBase(BaseModel):
    """交易规则基础模式"""
    name: str = Field(..., description="规则名称", max_length=100)
    rule_type: str = Field(..., description="规则类型: buy/sell")
    enabled: bool = Field(True, description="是否启用")
    priority: int = Field(0, ge=0, description="优先级(越大越优先)")
    strength: int = Field(2, ge=1, le=5, description="信号强度1-5")
    conditions: List[ConditionConfig] = Field(..., description="触发条件列表")
    price_config: PriceConfig = Field(..., description="价位配置")
    description_template: Optional[str] = Field(None, description="描述模板", max_length=500)


class TradingRuleCreate(TradingRuleBase):
    """创建交易规则的请求模式"""
    pass


class TradingRuleUpdate(BaseModel):
    """更新交易规则的请求模式"""
    name: Optional[str] = Field(None, description="规则名称", max_length=100)
    rule_type: Optional[str] = Field(None, description="规则类型: buy/sell")
    enabled: Optional[bool] = Field(None, description="是否启用")
    priority: Optional[int] = Field(None, ge=0, description="优先级(越大越优先)")
    strength: Optional[int] = Field(None, ge=1, le=5, description="信号强度1-5")
    conditions: Optional[List[ConditionConfig]] = Field(None, description="触发条件列表")
    price_config: Optional[PriceConfig] = Field(None, description="价位配置")
    description_template: Optional[str] = Field(None, description="描述模板", max_length=500)


class TradingRuleInDB(TradingRuleBase):
    """数据库中的交易规则模式"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TradingRuleResponse(TradingRuleInDB):
    """交易规则响应模式"""
    pass


class RecalculateSignalsRequest(BaseModel):
    """重新计算信号请求"""
    stock_ids: Optional[List[int]] = Field(None, description="指定股票ID列表，为空则重算所有")
    target_date: Optional[date] = Field(None, description="目标日期，默认今天")


class RecalculateSignalsResponse(BaseModel):
    """重新计算信号响应"""
    message: str
    total_stocks: int = Field(..., description="处理的股票总数")
    success_count: int = Field(..., description="成功生成信号的股票数")
    error_count: int = Field(0, description="处理失败的股票数")
