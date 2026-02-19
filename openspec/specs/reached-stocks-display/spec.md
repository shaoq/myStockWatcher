# reached-stocks-display Specification

## Purpose
今日达标个股展示功能：在每日报告页面展示当日所有达标股票的详细信息，采用分组卡片布局和状态分类。

## Requirements

### Requirement: Display reached stocks in daily report

The system SHALL display all stocks that reached their MA targets on the selected date in a grouped card layout with status classification.

#### Scenario: Display reached stocks grouped by MA type
- **WHEN** user views daily report page
- **THEN** system displays reached stocks in a card layout grouped by MA type
- **AND** each MA group displays as a collapsible panel
- **AND** each group shows count of reached stocks for that MA type

#### Scenario: Status classification within MA groups
- **WHEN** displaying reached stocks within an MA group
- **THEN** system classifies each indicator as either "new_reach" or "continuous_reach"
- **AND** "new_reach" indicators (昨日未达标 → 今日达标) display first with bright green color
- **AND** "continuous_reach" indicators (昨日达标 → 今日达标) display after with light green color
- **AND** each status category shows count (e.g., "🟢 新增达标 (3只)")

#### Scenario: Sort items within status category
- **WHEN** rendering items within a status category
- **THEN** system sorts by `price_difference_percent` in descending order (largest deviation first)

#### Scenario: Multiple reached indicators per stock
- **WHEN** a stock has multiple MA indicators reached
- **THEN** system displays each indicator as a separate item in its respective MA group
- **AND** each item shows the stock symbol, name, current price, MA price, and deviation percentage

### Requirement: Reached indicator display format

The system SHALL display reached indicators with color-coded status tags and reach type classification.

#### Scenario: Tag display for new reach
- **WHEN** an indicator status is "new_reach"
- **THEN** the tag uses bright green color (#52c41a, Ant Design "success")
- **AND** displays with 🟢 emoji indicator

#### Scenario: Tag display for continuous reach
- **WHEN** an indicator status is "continuous_reach"
- **THEN** the tag uses light green color (#b7eb8f)
- **AND** displays with 🟢 emoji indicator

#### Scenario: API returns reach_type field
- **WHEN** client requests `/reports/daily`
- **THEN** each item in `reached_indicators` array MUST include a `reach_type` field
- **AND** `reach_type` value is either "new_reach" or "continuous_reach"

### Requirement: Reach type classification in API response

The system SHALL provide reach type classification for each reached indicator in the API response.

#### Scenario: API includes reach_type field
- **WHEN** client requests `/reports/daily`
- **THEN** each item in `reached_indicators` array MUST include a `reach_type` field
- **AND** `reach_type` value is either "new_reach" or "continuous_reach"

#### Scenario: Classify as new_reach
- **WHEN** calculating reach_type for an indicator
- **AND** the indicator was NOT reached on the previous trading day
- **AND** the indicator IS reached on the current day
- **THEN** `reach_type` MUST be "new_reach"

#### Scenario: Classify as continuous_reach
- **WHEN** calculating reach_type for an indicator
- **AND** the indicator WAS reached on the previous trading day
- **AND** the indicator IS reached on the current day
- **THEN** `reach_type` MUST be "continuous_reach"

#### Scenario: Default to new_reach when no previous data
- **WHEN** calculating reach_type for an indicator
- **AND** no previous trading day snapshot exists
- **THEN** `reach_type` MUST be "new_reach"

### Requirement: ReachedStockItem data schema with reach_type

The system SHALL define an extended schema for reached stock items including reach_type.

#### Scenario: ReachedStockItem structure with reach_type
- **WHEN** API returns reached stock data
- **THEN** each item conforms to the following schema:
  ```
  {
    "stock_id": int,
    "symbol": str,
    "name": str,
    "current_price": float,
    "max_deviation_percent": float,
    "reached_indicators": [
      {
        "ma_type": str,
        "ma_price": float,
        "price_difference_percent": float,
        "reach_type": "new_reach" | "continuous_reach"
      }
    ]
  }
  ```

### Requirement: Empty state handling

The system SHALL display appropriate message when no stocks reached targets.

#### Scenario: No reached stocks
- **WHEN** no stocks reached their MA targets on selected date
- **THEN** system displays empty state message "暂无达标个股"
