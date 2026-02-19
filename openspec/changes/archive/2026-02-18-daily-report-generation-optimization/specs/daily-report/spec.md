## ADDED Requirements

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
