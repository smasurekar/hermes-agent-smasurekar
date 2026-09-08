# Research Plan: 2023 Romance Books Meeting Canadian & NYT Bestseller Criteria

## Goal
Identify all romance books released in 2023 that were (a) in the top 10 most sold fiction books in Canada by print sales volume, AND (b) appeared on the NYT "Combined Print & E-Book Fiction" bestseller list for more than 20 consecutive weeks in 2023.

## Components
1. **Canadian 2023 Fiction Bestsellers (Print)** — Source the official top 10 print fiction bestsellers in Canada for 2023 (BookNet Canada, Toronto Star, Globe & Mail, or Nielsen BookScan Canada).
2. **NYT Combined Print & E-Book Fiction 2023 Weekly Lists** — Obtain weekly NYT bestseller data for "Combined Print & E-Book Fiction" throughout 2023 to track consecutive-week runs.
3. **Romance Genre Classification** — Verify which of the intersecting titles are categorized as romance (industry BISAC codes, publisher classification, retailer tags).
4. **Cross-Reference & Filter** — Match titles across both lists, verify 2023 publication date, confirm >20 consecutive weeks on NYT list.

## Constraints
- Output: List of qualifying books with title, author, Canadian rank, NYT consecutive weeks, publication date.
- Only 2023 releases (not backlist titles surging in 2023).
- "Romance" = core genre romance, not romantic subplot in other genres.
- Sources must be verifiable (industry reports, archived bestseller lists).

## Queries

| # | Query | Depth | Component |
|---|-------|-------|-----------|
| 1 | "Canada 2023 top 10 fiction bestsellers print sales BookNet Canada Nielsen" | high | 1 |
| 2 | "New York Times Combined Print E-Book Fiction bestseller list 2023 weekly archive" | high | 2 |
| 3 | "2023 romance novels New York Times bestseller 20+ weeks consecutive" | medium | 2, 3 |
| 4 | "BookNet Canada 2023 annual bestseller report fiction print" | high | 1 |
| 5 | "Toronto Star Globe Mail 2023 Canadian bestseller list fiction top 10" | medium | 1 |