# Research Plan: OECS Founding Members Meeting Multiple 2020/2021 Criteria

## Goal
Identify which founding members of the Organisation of Eastern Caribbean States (OECS) meet all three criteria:
1. Population growth rate < 0.5% in 2021 (CIA World Factbook 2021 archive)
2. Under-5 mortality rate < 20 per 1000 live births in 2020 (UN data)
3. Female life expectancy at birth > 75 years in 2020 (UN data)

## Components
1. **OECS Founding Members** - List all founding member states
2. **Population Growth Rates 2021** - CIA World Factbook 2021 archive data for each founding member
3. **Under-5 Mortality Rates 2020** - UN data (UN IGME or World Bank/UN Population Division) for each founding member
4. **Female Life Expectancy 2020** - UN data (UN World Population Prospects) for each founding member
5. **Cross-filtering** - Apply all three criteria and identify qualifying members

## Constraints
- Use CIA World Factbook 2021 *archive* (not current edition) for population growth
- Use UN data sources for mortality and life expectancy (not CIA or other sources)
- 2020 data for mortality and life expectancy; 2021 for population growth
- Output: List of qualifying countries, or "none" if no country meets all criteria

## Queries

### Query 1 (High) - OECS Founding Members
**Component:** 1
**Goal:** Identify all founding member states of the Organisation of Eastern Caribbean States and the founding date.

### Query 2 (High) - Population Growth Rates 2021 (CIA Factbook Archive)
**Component:** 2
**Goal:** For each OECS founding member, find the 2021 population growth rate (%) from the CIA World Factbook 2021 archive edition.

### Query 3 (High) - Under-5 Mortality Rates 2020 (UN Data)
**Component:** 3
**Goal:** For each OECS founding member, find the 2020 under-5 mortality rate (deaths per 1000 live births) from UN data (UN IGME, UN World Population Prospects, or World Bank UN estimates).

### Query 4 (High) - Female Life Expectancy 2020 (UN Data)
**Component:** 4
**Goal:** For each OECS founding member, find the 2020 female life expectancy at birth (years) from UN data (UN World Population Prospects 2022 revision or similar).

### Query 5 (Medium) - Cross-Reference & Verification
**Component:** 5
**Goal:** Verify the intersection: which founding members have pop growth <0.5% (2021 CIA), U5MR <20 (2020 UN), AND female LE >75 (2020 UN). Provide citations for each data point.