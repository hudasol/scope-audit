# Decisions

Decisions taken during the build, with the reason for each.

1. Benchmark choice. Caltech Camera Traps (CDLA permissive, labels with sequence identifiers, locations and timestamps) is the primary benchmark because published MegaDetector results exist and it has about 70 percent empty images, so a negative pool exists.
2. Known leakage. The data page and the detector documentation state that Caltech Camera Traps was used to train earlier MegaDetector versions. Absolute error rates on it are treated as optimistic. This was recorded in docs/PRIOR_ART.md before any experiment.
3. Desert Lion Conservation Camera Traps was checked and not used for experiment B. It is arid but has no images labelled empty, so the truth for blank predictions cannot be estimated without selection bias.
4. Detector results. The published MegaDetector v5a results file from LILA is ingested in place of running inference. No heavy inference is run in this build.
5. Event definition. Events are the sequences given by the dataset sequence identifier. An event is AI negative at threshold T only if every frame has no animal detection at confidence T or higher.
