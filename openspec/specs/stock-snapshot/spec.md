# stock-snapshot Specification

## Purpose
TBD - created by archiving change daily-report. Update Purpose after archive.
## Requirements
### Requirement: Snapshot Storage

The system SHALL store daily snapshots of stock indicator states for historical comparison.

#### Scenario: Create snapshot for a stock

- **WHEN** user requests to generate snapshots
- **THEN** the system MUST save current price and MA results for each monitored stock
- **AND** the snapshot date MUST be set to the current date
- **AND** each stock MUST have at most one snapshot per date

#### Scenario: Prevent duplicate snapshots

- **WHEN** a snapshot already exists for a stock on the current date
- **THEN** the system MUST update the existing snapshot instead of creating a duplicate

### Requirement: Snapshot Data Structure

Each snapshot SHALL contain the following information:

#### Scenario: Snapshot contains complete indicator data

- **WHEN** a snapshot is created
- **THEN** it MUST include the stock ID, snapshot date, current price
- **AND** it MUST include MA results as JSON (containing ma_price, reached_target, price_difference, price_difference_percent for each MA type)

### Requirement: Check Today's Snapshot

The system SHALL provide an API to check if snapshots exist for the current date.

#### Scenario: Check snapshot existence

- **WHEN** user checks for today's snapshots
- **THEN** the system MUST return whether snapshots exist for all monitored stocks
- **AND** the system MUST return the count of stocks with snapshots

