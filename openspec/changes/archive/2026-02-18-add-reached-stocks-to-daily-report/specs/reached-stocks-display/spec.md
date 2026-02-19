## ADDED Requirements

### Requirement: Display reached stocks in daily report
The system SHALL display all stocks that reached their MA targets on the selected date, showing stock code, name, reached indicators, current price, and maximum deviation.

#### Scenario: Display reached stocks with pagination
- **WHEN** user views daily report page
- **THEN** system displays a table of reached stocks with pagination controls
- **AND** default page size is 10 items
- **AND** each row shows stock symbol, name, reached indicators as tags, current price, and max deviation percentage

#### Scenario: Multiple reached indicators aggregated per stock
- **WHEN** a stock has multiple MA indicators reached (e.g., MA5 and MA20)
- **THEN** system displays the stock in a single row
- **AND** all reached indicators are shown as tags
- **AND** max deviation percentage is the highest among all reached indicators

#### Scenario: Sort by deviation descending
- **WHEN** reached stocks list is displayed
- **THEN** stocks are sorted by max_deviation_percent in descending order
- **AND** stocks with higher deviation appear first

### Requirement: Pagination controls for reached stocks
The system SHALL provide pagination controls for navigating through reached stocks.

#### Scenario: Navigate between pages
- **WHEN** total reached stocks exceed page size
- **THEN** system displays pagination controls
- **AND** user can click page numbers or prev/next buttons
- **AND** current page is highlighted

#### Scenario: Display total count
- **WHEN** pagination is shown
- **THEN** system displays total number of reached stocks in header (e.g., "今日达标个股 (12只)")

### Requirement: Reached indicator display format
The system SHALL display reached indicators as visual tags with clear formatting.

#### Scenario: Tag display for reached indicators
- **WHEN** a stock has reached one or more MA indicators
- **THEN** each indicator is displayed as a colored tag (e.g., "MA5", "MA20")
- **AND** tags use success/green color to indicate positive status

### Requirement: Empty state handling
The system SHALL display appropriate message when no stocks reached targets.

#### Scenario: No reached stocks
- **WHEN** no stocks reached their MA targets on selected date
- **THEN** system displays empty state message "暂无达标个股"
- **AND** pagination controls are hidden
