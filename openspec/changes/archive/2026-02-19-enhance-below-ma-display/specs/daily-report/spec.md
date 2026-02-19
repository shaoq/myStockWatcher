## ADDED Requirements

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
