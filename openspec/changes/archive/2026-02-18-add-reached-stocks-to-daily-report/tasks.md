## 1. Backend Schema Definitions

- [x] 1.1 Add `ReachedIndicator` schema in `schemas.py` with fields: ma_type, ma_price, price_difference_percent
- [x] 1.2 Add `ReachedStockItem` schema in `schemas.py` with fields: stock_id, symbol, name, current_price, max_deviation_percent, reached_indicators
- [x] 1.3 Extend `DailyReportResponse` schema to include `reached_stocks: List[ReachedStockItem]` and `total_reached: int`

## 2. Backend Service Layer

- [x] 2.1 Modify `get_daily_report()` in `services.py` to extract all reached stocks from snapshots
- [x] 2.2 Implement aggregation logic: group reached indicators by stock_id
- [x] 2.3 Calculate `max_deviation_percent` for each stock (max of all reached indicators)
- [x] 2.4 Sort reached stocks by `max_deviation_percent` descending
- [x] 2.5 Implement pagination logic with default page_size=10, max=50

## 3. Backend API Endpoint

- [x] 3.1 Modify `/reports/daily` endpoint in `main.py` to accept `page` and `page_size` query parameters
- [x] 3.2 Pass pagination parameters to `get_daily_report()` service function
- [x] 3.3 Return extended response with `reached_stocks` and `total_reached` fields

## 4. Frontend API Layer

- [x] 4.1 Extend `getDailyReport()` in `api.js` to accept optional page and pageSize parameters
- [x] 4.2 Update API call to pass pagination query params

## 5. Frontend UI Components

- [x] 5.1 Add new state variables in `DailyReport.jsx`: `reachedStocks`, `reachedPage`, `reachedTotal`
- [x] 5.2 Create "今日达标个股" section with Ant Design Table component
- [x] 5.3 Implement table columns: symbol, name, reached_indicators (as Tags), current_price, max_deviation_percent
- [x] 5.4 Add Ant Design Pagination component with page change handler
- [x] 5.5 Add empty state handling when no reached stocks
- [x] 5.6 Style max_deviation_percent with green color and "+" prefix

## 6. Testing & Verification

- [x] 6.1 Test backend API with different page and page_size values
- [x] 6.2 Verify sorting: stocks with higher deviation appear first
- [x] 6.3 Verify aggregation: stocks with multiple reached indicators show all tags
- [x] 6.4 Test frontend pagination: navigate between pages
- [x] 6.5 Test edge cases: no reached stocks, single page, boundary page sizes
