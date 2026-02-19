## 1. Setup & Dependencies

- [x] 1.1 Add openbb>=4.0.0 to backend/requirements.txt
- [x] 1.2 Create backend/app/providers/openbb/ directory structure
- [x] 1.3 Create backend/app/services/advanced/ directory structure
- [x] 1.4 Create backend/app/schemas/advanced.py file

## 2. Base Class Extension (Data Source Capabilities)

- [x] 2.1 Add CAPABILITIES: Set[str] class attribute to DataProvider base class
- [x] 2.2 Add get_financial_report() abstract method to DataProvider (with default NotImplementedError)
- [x] 2.3 Add get_valuation_metrics() abstract method to DataProvider (with default NotImplementedError)
- [x] 2.4 Add get_macro_indicators() abstract method to DataProvider (with default NotImplementedError)
- [x] 2.5 Update existing providers (Sina, EastMoney, Tencent, Netease) with CAPABILITIES declaration
- [x] 2.6 Update providers/__init__.py to export new classes

## 3. OpenBB Provider Implementation

- [x] 3.1 Create OpenBBProvider class with PRIORITY=5, NAME="openbb"
- [x] 3.2 Implement lazy loading for OpenBB (get_obb() function)
- [x] 3.3 Implement _convert_symbol_for_openbb() for A-share code conversion
- [x] 3.4 Implement OpenBBProvider.is_available() to check OpenBB installation
- [x] 3.5 Implement OpenBBProvider.get_realtime_price() (basic implementation)
- [x] 3.6 Implement OpenBBProvider.get_kline_data() (basic implementation)
- [x] 3.7 Implement OpenBBProvider.get_financial_report() with report_type and period parameters
- [x] 3.8 Implement OpenBBProvider.get_valuation_metrics() returning PE/PB/ROE/growth/margin/debt
- [x] 3.9 Implement OpenBBProvider.get_macro_indicators() for GDP/CPI/interest rate
- [x] 3.10 Add error handling and logging for all OpenBB methods

## 4. Coordinator Extension

- [x] 4.1 Add get_financial_report() method to DataSourceCoordinator
- [x] 4.2 Add get_valuation_metrics() method to DataSourceCoordinator
- [x] 4.3 Add get_macro_indicators() method to DataSourceCoordinator
- [x] 4.4 Add get_capabilities() method to return provider capabilities map
- [x] 4.5 Add _get_capable_providers(capability) helper method
- [x] 4.6 Add OpenBBProvider to providers list in coordinator

## 5. Caching Layer

- [x] 5.1 Add financial_report_cache with 24h TTL
- [x] 5.2 Add valuation_cache with 1h TTL
- [x] 5.3 Add macro_cache with 24h TTL
- [x] 5.4 Update clear_all_caches() to include new caches

## 6. Schema Definitions

- [x] 6.1 Create FinancialReportResponse schema
- [x] 6.2 Create ValuationMetricsResponse schema
- [x] 6.3 Create MacroIndicatorsResponse schema
- [x] 6.4 Create ErrorResponse schema for advanced data errors

## 7. Service Layer

- [x] 7.1 Create advanced/financial.py service with get_financial_report() function
- [x] 7.2 Create advanced/valuation.py service with get_valuation_metrics() function
- [x] 7.3 Create advanced/macro.py service with get_macro_indicators() function
- [x] 7.4 Add service-level error handling and fallback logic

## 8. API Endpoints

- [x] 8.1 Add GET /stocks/{symbol}/financial/report endpoint
- [x] 8.2 Add GET /stocks/{symbol}/valuation endpoint
- [x] 8.3 Add GET /macro/indicators endpoint
- [x] 8.4 Add request validation for query parameters
- [x] 8.5 Add response serialization with proper HTTP status codes

## 9. Testing

- [x] 9.1 Write unit tests for OpenBBProvider.get_financial_report()
- [x] 9.2 Write unit tests for OpenBBProvider.get_valuation_metrics()
- [x] 9.3 Write unit tests for OpenBBProvider.get_macro_indicators()
- [x] 9.4 Write unit tests for coordinator capability routing
- [x] 9.5 Write integration tests for /financial/report endpoint
- [x] 9.6 Write integration tests for /valuation endpoint
- [x] 9.7 Write integration tests for /macro/indicators endpoint
- [x] 9.8 Write tests for cache behavior

## 10. Documentation & Cleanup

- [x] 10.1 Update CLAUDE.md with new API endpoints
- [x] 10.2 Add docstrings to all new classes and methods
- [x] 10.3 Add installation instructions for OpenBB dependency
- [x] 10.4 Add troubleshooting guide for common OpenBB issues
