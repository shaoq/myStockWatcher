## ADDED Requirements

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
