Based on my research, here's what I found:

## Five States with Highest Poverty Rate in 2022 (per Center for American Progress / U.S. Census Bureau ACS)

The Center for American Progress's poverty data project uses U.S. Census Bureau American Community Survey (ACS) data. Multiple sources citing the 2022 ACS 1-year estimates consistently identify these five states as having the highest official poverty rates:

| Rank | State | Poverty Rate (2022 ACS) |
|------|-------|------------------------|
| 1 | **Louisiana** | 18.7% – 18.9% |
| 2 | **Mississippi** | 17.8% – 18.0% |
| 3 | **New Mexico** | 16.8% – 18.3% |
| 4 | **West Virginia** | 16.7% – 16.8% |
| 5 | **Arkansas** | 15.5% – 15.9% |

*Sources: Census Bureau ACS 2022 1-year estimates (Table S1701/DP03); CAP poverty data project; Visual Capitalist, World Population Review, and KFF analyses of 2022 ACS data.*

---

## Grandparents with Disability Caring for Grandchildren (2022 ACS, Table B10052)

I attempted to retrieve 2022 ACS 1-year or 5-year estimates from Census Table **B10052** ("Disability Status of Grandparents Living With Own Grandchildren Under 18 Years by Responsibility for Own Grandchildren and Age of Grandparent") for the five states above. The specific variable of interest is:

- **B10052_002E**: Total grandparents *with any disability*
- **B10052_003E**: With disability, *responsible for grandchildren*, ages 30–59
- **B10052_004E**: With disability, *responsible for grandchildren*, age 60+
- **B10052_005E**: With disability, *not responsible for grandchildren*

However, the Census API endpoints for 2022 ACS (both 1-year and 5-year) are not returning data for these detailed tables at the state level in my queries, and the Census Reporter / data.census.gov web interfaces require interactive selection that isn't accessible via programmatic extraction.

**What the table structure tells us:** The relevant figure for your question would be the sum of `B10052_003E + B10052_004E` for each state — i.e., grandparents **with a disability** who are **responsible for own grandchildren under 18**.

---

## Next Steps to Get the Exact Numbers

To obtain the definitive counts for the five states, you would need to:

1. **Use data.census.gov directly**: Go to [Table B10052](https://data.census.gov/table/ACSDT1Y2022.B10052) (or the 5-year version ACSDT5Y2022), filter for Geography = **State**, select the five states (LA, MS, NM, WV, AR), and read the values for rows:
   - `With any disability: Grandparent responsible for own grandchildren under 18 years: 30 to 59 years`
   - `With any disability: Grandparent responsible for own grandchildren under 18 years: 60 years and over`

2. **Or use the Census API with a valid key** (the public endpoint may be rate-limited or require a key for detailed tables):
   ```
   https://api.census.gov/data/2022/acs/acs1?get=NAME,B10052_003E,B10052_004E&for=state:22,28,35,54,05&key=YOUR_KEY
   ```

3. **Check Census Reporter** profiles for each state — they sometimes surface B10052 data in the "Families" or "Disability" sections.

---

## Summary

- **Five highest-poverty states (2022)**: Louisiana, Mississippi, New Mexico, West Virginia, Arkansas.
- **Grandparents with disability caring for grandchildren**: The data exists in Census Table **B10052** (variables `_003E` + `_004E`) but requires direct query from data.census.gov or the Census API to extract the 2022 state-level counts for these five states.

If you can access data.census.gov, the comparison takes about 2 minutes: select B10052 → 2022 ACS 1-year → Geography: State → pick the 5 states → read the two "Grandparent responsible… With any disability" rows.
