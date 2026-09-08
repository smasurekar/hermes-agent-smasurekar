# Research Plan: Highly Commercial Fish Species in Japan (FishBase)

## Goal
Identify every fish species in Japan that has "highly commercial" designation in both the "use" column and "use elsewhere" column according to FishBase (fishbase.org).

## Components
1. **FishBase data structure** - Understand how FishBase organizes species data, country distributions, and commercial use categories
2. **Japan fish species list** - Get all fish species recorded in Japan from FishBase
3. **Commercial use classification** - Identify the "use" and "use elsewhere" columns and their "highly commercial" values
4. **Filtering logic** - Cross-reference species with both columns = "highly commercial"
5. **Output format** - FishBase Name and species for each qualifying fish

## Constraints
- Source: fishbase.org only
- Must have "highly commercial" in BOTH "use" AND "use elsewhere" columns
- Geographic scope: Japan only
- Output: FishBase Name + species (scientific name)

## Queries

### Query 1 (High depth): FishBase Japan species list with commercial use data
**Goal**: Find how to query FishBase for all fish species in Japan with their "use" and "use elsewhere" commercial designations
**Approach**: Search for FishBase API, country species lists, commercial use categories, or downloadable datasets

### Query 2 (High depth): FishBase commercial use classification definitions
**Goal**: Understand what "highly commercial" means in "use" vs "use elsewhere" columns
**Approach**: Search FishBase documentation, glossary, or data field definitions

### Query 3 (Medium depth): Existing compiled lists or research papers using FishBase Japan commercial data
**Goal**: Find if anyone has already compiled this specific filter (Japan + highly commercial in both columns)
**Approach**: Search academic papers, fisheries reports, or data analyses using FishBase Japan commercial data

### Query 4 (Medium depth): FishBase database access methods
**Goal**: Determine if there's an API, SQL dump, CSV export, or web query interface for this data
**Approach**: Search for FishBase API, R package (rfishbase), Python access, or bulk download options

### Query 5 (Low depth): FishBase "use" vs "use elsewhere" column distinction
**Goal**: Clarify the difference between these two commercial use fields
**Approach**: Search FishBase field definitions or user guides