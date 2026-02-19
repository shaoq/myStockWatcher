## MODIFIED Requirements

### Requirement: Flexible Date Format Parsing

The system SHALL support multiple date formats when parsing trading calendar data.

#### Scenario: Parse date with hyphen format
- **WHEN** date string is in format "2026-01-05"
- **THEN** the system MUST successfully parse it to a date object

#### Scenario: Parse date with no separator format
- **WHEN** date string is in format "20260105"
- **THEN** the system MUST successfully parse it to a date object

#### Scenario: Parse date with slash format
- **WHEN** date string is in format "2026/01/05"
- **THEN** the system MUST successfully parse it to a date object

#### Scenario: Invalid date format
- **WHEN** date string cannot be parsed by any supported format
- **THEN** the system MUST return None and log a warning
- **AND** the system MUST continue processing other dates

### Requirement: Multi-Layer Data Source Fallback

The system SHALL implement a 3-layer fallback mechanism for trading calendar data retrieval.

#### Scenario: Primary source succeeds
- **WHEN** AkShare API returns valid data
- **THEN** the system MUST use AkShare data as the primary source
- **AND** the system MUST NOT call backup sources

#### Scenario: Primary source fails, backup succeeds
- **WHEN** AkShare API fails or returns invalid data
- **AND** exchange_calendars library is available
- **THEN** the system MUST use exchange_calendars as backup source

#### Scenario: All external sources fail
- **WHEN** both AkShare and exchange_calendars are unavailable
- **THEN** the system MUST fallback to basic weekend detection
- **AND** the system MUST return a valid trading day judgment
- **AND** the system MUST log the fallback event
