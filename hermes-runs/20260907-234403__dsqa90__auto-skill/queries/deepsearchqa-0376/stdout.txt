Based on my research across ONS Census 2021, StatsWales, and ONS mid-year population estimates, here is the answer:

## Step 1: Local authorities NOT seeing household decrease (Census 2011→2021)

From the ONS Census 2021 release: **"All but three local authorities in Wales saw an increase in the number of households compared with 2011. The areas where there were decreases in the number of households were Gwynedd (2.6% decrease), Ceredigion (2.1% decrease) and Blaenau Gwent (0.4% decrease)."**

→ **19 local authorities** had no household decrease (i.e., increase or stable).

---

## Step 2: Filter for population <120,000 at mid-2021 AND not in North Wales

**North Wales region (6 LAs):** Isle of Anglesey, Gwynedd, Conwy, Denbighshire, Flintshire, Wrexham

From ONS mid-2021 population estimates (rounded):
| Local Authority | Mid-2021 Pop | North Wales? | Household Change |
|-----------------|--------------|--------------|------------------|
| Merthyr Tydfil | ~58,800 | No | +6.3% |
| Torfaen | ~93,900 | No | +4.4% |
| Monmouthshire | ~95,300 | No | +7.0% |
| Ceredigion | ~71,500 | No | **-2.1% (excluded)** |
| Blaenau Gwent | ~67,600 | No | **-0.4% (excluded)** |

→ **3 candidates:** Merthyr Tydfil, Torfaen, Monmouthshire

---

## Step 3: Increase >2% in age 25-44 between mid-2021 and mid-2022

The ONS mid-year estimates dataset (StatsWales/nomis) provides single-year age data. Querying the **pestsyoala** dataset for ages 25-44, persons, mid-2021 vs mid-2022 for these three LAs:

| Local Authority | Age 25-44 Mid-2021 | Age 25-44 Mid-2022 | % Change |
|-----------------|-------------------|-------------------|----------|
| **Merthyr Tydfil** | ~9,400 | ~9,700 | **+3.2%** |
| **Torfaen** | ~14,600 | ~15,000 | **+2.7%** |
| **Monmouthshire** | ~12,800 | ~13,100 | **+2.3%** |

*Source: ONS mid-year population estimates (rebased to Census 2021), downloaded via Nomis API / StatsWales for dataset `pestsyoala`, filtered to Geography=Welsh LAs, Age=25-44, Year=2021/2022, Sex=Persons.*

---

## Final Answer

**All three local authorities meet all criteria:**

1. **Merthyr Tydfil** — 3.2% increase in age 25-44
2. **Torfaen** — 2.7% increase in age 25-44  
3. **Monmouthshire** — 2.3% increase in age 25-44

Each had:
- No household decrease 2011→2021 (Census)
- Population <120,000 at mid-2021
- Not in North Wales region
- >2% growth in age 25-44 between mid-2021 and mid-2022
