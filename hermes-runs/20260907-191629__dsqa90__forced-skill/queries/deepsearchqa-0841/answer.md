Now let me analyze the combined data to find the intersection.

## Analysis

**EU average GDP per capita (2019, World Bank): $35,374.15**

### Countries with MCV2 coverage below 90% (WUENIC 2019):
| Country | MCV2 Coverage | Below 90%? |
|---------|---------------|------------|
| Austria | 88% | ✓ |
| Belgium | 99% | ✗ |
| Bulgaria | 72% | ✓ |
| Czechia | 72% | ✓ |
| France | 86% | ✓ |
| Germany | 93% | ✗ |
| Italy | 88% | ✓ |
| Lithuania | 93% | ✗ |
| Poland | 91% | ✗ |
| Romania | 76% | ✓ |
| Slovakia | 72% | ✓ |
| Spain | 94% | ✗ |

### Countries with GDP per capita below EU average ($35,374):
| Country | GDP per capita | Below EU avg? |
|---------|----------------|---------------|
| Austria | $49,886 | ✗ |
| Belgium | $46,717 | ✗ |
| Bulgaria | $10,354 | ✓ |
| Czechia | $23,102 | ✓ |
| France | $40,408 | ✗ |
| Germany | $47,656 | ✗ |
| Italy | $33,813 | ✓ |
| Lithuania | $19,455 | ✓ |
| Poland | $15,875 | ✓ |
| Romania | $12,910 | ✓ |
| Slovakia | $19,406 | ✓ |
| Spain | $29,787 | ✓ |

### Intersection (meets BOTH criteria):
| Country | MCV2 < 90% | GDP < $35,374 | **Result** |
|---------|------------|---------------|------------|
| **Bulgaria** | 72% ✓ | $10,354 ✓ | **YES** |
| **Czechia** | 72% ✓ | $23,102 ✓ | **YES** |
| **Italy** | 88% ✓ | $33,813 ✓ | **YES** |
| **Romania** | 76% ✓ | $12,910 ✓ | **YES** |
| **Slovakia** | 72% ✓ | $19,406 ✓ | **YES** |

## Answer

**5 countries** from the ECDC 2019 list meet both criteria:

1. **Bulgaria** – MCV2 72%, GDP $10,354
2. **Czechia** – MCV2 72%, GDP $23,102
3. **Italy** – MCV2 88%, GDP $33,813
4. **Romania** – MCV2 76%, GDP $12,910
5. **Slovakia** – MCV2 72%, GDP $19,406

---

## Sources

1. EU average GDP per capita 2019: https://api.worldbank.org/v2/country/EU/indicator/NY.GDP.PCAP.CD
2. WUENIC MCV2 coverage 2019 (WHO GHO OData API): https://ghoapi.azureedge.net/api/MCV2
3. World Bank GDP per capita 2019 for each country: https://api.worldbank.org/v2/country/AT;BE;BG;CZ;FR;DE;IT;LT;PL;RO;SK;ES/indicator/NY.GDP.PCAP.CD
4. ECDC Measles 2019 Annual Epidemiological Report: https://www.ecdc.europa.eu/sites/default/files/documents/measles-2019-aer.pdf
