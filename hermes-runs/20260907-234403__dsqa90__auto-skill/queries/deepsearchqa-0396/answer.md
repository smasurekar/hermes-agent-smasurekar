Based on my analysis of Eurostat data for 2022, **Ireland** transported the most goods in total across air, sea, road, and rail among countries with average full-time adjusted salary ≥ €50,000.

**Total freight transport 2022 (million tonne-km) for qualifying countries:**

| Country | Salary (€) | Road | Rail | Air | Sea (est.) | Total |
|---------|-----------|------|------|-----|------------|-------|
| **Ireland** | 53,559 | 11,424 | 81 | 181 | 114,885 | **~126,571** |
| Belgium | 50,701 | 34,379 | 5,229 | 491 | 31,012 | ~71,111 |
| Denmark | 65,211 | 14,686 | 2,190 | 152 | 49,912 | ~66,940 |
| Luxembourg | 74,500 | 6,176 | 228 | 40 | 0 | ~6,444 |

**Data sources:**
- **Road**: `ttr00005` / `road_go_ta_tott` (absolute MIO_TKM)
- **Rail**: `rail_go_typepas` (absolute MIO_TKM)  
- **Air**: `avia_tpgo` (absolute MIO_TKM)
- **Sea**: Estimated from modal split percentages in `tran_hv_ms_frmod` (SEA% / ROAD% × road absolute)
- **Salaries**: `nama_10_fte` (2022 average full-time adjusted salary)

**Note**: Netherlands (salary ~€54,312) is excluded from `nama_10_fte` per Eurostat metadata. Austria, Germany, Finland, Sweden all fall below €50,000 threshold.
