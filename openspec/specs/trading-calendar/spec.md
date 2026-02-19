## ADDED Requirements

### Requirement: Trading Day Check

The system SHALL provide an API to check if a given date is a trading day.

#### Scenario: Check trading day

- **WHEN** user requests `GET /trading-calendar/check?date=2024-02-18`
- **THEN** the system MUST return `{ "date": "2024-02-18", "is_trading_day": true }`

#### Scenario: Check non-trading day (weekend)

- **WHEN** user requests `GET /trading-calendar/check?date=2024-02-17` (Saturday)
- **THEN** the system MUST return `{ "date": "2024-02-17", "is_trading_day": false, "reason": "周末" }`

#### Scenario: Check non-trading day (holiday)

- **WHEN** user requests `GET /trading-calendar/check?date=2024-02-10` (Spring Festival)
- **THEN** the system MUST return `{ "date": "2024-02-10", "is_trading_day": false, "reason": "节假日" }`

### Requirement: Trading Calendar Cache

The system SHALL cache trading calendar data to minimize external API calls.

#### Scenario: Cache miss triggers API call

- **WHEN** the system receives a date query for a year not in cache
- **THEN** the system MUST fetch trading calendar for that year from AkShare API
- **AND** the system MUST store the data in the database

#### Scenario: Cache hit returns cached data

- **WHEN** the system receives a date query for a year already in cache
- **THEN** the system MUST return the cached data without calling external API

### Requirement: Trading Calendar Refresh

The system SHALL provide an API to manually refresh the trading calendar cache.

#### Scenario: Manual refresh

- **WHEN** admin requests `POST /trading-calendar/refresh?year=2024`
- **THEN** the system MUST clear the cache for that year
- **AND** the system MUST fetch fresh data from AkShare API
