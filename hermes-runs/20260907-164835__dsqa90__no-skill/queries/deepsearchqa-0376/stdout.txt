Based on my research using official Welsh Census 2021 and ONS/Welsh Government mid-year population estimates, here is the step-by-step analysis:

---

### **Step 1: Local authorities with NO decrease in households (Census 2011 → 2021)**

From ONS Census 2021 (Figure 6), only **3 local authorities** saw a household decrease:
- Gwynedd (−2.6%)
- Ceredigion (−2.1%)
- Blaenau Gwent (−0.4%)

**→ 19 local authorities did NOT see a household decrease** (all except the three above).

---

### **Step 2: Mid-2021 population < 120,000 AND not in North Wales**

North Wales LAs (6): Isle of Anglesey, Gwynedd, Conwy, Denbighshire, Flintshire, Wrexham.

From rebased mid-2021 estimates (ONS/Welsh Gov):
| Local Authority | Mid-2021 Population | <120k? | Region |
|-----------------|---------------------|--------|--------|
| Merthyr Tydfil  | 58,800              | Yes    | South East |
| Blaenau Gwent   | 67,000              | Yes    | South East |
| Ceredigion      | 72,700              | Yes    | Mid Wales |
| Torfaen         | ~92,300             | Yes    | South East |
| Monmouthshire   | ~95,800             | Yes    | South East |
| Pembrokeshire   | ~123,400            | No     | South West |
| Powys           | ~134,800            | No     | Mid Wales |
| Others          | >120,000            | No     | Various |

**→ 5 local authorities meet both criteria**: **Merthyr Tydfil, Blaenau Gwent, Ceredigion, Torfaen, Monmouthshire**.

---

### **Step 3: Aged 25–44 increase >2% (mid-2021 → mid-2022)**

This requires the ONS MYE2 dataset (mid-year estimates by single year of age) for each LA for 2021 and 2022. The data is available via:
- **Nomis API** (dataset `NM_2002_1`)
- **ONS "Estimates of the population for England and Wales"** MYE2 editions
- **StatsWales** downloadable tables

**I was unable to programmatically retrieve the exact 25–44 age-band totals for each of the 5 LAs for both years** due to API/format restrictions on the ONS/Nomis endpoints. The data exists in the official releases but requires manual download of the MYE2 xlsx/csv files and summing ages 25–44 for each LA.

---

### **What you need to do to complete Step 3**

1. Download the **mid-2021** and **mid-2022** MYE2 local authority tables (2021 boundaries) from ONS:
   - [ONS MYE2 2021](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/estimatesofthepopulationforenglandandwales/mid20212021localauthorityboundaires)
   - [ONS MYE2 2022](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/estimatesofthepopulationforenglandandwales/mid20222021localauthorityboundaires)

2. For each of the 5 LAs, sum the population for ages **25 through 44** (inclusive) for both years.

3. Calculate percentage change:
   ```
   % change = (Pop_2022_25_44 - Pop_2021_25_44) / Pop_2021_25_44 * 100
   ```

4. Select those with **>2% increase**.

---

### **Summary of the 5 candidate LAs**

| Local Authority | Mid-2021 Pop (All Ages) | Household Change 2011-21 | Region | Meets Step 1&2? |
|-----------------|-------------------------|--------------------------|--------|-----------------|
| Merthyr Tydfil  | 58,800                  | +6.3%                    | South East | **Yes** |
| Blaenau Gwent   | 67,000                  | **−0.4%** (decrease)     | South East | **No** (failed Step 1) |
| Ceredigion      | 72,700                  | **−2.1%** (decrease)     | Mid Wales | **No** (failed Step 1) |
| Torfaen         | ~92,300                 | +4.4%                    | South East | **Yes** |
| Monmouthshire   | ~95,800                 | +7.0%                    | South East | **Yes** |

**After Step 1 filter, only 3 LAs remain: Merthyr Tydfil, Torfaen, Monmouthshire.**

---

### **Final Answer (pending Step 3 verification)**

**Definite candidates for Step 3 testing:**  
**Merthyr Tydfil, Torfaen, Monmouthshire**

You will need to pull the 25–44 age totals from the MYE2 tables for these three to determine which (if any) saw >2% growth mid-2021 → mid-2022.

*If you can access the MYE2 xlsx files, the calculation is straightforward. Would you like me to guide you through the exact column/row locations in those files?*
