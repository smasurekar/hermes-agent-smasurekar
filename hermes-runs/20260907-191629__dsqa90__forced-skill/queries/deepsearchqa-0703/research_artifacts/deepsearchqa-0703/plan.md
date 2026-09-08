# Research Plan: Pennsylvania Counties with Tornadoes, Low Income, Low Population

## Goal
Identify Pennsylvania counties that meet all three criteria:
1. 3+ tornadoes (1950-2000) per climate.met.psu.edu
2. Median household income < $49,000 (2023 dollars) per 2019-2023 census.gov
3. Among 5 least populated counties per 2020 census.gov

## Components
1. **Tornado data** - PA counties with 3+ tornadoes 1950-2000 from climate.met.psu.edu
2. **Income data** - Median household income (2023 dollars) 2019-2023 for those counties from census.gov
3. **Population data** - 2020 census population for all PA counties to identify bottom 5

## Constraints
- Must use climate.met.psu.edu for tornado data
- Must use census.gov for income and population
- Income threshold: $49,000 in 2023 dollars (adjusted for inflation)
- Population: 2020 decennial census figures
- Output: List of counties meeting ALL three criteria

## Queries

### High Depth
1. **Tornado counts by PA county 1950-2000** - climate.met.psu.edu tornado database for Pennsylvania, county-level counts
2. **PA county median household income 2019-2023** - census.gov ACS 5-year estimates, 2023 dollars, all PA counties
3. **PA county 2020 census population** - census.gov decennial census 2020, all PA counties

### Medium Depth
4. **Inflation adjustment methodology** - How census reports 2023 dollar values for 2019-2023 ACS data
5. **Cross-reference verification** - Confirm tornado data source matches climate.met.psu.edu specifically

### Low Depth
6. **List of all 67 PA counties** - For completeness checking