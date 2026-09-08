Based on my research across Eurostat datasets, here is the answer:

## Answer

**Belgium** transported the most goods in total across air, sea, road, and rail in 2022 among countries with average full-time adjusted salary ≥ €50,000.

## Supporting Data

### Countries Meeting the €50k Salary Threshold (2022)
| Country | Average Full-Time Adjusted Salary |
|---------|-----------------------------------|
| Luxembourg | €74,500 |
| Denmark | €65,211 |
| Ireland | €54,312 |
| Belgium | €53,559 |
| Austria | €50,701 |

*Source: Eurostat `nama_10_fte`*

### 2022 Total Goods Transport (thousand tonnes)
| Country | Road | Rail | Sea | Air | **Total** |
|---------|------|------|-----|-----|-----------|
| **Belgium** | 273,307 | N/A* | 288,229 | 1,729 | **563,265** |
| Austria | 390,419 | 103,870 | 0 | 188 | **494,477** |
| Denmark | 174,842 | 7,759 | 98,230 | 266 | **281,097** |
| Ireland | 162,902 | 419 | 53,482 | 157 | **216,960** |
| Luxembourg | 50,339 | 7,453 | 0 | 969 | **58,761** |

*Belgium rail data is confidential (flagged 'C' in Eurostat) and excluded from total.

## Key Methodological Notes
- **Units harmonized to thousand tonnes**: Road/rail from source datasets (`road_go_ta_tott`, `rail_go_total`); sea from `ttr00009`/`mar_go_aa` (gross weight handled in ports); air from `ttr00011`/`avia_gooc` converted from tonnes.
- **Modal definitions differ**: Sea measures port throughput (loading + unloading), while road/rail/air measure goods transported. Air represents <1% of totals.
- Austria and Luxembourg have no maritime ports (sea = 0).

## Sources
1. Eurostat `nama_10_fte` - Average full time adjusted salary per employee 2022
2. Eurostat `road_go_ta_tott` - Road goods transport, thousand tonnes 2022
3. Eurostat `rail_go_total` - Rail goods transport, thousand tonnes 2022
4. Eurostat `ttr00009`/`mar_go_aa` - Maritime goods transport, thousand tonnes 2022
5. Eurostat `ttr00011`/`avia_gooc` - Air goods transport, tonnes 2022
