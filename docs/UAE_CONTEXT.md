# Context for the Ministry of Climate Change and Environment 🌷

Challenge 34 asks for AI powered wildlife monitoring. A camera trap programme produces many images and most of them are empty. A detector can remove empty images from human review, and the programme then needs to know what it lost. Scope Audit answers that question with a rate and an interval, and it keeps the audit trail that a government programme needs.

## What the product gives the Ministry

- A budgeted human review of the images the detector called negative, designed to find hidden animal events efficiently.
- An estimate of the false omission rate with an interval and a statement of what the interval does and does not cover.
- Deployment integrity checks that report what the data show about gaps and metadata, without asserting what happened to a camera.
- An approval gate: only human approved observations leave the system, as a Camtrap DP package that other biodiversity systems can read.
- Role based visibility of coordinates, so that precise locations of sensitive species are not shown to every user.

## What it does not do

It does not estimate how many animals exist, where a species is present, or whether a species is gone. Those claims need survey design and effort data that a detector audit cannot supply.

## Alignment

The export follows the Camtrap DP standard from the biodiversity data community. Any use of national data requires the Ministry to decide who owns, hosts and may view it. No such data were touched in this build.
