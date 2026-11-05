# Open data check for Challenge 34 🌿

A short search on 6 November 2026 asked whether UAE government open data exists that a wildlife monitoring audit could use. Status words: VERIFIED means read in a source during this check at snippet or page level, UNVERIFIED means inferred and not read.

## Findings

| Source | What it offers | Status |
| --- | --- | --- |
| Bayanat.ae, the national open data portal | Federal and emirate datasets in machine readable formats, with environment among the sectors. A short search found no public camera trap image dataset on it. | VERIFIED for the portal, UNVERIFIED on whether any wildlife dataset exists there |
| Abu Dhabi Spatial Data Infrastructure open data service | A protected areas layer managed by the Environment Agency Abu Dhabi, with area type, status and purpose, usable to place a deployment inside a protected area. | VERIFIED |
| GBIF and Camtrap DP | Camera trap datasets published as Camtrap DP and registered with GBIF are discoverable through the GBIF interface. Mammal occurrence records for the UAE are available for the candidate species list. | VERIFIED |
| Abu Dhabi Global Environmental Data Initiative | A GBIF hosted repository for biodiversity data from environmental impact assessments in West Asia. | VERIFIED |
| Environment Agency Abu Dhabi camera trap programme | A monitoring programme running since 2011 that has recorded rare mammals. No public image dataset was found. | VERIFIED at news report level |
| Emirates Nature-WWF Wildlife Scanner | A volunteer programme that classifies camera trap images on a citizen science platform. Its published figures are used for the workload context below. | VERIFIED at report level |

## What this means for the solution

1. No public UAE camera trap image set was found, so the software was tested on the borrowed benchmark and the repository says so everywhere. A pilot needs the Ministry or a partner to supply images under its own access rules.
2. The export follows Camtrap DP, which is the route into GBIF, so approved observations can join the open biodiversity record without a new format.
3. The Abu Dhabi protected areas layer and the Bayanat portal are the open sources to use for the deployment registry and the sensitive location rules in the pilot. They were not used in this build.
4. The workload context is a published figure set (see data/reference/uae_context_figures.json): a volunteer programme reported many thousands of images from a few dozen cameras in one year, of which volunteers classified only part. This shows the screening burden and the need to know what filtering leaves out. It is one programme, not a national figure.

## Not checked

The Dubai and other emirate portals, the MOCCAE own data holdings, and any restricted dataset. Access to restricted data needs the entity, and none was requested.
