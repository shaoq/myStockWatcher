# daily-report Specification

## Purpose
每日报告功能：展示股票指标变化和趋势，支持查看历史报告和交易日判断。

## Requirements

### Requirement: Daily Summary Report

The system SHALL generate a daily report summarizing indicator status changes.

#### Scenario: Generate daily report

- **WHEN** user requests the daily report
- **THEN** the system MUST return summary statistics including total stocks, reached count, newly reached count, and newly below count
- **AND** the system MUST calculate reached rate and its change compared to the previous trading day

### Requirement: Status Change Detection

The system SHALL detect stocks whose indicator status changed compared to the previous day.

#### Scenario: Identify newly reached stocks

- **WHEN** a stock was below MA yesterday and is at or above MA today
- **THEN** the system MUST include it in the "newly reached" list
- **AND** the report MUST show which MA type(s) changed status

#### Scenario: Identify newly below stocks

- **WHEN** a stock was at or above MA yesterday and is below MA today
- **THEN** the system MUST include it in the "newly below" list
- **AND** the report MUST show which MA type(s) changed status

### Requirement: Daily report API response structure

The `/reports/daily` API SHALL return reached stocks data with pagination support.

#### Scenario: API returns reached stocks with pagination
- **WHEN** client requests `/reports/daily?page=1&page_size=10`
- **THEN** API returns response containing:
  - `reached_stocks`: array of paginated reached stock items
  - `total_reached`: total count of reached stocks
- **AND** each reached stock item contains:
  - `stock_id`: integer
  - `symbol`: string
  - `name`: string
  - `current_price`: float
  - `max_deviation_percent`: float
  - `reached_indicators`: array of {ma_type, ma_price, price_difference_percent}

#### Scenario: Default pagination when parameters omitted
- **WHEN** client requests `/reports/daily` without page parameters
- **THEN** API returns first page with default page_size of 10

#### Scenario: Pagination boundary enforcement
- **WHEN** client requests page_size greater than 50
- **THEN** API limits page_size to 50 maximum

### Requirement: ReachedStockItem data schema

The system SHALL define a structured schema for reached stock items in API responses.

