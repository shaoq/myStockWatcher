## MODIFIED Requirements

### Requirement: Daily report API response structure
The `/reports/daily` API SHALL return reached stocks data with pagination support.

**Original**: API returned only summary statistics and change lists (newly_reached, newly_below).
**Modified**: API now additionally returns reached_stocks array and total_reached count.

#### Scenario: API returns reached stocks with pagination
- **WHEN** client requests `/reports/daily?page=1&page_size=10`
- **THEN** API returns response containing:
  - `reached_stocks`: array of paginated reached stock items
  - `total_reached`: total count of reached stocks
- **AND** each reached stock item contains:
  - `stock_id`: integer
  - `symbol`: string
  - `name`: string
  - `current_price`: float
  - `max_deviation_percent`: float
  - `reached_indicators`: array of {ma_type, ma_price, price_difference_percent}

#### Scenario: Default pagination when parameters omitted
- **WHEN** client requests `/reports/daily` without page parameters
- **THEN** API returns first page with default page_size of 10

#### Scenario: Pagination boundary enforcement
- **WHEN** client requests page_size greater than 50
- **THEN** API limits page_size to 50 maximum

## ADDED Requirements

### Requirement: ReachedStockItem data schema
The system SHALL define a structured schema for reached stock items in API responses.

#### Scenario: ReachedStockItem structure
- **WHEN** API returns reached stock data
- **THEN** each item conforms to the following schema:
  ```
  {
    "stock_id": int,
    "symbol": str,
    "name": str,
    "current_price": float,
    "max_deviation_percent": float,
    "reached_indicators": [
      {
        "ma_type": str,
        "ma_price": float,
        "price_difference_percent": float
      }
    ]
  }
  ```

### Requirement: Backend aggregation logic
The system SHALL aggregate multiple reached indicators per stock and calculate max deviation.

#### Scenario: Aggregate indicators for single stock
- **WHEN** processing snapshots for daily report
- **THEN** system groups all reached indicators by stock_id
- **AND** calculates max_deviation_percent from all reached indicators
- **AND** sorts stocks by max_deviation_percent descending

#### Scenario: Filter only reached indicators
- **WHEN** aggregating indicators for a stock
- **THEN** system only includes indicators where reached_target is true
- **AND** excludes indicators where reached_target is false
