# Daily Report Specification

## ADDED Requirements

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

### Requirement: Trend Data

The system SHALL provide trend data for visualization over a configurable number of days.

#### Scenario: Get trend data for N days

- **WHEN** user requests trend data
- **THEN** the system MUST return daily statistics for the specified number of days
- **AND** the data MUST include date labels and corresponding values for chart rendering

### Requirement: Report Page

The frontend SHALL provide a dedicated page for viewing daily reports.

#### Scenario: View daily report page

- **WHEN** user navigates to the daily report page
- **THEN** the system MUST display the summary section with key metrics
- **AND** the system MUST display the status change list
- **AND** the system MUST display a trend chart visualization
