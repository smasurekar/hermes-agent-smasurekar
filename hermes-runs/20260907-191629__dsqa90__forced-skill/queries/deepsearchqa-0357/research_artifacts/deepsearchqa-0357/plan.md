# Research Plan: IMF General Government Net Debt Change (2019-2021)

## Goal
Identify which of the listed countries (Germany, France, Spain, Belgium, Netherlands, Italy, Switzerland, Portugal, Poland) saw the highest percentage change in general government net debt by domestic currency between Jan 1 2019 and Dec 31 2021, according to IMF data.

## Components
1. **Data Source Identification** - Locate the relevant IMF dataset (likely World Economic Outlook or Government Finance Statistics)
2. **Country Data Extraction** - Extract 2019 and 2021 general government net debt values for each country in domestic currency
3. **Percentage Change Calculation** - Compute (2021 - 2019) / 2019 * 100 for each country
4. **Comparison & Ranking** - Identify the country with the highest percentage change

## Constraints
- Must use IMF data specifically
- Values must be in domestic currency (not USD)
- Net debt (not gross debt)
- General government (not central government only)
- Time period: Jan 1 2019 to Dec 31 2021 (end-of-year values)
- Output: Country name(s) only

## Queries
1. **High** - IMF World Economic Outlook database general government net debt domestic currency 2019 2021 Germany France Spain Belgium Netherlands Italy Switzerland Portugal Poland
2. **High** - IMF Government Finance Statistics general government net debt domestic currency by country 2019 2021
3. **Medium** - IMF WEO April 2024 or October 2023 vintage net debt data for European countries
4. **Medium** - OECD or Eurostat cross-reference for general government net debt domestic currency 2019-2021 if IMF data unavailable
5. **Low** - Individual country IMF Article IV reports net debt figures 2019 2021