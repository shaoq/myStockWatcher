## ADDED Requirements

### Requirement: System can fetch GDP data

The system SHALL provide the ability to fetch GDP growth rate for specified market.

#### Scenario: Fetch China GDP growth rate

- **WHEN** user requests macro indicators with market="cn" and indicators=["gdp"]
- **THEN** system returns GDP growth rate for China
- **AND** value is expressed as percentage

### Requirement: System can fetch CPI data

The system SHALL provide the ability to fetch Consumer Price Index (CPI) for specified market.

#### Scenario: Fetch China CPI

- **WHEN** user requests macro indicators with market="cn" and indicators=["cpi"]
- **THEN** system returns CPI value for China
- **AND** value includes year-over-year change

### Requirement: System can fetch interest rate data

The system SHALL provide the ability to fetch benchmark interest rate for specified market.

#### Scenario: Fetch China benchmark interest rate

- **WHEN** user requests macro indicators with market="cn" and indicators=["interest_rate"]
- **THEN** system returns benchmark interest rate for China

### Requirement: System can fetch multiple indicators at once

The system SHALL support fetching multiple macro indicators in a single request.

#### Scenario: Fetch multiple indicators

- **WHEN** user requests macro indicators with indicators=["gdp","cpi","interest_rate"]
- **THEN** system returns all requested indicators in single response
- **AND** each indicator includes value, unit, and last_updated timestamp

### Requirement: Macro data is cached appropriately

The system SHALL cache macro indicator data for 24 hours.

#### Scenario: Cache hit for macro data

- **WHEN** user requests macro data that was fetched within 24 hours
- **THEN** system returns cached data without making external API call

### Requirement: Macro indicators API endpoint

The system SHALL expose macro indicators through REST API endpoint.

#### Scenario: API endpoint structure

- **WHEN** client calls `GET /macro/indicators`
- **THEN** system accepts query parameters: market (default "cn"), indicators (comma-separated)
- **AND** returns JSON response with requested indicators

#### Scenario: Default market is China

- **WHEN** client calls `GET /macro/indicators` without market parameter
- **THEN** system returns indicators for China market

### Requirement: Macro data handles unsupported indicators

The system SHALL handle cases where requested indicator is not available.

#### Scenario: Request unsupported indicator

- **WHEN** user requests macro indicator "unsupported_indicator"
- **THEN** system returns error response indicating indicator is not supported
- **AND** response includes list of supported indicators
