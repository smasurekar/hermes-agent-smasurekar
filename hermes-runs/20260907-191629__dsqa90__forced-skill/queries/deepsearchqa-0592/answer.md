Based on the Washington State Statistical Analysis Center's Criminal Justice Data Book (CJDB90_24.xlsx) — the official CrimeStats dataset containing 2022 NIBRS adult arrest data by county — **three counties had absolutely zero adult arrests reported to NIBRS for all four crime categories in 2022:**

**Columbia County** — Murder: 0, Robbery: 0, Kidnapping: 0, Forcible Sex Offenses: 0  
**Ferry County** — Murder: 0, Robbery: 0, Kidnapping: 0, Forcible Sex Offenses: 0  
**Wahkiakum County** — Murder: 0, Robbery: 0, Kidnapping: 0, Forcible Sex Offenses: 0

These are all small, rural counties (populations under 8,000 each). The data comes from the SAC's `ARN_MURDER` (NIBRS 09A), `ARN_ROBBERY` (NIBRS 120), `ARN_KIDNAP` (NIBRS 100), and `ARN_FSEX` (NIBRS 11A/11B/11C/11D) columns for calendar year 2022, filtered to county-level agencies only (excluding state-level rollups like "STATE PATROL").

## Sources

- [Washington State SAC Data Portal — Criminal Justice Data Book (CJDB90_24.xlsx)](https://sac.ofm.wa.gov/sites/default/files/CJDB90_24.xlsx) — Primary dataset containing ARN_ columns for 2022 NIBRS adult arrests by county
- [Washington State SAC CrimeStats Online](https://sac.ofm.wa.gov/crimestats-online) — Official query tool for the same data
- [Washington State SAC NIBRS Data Dictionary](https://sac.ofm.wa.gov/sites/default/files/nibrs_dictionary.pdf) — Documents ARN_ column definitions (adult NIBRS arrests)
