## ADDED Requirements

### Requirement: DatePicker Future Date Restriction

The system SHALL prevent users from selecting future dates in the daily report date picker.

#### Scenario: Future date is disabled
- **WHEN** user opens the date picker
- **THEN** dates after today MUST be disabled and not selectable
- **AND** the user MUST only be able to select today or past dates

#### Scenario: Today is selectable
- **WHEN** user opens the date picker
- **THEN** today's date MUST be selectable

### Requirement: Report Generation Prompt for Missing Snapshot

The system SHALL prompt users to generate a report when selecting a historical trading day without existing snapshots.

#### Scenario: Prompt for missing historical snapshot
- **WHEN** user selects a past trading day that has no snapshot data
- **THEN** the system MUST display a confirmation dialog
- **AND** the dialog MUST ask if the user wants to generate a report for that date
- **AND** the dialog MUST include the selected date in the message

#### Scenario: User confirms report generation
- **WHEN** user clicks "Confirm" in the generation dialog
- **THEN** the system MUST call the snapshot generation API for the selected date
- **AND** the system MUST display a loading indicator during generation
- **AND** after successful generation, the system MUST load and display the report

#### Scenario: User cancels report generation
- **WHEN** user clicks "Cancel" in the generation dialog
- **THEN** the system MUST close the dialog
- **AND** the system MUST NOT make any API calls
- **AND** the system MUST remain on the current view without a report

### Requirement: Trading Day Check Error Handling

The system SHALL provide clear feedback when trading day information cannot be retrieved.

#### Scenario: Trading day API returns error
- **WHEN** the trading day check API returns an error or timeout
- **THEN** the system MUST display a user-friendly error message
- **AND** the system MUST allow the user to retry the operation

#### Scenario: Trading day check loading state
- **WHEN** the system is checking if a date is a trading day
- **THEN** the system MUST display a loading indicator
- **AND** the date picker MUST remain interactive during the check
