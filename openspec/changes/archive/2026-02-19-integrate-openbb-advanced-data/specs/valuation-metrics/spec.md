## ADDED Requirements

### Requirement: System can calculate PE ratio

The system SHALL provide the ability to fetch Price-to-Earnings (PE) ratio for a given stock.

#### Scenario: Fetch PE ratio for profitable stock

- **WHEN** user requests valuation metrics for a profitable stock "600000"
- **THEN** system returns PE ratio value
- **AND** PE ratio is calculated as current_price / earnings_per_share

#### Scenario: Fetch PE ratio for unprofitable stock

- **WHEN** user requests valuation metrics for a stock with negative earnings
- **THEN** system returns PE ratio as null or negative value
- **AND** response indicates the company is unprofitable

### Requirement: System can calculate PB ratio

The system SHALL provide the ability to fetch Price-to-Book (PB) ratio for a given stock.

#### Scenario: Fetch PB ratio

- **WHEN** user requests valuation metrics for stock "600000"
- **THEN** system returns PB ratio value
- **AND** PB ratio is calculated as current_price / book_value_per_share

### Requirement: System can provide ROE metric

The system SHALL provide the ability to fetch Return on Equity (ROE) for a given stock.

#### Scenario: Fetch ROE

- **WHEN** user requests valuation metrics for stock "600000"
- **THEN** system returns ROE value as percentage
- **AND** ROE reflects the most recent fiscal period

### Requirement: System can provide revenue growth metric

The system SHALL provide the ability to fetch revenue growth rate for a given stock.

#### Scenario: Fetch revenue growth

- **WHEN** user requests valuation metrics for stock "600000"
- **THEN** system returns revenue growth as percentage (YoY)

### Requirement: System can provide profit margin metric

The system SHALL provide the ability to fetch profit margin for a given stock.

#### Scenario: Fetch profit margin

- **WHEN** user requests valuation metrics for stock "600000"
- **THEN** system returns profit margin as percentage
- **AND** profit margin is net_income / revenue

### Requirement: System can provide debt-to-equity ratio

The system SHALL provide the ability to fetch debt-to-equity ratio for a given stock.

#### Scenario: Fetch debt-to-equity ratio

- **WHEN** user requests valuation metrics for stock "600000"
- **THEN** system returns debt-to-equity ratio
- **AND** ratio is calculated as total_debt / total_equity

### Requirement: Valuation data is cached appropriately

The system SHALL cache valuation metrics for 1 hour.

#### Scenario: Cache hit for valuation data

- **WHEN** user requests valuation data that was fetched within 1 hour
- **THEN** system returns cached data without making external API call

#### Scenario: Cache refresh after price update

- **WHEN** stock price changes significantly
- **AND** user requests valuation metrics
- **THEN** system may recalculate valuation metrics if cache has expired

### Requirement: Valuation data API endpoint

The system SHALL expose valuation metrics through REST API endpoint.

#### Scenario: API endpoint structure

- **WHEN** client calls `GET /stocks/{symbol}/valuation`
- **THEN** system returns JSON response with all valuation metrics
- **AND** response includes: pe_ratio, pb_ratio, roe, revenue_growth, profit_margin, debt_to_equity
- **AND** response includes data source and fetch timestamp

### Requirement: Valuation data handles missing metrics

The system SHALL handle cases where some metrics are unavailable.

#### Scenario: Partial valuation data

- **WHEN** user requests valuation metrics but some data is unavailable
- **THEN** system returns available metrics
- **AND** unavailable metrics are returned as null with appropriate message
