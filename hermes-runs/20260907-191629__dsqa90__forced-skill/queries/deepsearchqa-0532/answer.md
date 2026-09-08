Now I have all the data needed. Let me compile the complete answer.

## Answer

### Five Countries with Greatest Share of Reduction in Reported TB Cases (2021 vs 2019)

Based on WHO Global TB Report data (indicator `TB_c_newinc` = new and relapse cases notified), the five countries accounting for the largest share of the global reduction in reported TB cases between 2019 and 2021 were:

| Country | 2019 Cases | 2021 Cases | Absolute Reduction | Share of 5-Country Total Reduction |
|---------|------------|------------|-------------------|-----------------------------------|
| **India** | 2,162,323 | 1,965,444 | **196,879** | 31.5% |
| **China** | 728,265 | 585,340 | **142,925** | 22.9% |
| **Indonesia** | 559,847 | 432,577 | **127,270** | 20.4% |
| **Philippines** | 409,167 | 321,564 | **87,603** | 14.0% |
| **Myanmar** | 134,501 | 64,410 | **70,091** | 11.2% |

These five countries collectively accounted for **624,768** fewer reported TB cases in 2021 vs 2019, consistent with the WHO Global TB Report 2022 finding that these five "accounted for 90% of the reduction in case notifications in 2021 compared with 2019" [1].

The WHO defines "share of reduction" as each country's absolute reduction as a proportion of the global absolute reduction [2].

### Lowest 2023 TB Cases Among These Five

| Country | 2023 Reported TB Cases |
|---------|------------------------|
| **Myanmar** | **129,122** |
| China | 564,918 |
| Philippines | 575,770 |
| Indonesia | 804,836 |
| India | 2,382,714 |

**Myanmar** reported the lowest number of TB cases in 2023 among the five countries with the greatest share of reduction in 2021 vs 2019, with **129,122** notified cases.

---

## Sources

[1] WHO Global TB Report 2022 / CIDRAP summary: "These five [India, Indonesia, China, Myanmar, Philippines] accounted for 90% of the reduction in case notifications in 2021 compared with 2019" — https://www.cidrap.umn.edu/tuberculosis/who-reports-rise-global-tb-cases-deaths

[2] WHO Global Tuberculosis Report 2021 methodology: "The countries that contributed most to the global reduction in TB notifications between 2019 and 2020 were India (41%), Indonesia (14%), the Philippines (12%) and China (8%)" — definition of share = country absolute reduction / global absolute reduction — https://www.who.int/news/item/14-10-2021-tuberculosis-deaths-rise-for-the-first-time-in-more-than-a-decade-due-to-the-covid-19-pandemic

[3] WHO GHO API — 2019 reported TB cases (TB_c_newinc):
- India: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'IND'%20and%20TimeDim%20eq%202019
- Indonesia: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'IDN'%20and%20TimeDim%20eq%202019
- China: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'CHN'%20and%20TimeDim%20eq%202019
- Myanmar: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'MMR'%20and%20TimeDim%20eq%202019
- Philippines: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'PHL'%20and%20TimeDim%20eq%202019

[4] WHO GHO API — 2021 reported TB cases (TB_c_newinc):
- India: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'IND'%20and%20TimeDim%20eq%202021
- Indonesia: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'IDN'%20and%20TimeDim%20eq%202021
- China: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'CHN'%20and%20TimeDim%20eq%202021
- Myanmar: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'MMR'%20and%20TimeDim%20eq%202021
- Philippines: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'PHL'%20and%20TimeDim%20eq%202021

[5] WHO GHO API — 2023 reported TB cases (TB_c_newinc):
- India: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'IND'%20and%20TimeDim%20eq%202023
- Indonesia: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'IDN'%20and%20TimeDim%20eq%202023
- China: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'CHN'%20and%20TimeDim%20eq%202023
- Myanmar: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'MMR'%20and%20TimeDim%20eq%202023
- Philippines: https://ghoapi.azureedge.net/api/TB_c_newinc?$filter=SpatialDim%20eq%20'PHL'%20and%20TimeDim%20eq%202023
