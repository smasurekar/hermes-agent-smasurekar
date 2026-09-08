# Research Plan: Women/Girls Population Percentage Analysis

## Goal
Identify which country (from those with women/girls <45% of population in 2000 per World Bank) had the highest average percentage of women/girls from 2020-2023.

## Components
1. **Identify candidate countries**: World Bank data showing countries with female population <45% in 2000
2. **Get 2020-2023 data**: Female population percentages for those candidate countries across 2020, 2021, 2022, 2023
3. **Calculate averages**: Average female % for each candidate country over 2020-2023
4. **Determine winner**: Country with highest average

## Constraints
- Use World Bank data (World Development Indicators)
- Female population as % of total population
- 2000 threshold: <45%
- Average period: 2020 through end of 2023 (4 years)

## Queries

### Query 1 (High depth): Countries with female population <45% in 2000
Search World Bank WDI for "Population, female (% of total population)" in year 2000, filter <45%

### Query 2 (High depth): 2020-2023 female population % for each candidate country
For each country from Query 1, get female % of total population for 2020, 2021, 2022, 2023

### Query 3 (Medium depth): Verify World Bank indicator definition
Confirm the exact indicator code and methodology for "Population, female (% of total population)"