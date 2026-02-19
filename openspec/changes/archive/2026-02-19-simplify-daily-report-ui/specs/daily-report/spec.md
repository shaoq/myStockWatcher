## REMOVED Requirements

### Requirement: Trend Data

**Reason**: 趋势图表使用频率低，增加页面复杂度和API调用开销。核心关注点是当日达标/未达标个股列表。

**Migration**: 移除 `/reports/trend` API 端点，前端移除 `getTrendData()` API 调用和 `renderTrendChart()` 渲染函数。

### Requirement: Report Page (部分移除)

**Reason**: 概览统计卡片和达标率卡片使用频率低，达标/未达标数量在列表卡片标题中已显示（如"达标个股 (12只)"）。

**Migration**: 前端移除概览卡片和达标率卡片的渲染代码。后端 summary 计算保持不变（API响应兼容性）。

#### 移除的场景:
- "View daily report page" 中关于 summary section 和 trend chart 的展示要求

## ADDED Requirements

### Requirement: Simplified Report Page Layout

The frontend SHALL display a simplified daily report page with only reached/below stocks lists.

#### Scenario: View simplified daily report page

- **WHEN** user navigates to the daily report page
- **THEN** the system MUST display only the reached stocks list
- **AND** the system MUST display only the below stocks list
- **AND** the system MUST NOT display summary statistics cards
- **AND** the system MUST NOT display reached rate cards
- **AND** the system MUST NOT display trend chart visualization

#### Scenario: Stock count in card header

- **WHEN** the daily report page renders reached/below stocks cards
- **THEN** each card header MUST display the count of stocks (e.g., "达标个股 (12只)")
- **AND** users can see the total count without summary cards
