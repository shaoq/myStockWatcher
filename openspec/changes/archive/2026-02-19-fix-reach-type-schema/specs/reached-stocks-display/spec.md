## MODIFIED Requirements

### Requirement: Reached indicator display format

The system SHALL display reached indicators with color-coded status tags and reach type classification.

#### Scenario: API returns reach_type field
- **WHEN** client requests `/reports/daily`
- **THEN** each item in `reached_indicators` array MUST include a `reach_type` field
- **AND** `reach_type` value is either "new_reach" or "continuous_reach"
