## ADDED Requirements

### Requirement: Calendar Date Report Indicator

The date picker calendar SHALL display a visual indicator on dates that have existing report data.

#### Scenario: Display indicator for dates with reports
- **WHEN** user opens the date picker calendar in the daily report page
- **THEN** the system MUST display a green dot indicator on dates that have report data
- **AND** dates without reports MUST display normally without any indicator

#### Scenario: Indicator visibility
- **WHEN** rendering a calendar date cell
- **THEN** the indicator MUST be visible as a small green circle (6px diameter)
- **AND** the indicator MUST be positioned at the top-right corner of the date cell
- **AND** the indicator MUST NOT obscure the date number

#### Scenario: Data source for indicator
- **WHEN** determining which dates should show the indicator
- **THEN** the system MUST use the existing `availableDates` data
- **AND** no additional API requests SHALL be required
