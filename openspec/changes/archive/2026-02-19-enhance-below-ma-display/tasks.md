## 1. Backend - Data Model & Schema

- [x] 1.1 Add `BelowStockItem` schema in `schemas.py` with fields: stock_id, symbol, name, current_price, ma_type, ma_price, price_difference_percent, fall_type
- [x] 1.2 Add `continuous_below_count` field to `DailyReportSummary` schema
- [x] 1.3 Add `all_below_stocks` field to `DailyReportResponse` schema

## 2. Backend - Business Logic

- [x] 2.1 Modify `get_daily_report()` in `services.py` to collect all below stocks (not just status changes)
- [x] 2.2 Implement `fall_type` classification logic: new_fall vs continuous_below
- [x] 2.3 Calculate and include `continuous_below_count` in summary
- [x] 2.4 Sort all_below_stocks by MA type, then by fall_type (new_fall first), then by deviation (most negative first)
- [x] 2.5 Maintain backward compatibility: keep `newly_below` array unchanged

## 3. Frontend - API Service

- [x] 3.1 Update `api.js` to handle new `all_below_stocks` response field
- [x] 3.2 Update `getDailyReport` function return type if needed

## 4. Frontend - Daily Report Component

- [x] 4.1 Modify `renderMACollapsePanel()` to handle below stocks with fall_type classification
- [x] 4.2 Add visual indicators: 🔴 for new_fall, 🟡 for continuous_below
- [x] 4.3 Update sorting: new_fall items first, then continuous_below, sorted by deviation
- [x] 4.4 Update summary card to show total below count and continuous below count

## 5. Testing & Verification

- [x] 5.1 Verify API returns correct `all_below_stocks` with proper `fall_type` classification
- [x] 5.2 Verify backward compatibility: `newly_below` still works for existing clients
- [x] 5.3 Verify frontend displays grouped below stocks correctly
- [x] 5.4 Test edge case: stocks without yesterday snapshot default to continuous_below
