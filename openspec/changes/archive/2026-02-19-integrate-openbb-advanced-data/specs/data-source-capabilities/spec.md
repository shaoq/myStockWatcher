## ADDED Requirements

### Requirement: Provider can declare supported capabilities

The system SHALL allow data providers to declare their supported capabilities through a CAPABILITIES attribute.

#### Scenario: Provider declares capabilities

- **WHEN** a DataProvider subclass defines CAPABILITIES = {"realtime_price", "kline_data"}
- **THEN** coordinator can query these capabilities
- **AND** coordinator can route requests based on capabilities

### Requirement: Standard capability names defined

The system SHALL define standard capability names for consistent routing.

#### Scenario: Standard capability names

- **WHEN** system initializes
- **THEN** the following capability names are defined:
  - "realtime_price" - real-time stock price
  - "kline_data" - K-line/candlestick data
  - "financial_report" - financial statements (balance sheet, income, cash flow)
  - "valuation_metrics" - valuation metrics (PE, PB, ROE, etc.)
  - "macro_indicators" - macroeconomic indicators
  - "news_sentiment" - news and sentiment analysis

### Requirement: Coordinator can query provider capabilities

The system SHALL allow coordinator to check if a provider supports a specific capability.

#### Scenario: Check provider capability

- **WHEN** coordinator checks if SinaProvider supports "financial_report"
- **THEN** system returns False (SinaProvider only supports realtime_price and kline_data)

#### Scenario: Check OpenBB capabilities

- **WHEN** coordinator checks if OpenBBProvider supports "financial_report"
- **THEN** system returns True

### Requirement: Coordinator routes by capability

The system SHALL route requests to appropriate provider based on requested capability.

#### Scenario: Route realtime price request

- **WHEN** coordinator receives request for realtime_price
- **THEN** coordinator tries providers in priority order (Sina → EastMoney → ...)
- **AND** only uses providers that have "realtime_price" capability

#### Scenario: Route financial report request

- **WHEN** coordinator receives request for financial_report
- **THEN** coordinator routes directly to OpenBBProvider
- **AND** skips providers without financial_report capability

### Requirement: Capability check accounts for availability

The system SHALL only route to providers that are both capable and available.

#### Scenario: Provider capable but unavailable

- **WHEN** OpenBBProvider has "financial_report" capability
- **AND** OpenBB is not installed
- **THEN** coordinator treats provider as unavailable
- **AND** financial_report request returns error

#### Scenario: Provider capable and available

- **WHEN** OpenBBProvider has "financial_report" capability
- **AND** OpenBB is installed and healthy
- **THEN** coordinator routes request to OpenBBProvider

### Requirement: New providers can be added with capabilities

The system SHALL allow adding new providers with their capabilities without modifying coordinator logic.

#### Scenario: Add new provider

- **WHEN** developer creates new provider class with CAPABILITIES = {"custom_data"}
- **AND** registers provider with coordinator
- **THEN** coordinator automatically routes "custom_data" requests to new provider
