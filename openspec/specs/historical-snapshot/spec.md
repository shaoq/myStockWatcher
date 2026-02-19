## ADDED Requirements

### Requirement: Historical Snapshot Generation

The system SHALL allow users to generate snapshots for historical trading days.

#### Scenario: Generate snapshot for historical date

- **WHEN** user requests `POST /snapshots/generate?date=2024-02-01`
- **AND** 2024-02-01 is a trading day
- **THEN** the system MUST fetch K-line data for that date
- **AND** the system MUST create snapshots using the closing price

#### Scenario: Reject non-trading day

- **WHEN** user requests `POST /snapshots/generate?date=2024-02-10` (holiday)
- **THEN** the system MUST return an error `{ "error": "该日期为非交易日", "is_trading_day": false }`

#### Scenario: Skip existing snapshots

- **WHEN** user requests snapshot generation for a date that already has snapshots
- **THEN** the system MUST skip creating duplicate snapshots
- **AND** the system MUST return `{ "message": "该日期已有快照", "skipped": true }`

### Requirement: Historical Data Source

The system SHALL use K-line closing price for historical snapshot data.

#### Scenario: Use closing price for historical data

- **WHEN** generating a snapshot for a historical date (not today)
- **THEN** the system MUST fetch the closing price from K-line API
- **AND** the system MUST calculate MA values using historical K-line data

#### Scenario: Mark data source

- **WHEN** returning historical snapshot data
- **THEN** the system MUST include `"data_source": "kline_close"` to indicate the data origin