#### Scenario: ReachedStockItem structure
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
        "price_difference_percent": float
      }
    ]
  }
  ```

### Requirement: Backend aggregation logic

The system SHALL aggregate multiple reached indicators per stock and calculate max deviation.

#### Scenario: Aggregate indicators for single stock
- **WHEN** processing snapshots for daily report
- **THEN** system groups all reached indicators by stock_id
- **AND** calculates max_deviation_percent from all reached indicators
- **AND** sorts stocks by max_deviation_percent descending

#### Scenario: Filter only reached indicators
- **WHEN** aggregating indicators for a stock
- **THEN** system only includes indicators where reached_target is true
- **AND** excludes indicators where reached_target is false

### Requirement: Trading Day Validation

The system SHALL validate if the requested date is a trading day before generating a report.

#### Scenario: Reject non-trading day report request

- **WHEN** user requests a report for a non-trading day
- **THEN** the system MUST return `{ "error": "该日期为非交易日", "is_trading_day": false, "reason": "周末/节假日" }`

#### Scenario: Show market status in UI

- **WHEN** user selects a non-trading day in the date picker
- **THEN** the system MUST display "休市" status
- **AND** the system MUST disable the "生成报告" button

### Requirement: Smart Report Generation

The system SHALL intelligently determine the appropriate action based on trading day status.

#### Scenario: Trading day with existing snapshots

- **WHEN** user requests report for a trading day that already has snapshots
- **THEN** the system MUST return the existing report directly

#### Scenario: Trading day without snapshots

- **WHEN** user requests report for a trading day without snapshots
- **THEN** the system MUST prompt "该日期暂无数据，是否生成？"
- **AND** the system MUST offer a "生成报告" option

#### Scenario: Auto-generate for today

- **WHEN** user visits the daily report page on a trading day
- **AND** today's snapshots do not exist
- **THEN** the system MUST show a prompt to generate today's report

### Requirement: Calendar Date Report Indicator

The date picker calendar SHALL display a visual indicator on dates that have existing report data.

#### Scenario: Display indicator for dates with reports
- **WHEN** user opens the date picker calendar in the daily report page
- **THEN** the system MUST display a green dot indicator on dates that have report data
- **AND** dates without reports MUST display normally without any indicator

#### Scenario: Indicator visibility
- **WHEN** rendering a calendar date cell
- **THEN** the indicator MUST be visible as a small green circle (6px diameter)
- **AND** the indicator MUST be positioned at the top-right corner of the date cell
- **AND** the indicator MUST NOT obscure the date number

#### Scenario: Data source for indicator
- **WHEN** determining which dates should show the indicator
- **THEN** the system MUST use the existing `availableDates` data
- **AND** no additional API requests SHALL be required

### Requirement: MA Grouped Change List Display

The frontend SHALL display status change lists (newly reached and newly below) grouped by MA indicator type.

#### Scenario: Display changes grouped by MA type
- **WHEN** the daily report page renders the "newly reached" or "newly below" section
- **THEN** the system MUST group items by their `ma_type` field
- **AND** each group MUST display as a collapsible panel
- **AND** the group header MUST show the MA type and count (e.g., "MA5 (3只)")

#### Scenario: Sort MA groups by numeric value
- **WHEN** rendering grouped change lists
- **THEN** the system MUST sort groups by the numeric value in MA type (MA5 → MA10 → MA20 → MA60)
- **AND** groups MUST display in ascending order

#### Scenario: Sort items within group by deviation
- **WHEN** rendering items within an MA group
- **THEN** the system MUST sort items by `price_difference_percent` in descending order (largest deviation first)

#### Scenario: Hide empty MA groups
- **WHEN** an MA type has no items in the change list
- **THEN** the system MUST NOT display that MA group

#### Scenario: Collapse panel interaction
- **WHEN** user clicks on an MA group panel header
- **THEN** the panel MUST toggle between expanded and collapsed states
- **AND** the expanded state MUST show all items in that group
- **AND** the collapsed state MUST show only the group header

### Requirement: All Below Stocks Display

The system SHALL display all stocks that are currently below their MA indicators, not just those with status changes.

#### Scenario: Display all below stocks with classification
- **WHEN** user views the daily report "below MA" section
- **THEN** the system MUST display all stocks where `reached_target` is false
- **AND** each stock MUST be classified with a `fall_type` field
- **AND** `fall_type` MUST be either `"new_fall"` or `"continuous_below"`

#### Scenario: Classify new fall stocks
- **WHEN** a stock was at or above MA yesterday AND is below MA today
- **THEN** the system MUST set `fall_type` to `"new_fall"`

#### Scenario: Classify continuous below stocks
- **WHEN** a stock was below MA yesterday AND is below MA today
- **THEN** the system MUST set `fall_type` to `"continuous_below"`
- **AND** if yesterday's snapshot does not exist, the system MUST default to `"continuous_below"`

### Requirement: Below Stocks API Response Structure

The `/reports/daily` API SHALL return all below stocks with classification information.

#### Scenario: API returns all_below_stocks array
- **WHEN** client requests `/reports/daily`
- **THEN** API returns response containing:
  - `all_below_stocks`: array of all below stock items
  - `summary.continuous_below_count`: count of continuous below stocks
- **AND** each below stock item contains:
  - `stock_id`: integer
  - `symbol`: string
  - `name`: string
  - `current_price`: float
  - `ma_type`: string
  - `ma_price`: float
  - `price_difference_percent`: float
  - `fall_type`: "new_fall" | "continuous_below"

#### Scenario: Backward compatibility with newly_below
- **WHEN** client requests `/reports/daily`
- **THEN** API MUST still return the existing `newly_below` array for backward compatibility
- **AND** `newly_below` content MUST remain unchanged (only status change stocks)

### Requirement: Grouped Below Stocks Display

The frontend SHALL display below stocks grouped by MA type and fall type.

#### Scenario: Display below stocks grouped by MA type
- **WHEN** the daily report page renders the "below MA" section
- **THEN** the system MUST group items by their `ma_type` field
- **AND** within each MA group, items MUST be sub-grouped by `fall_type`
- **AND** "new_fall" items MUST display before "continuous_below" items

#### Scenario: Visual distinction for fall types
- **WHEN** rendering below stock items
- **THEN** "new_fall" items MUST display with a red indicator (🔴)
- **AND** "continuous_below" items MUST display with a yellow indicator (🟡)
- **AND** each sub-group MUST show a count label

#### Scenario: Sort below stocks by deviation
- **WHEN** rendering below stock items within a sub-group
- **THEN** the system MUST sort items by `price_difference_percent` in ascending order (most negative first)

### Requirement: Summary Statistics Enhancement

The daily report summary SHALL include continuous below count.

#### Scenario: Display continuous below count
- **WHEN** user views the daily report summary
- **THEN** the system MUST display `continuous_below_count` in addition to existing statistics
- **AND** the "跌破均线" card MUST show total below count (newly_below + continuous_below)

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

### Requirement: Stock Chart Modal in Daily Report

The system SHALL allow users to view stock charts by clicking on stock items in the daily report.

#### Scenario: Click stock to view chart

- **WHEN** user clicks on a stock symbol or name in the reached/below stocks list
- **THEN** the system MUST display a modal showing the stock's chart
- **AND** the modal MUST include the stock symbol and name in the title
- **AND** the modal MUST be dismissible by clicking outside or the close button

#### Scenario: Chart display content

- **WHEN** the chart modal is displayed
- **THEN** the system MUST show tabs for different chart types (分时图, 日K线, 周K线, 月K线)
- **AND** the default active tab MUST be "日K线"
- **AND** the chart images MUST be fetched from the backend API

#### Scenario: Chart interaction consistency

- **WHEN** user interacts with the chart modal in daily report page
- **THEN** the behavior MUST be identical to the chart modal in stock list page
- **AND** the same StockChart component MUST be used

### Requirement: Clickable Stock Items

The stock items in the daily report list SHALL be clickable to show charts.

#### Scenario: Visual feedback on hover

- **WHEN** user hovers over a stock symbol or name
- **THEN** the cursor MUST change to pointer (hand) cursor
- **AND** the text MUST indicate it is clickable

#### Scenario: Click handler

- **WHEN** user clicks on stock symbol or name
- **THEN** the system MUST call showChartModal function with the stock's symbol and name
- **AND** the chart modal MUST open
