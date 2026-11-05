# Limitations 🌸

1. The benchmark images come from the southwestern United States. No camera trap data from the United Arab Emirates were used, and no result transfers to the Emirates without a pilot.
2. The benchmark was part of the public training data of earlier detector versions. Absolute error rates are therefore likely to be optimistic. Relative comparisons between sampling designs are less affected, but this has not been tested on unseen data.
3. The reviewer in the experiments is an oracle that reads benchmark labels. Human reviewers disagree and tire. The unresolved category and the sensitivity bounds cover part of this, and no reviewer agreement study was run.
4. The rate is estimated for events, not for individual animals and not for species.
5. The estimate describes a pool at one threshold. It does not describe how many animals live in an area, how many are present, or whether a species is absent.
6. Deployment coordinates in the demo are synthetic placeholders. The export is valid against the Camtrap DP table schemas, but a real registry is required before any real export.
7. The candidate species list was built from GBIF occurrence records. It has not been approved by an expert and may contain errors or species unsuited to camera traps.
8. The beta binomial interval was added after a first calibration run and is exploratory.
9. The software has not been tested with real field volumes, with very large data sets, or with several simultaneous reviewers.
10. Species classification is not included. An adapter interface exists, and nothing is bundled.
