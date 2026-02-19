## MODIFIED Requirements

### Requirement: Report Page

The frontend SHALL provide a dedicated page for viewing daily reports with a simplified layout focusing on status changes.

#### Scenario: View daily report page

- **WHEN** user navigates to the daily report page
- **THEN** the system MUST display the summary section with key metrics
- **AND** the system MUST display the status change list with grouped display
- **AND** the system MUST display a trend chart visualization
- **AND** the system MUST NOT display redundant "今日达标个股" table

#### Scenario: Overview cards display

- **WHEN** daily report page loads
- **THEN** the system MUST display overview cards for: total stocks, today's reached count, below MA count, continuous below count
- **AND** the system MUST NOT display "新增达标" as a separate statistic card

## REMOVED Requirements

### Requirement: Display reached stocks in daily report

**Reason**: Moved to `reached-stocks-display` spec with enhanced grouping and status classification. The previous table-based display is replaced by a card-based grouped display.

**Migration**: Use the new "达标个股" card display which shows reached stocks grouped by MA type with status classification (new_reach / continuous_reach).
