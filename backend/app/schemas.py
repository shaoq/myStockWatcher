"""Pydantic模式定义,用于API请求和响应验证"""
from pydantic import BaseModel, Field
from datetime import datetime
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
