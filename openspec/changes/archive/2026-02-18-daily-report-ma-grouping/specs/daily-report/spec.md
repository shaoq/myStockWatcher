## ADDED Requirements

### Requirement: MA Grouped Change List Display

The frontend SHALL display status change lists (newly reached and newly below) grouped by MA indicator type.

#### Scenario: Display changes grouped by MA type
- **WHEN** the daily report page renders the "newly reached" or "newly below" section
- **THEN** the system MUST group items by their `ma_type` field
- **AND** each group MUST display as a collapsible panel
- **AND** the group header MUST show the MA type and count (e.g., "MA5 (3只)")

#### Scenario: Sort MA groups by numeric value
- **WHEN** rendering grouped change lists
- **THEN** the system MUST sort groups by the numeric value in MA type (MA5 → MA10 → MA20 → MA60)
- **AND** groups MUST display in ascending order

#### Scenario: Sort items within group by deviation
- **WHEN** rendering items within an MA group
- **THEN** the system MUST sort items by `price_difference_percent` in descending order (largest deviation first)

#### Scenario: Hide empty MA groups
- **WHEN** an MA type has no items in the change list
- **THEN** the system MUST NOT display that MA group

#### Scenario: Collapse panel interaction
- **WHEN** user clicks on an MA group panel header
- **THEN** the panel MUST toggle between expanded and collapsed states
- **AND** the expanded state MUST show all items in that group
- **AND** the collapsed state MUST show only the group header
