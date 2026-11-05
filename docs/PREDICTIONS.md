# Predictions and success criteria

Registered before any experiment was run. The predictions below are fixed. They are never edited after results exist. Misses are reported as plainly as hits.

## Facts known before any experiment

1. The benchmark data (Caltech Camera Traps) is part of the public training data of earlier MegaDetector versions (see docs/PRIOR_ART.md). The detector may therefore perform better on it than on unseen data.
2. The benchmark is from the Southwestern United States and is borrowed. No UAE camera trap data are used.
3. About 70 percent of benchmark images are labelled empty (data page statement, to be confirmed by our own count).

## Regimes and design rules fixed in advance

- Unit of analysis: the event (sequence). Negative pool at threshold T: events with no animal detection at confidence T or higher in any frame.
- Threshold sweep: 0.1, 0.2, 0.4, 0.6, 0.8. Headline regime: T of 0.2.
- Stress regime rule: the smallest threshold in the sweep at which benchmark event FOR is at least 2 percent, or the largest threshold if none reaches it.
- Budgets: 50, 100, 200, 400 and 800 events. Seeds: 1000 for experiment B and 5000 for experiment C.
- M2 allocation rule fixed before any label is read: n_h proportional to W_h times (bin midpoint plus 0.02).
- Power rule: if fewer than 30 hidden animal events exist in a pool, the regime is reported as underpowered and no claim is made from it.

## Predictions

- P1 On the benchmark at T of 0.2, event level FOR is below 3 percent.
- P2 In the stress regime, M2 finds at least 1.5 times as many hidden animal events per 100 reviews as M0 at budgets 100 to 400.
- P3 Condition only strata (M1) find less than 1.3 times the M0 yield, and the interval of the ratio includes 1.0 for at least one budget.
- P4 M3 yield is within 10 percent of M2.
- P5 The stratified plug in estimator has mean error within 0.25 percentage points of the truth at budgets of 200 or more in the stress regime.
- P6 Wald plug in stratified intervals undercover (below 93 percent) in at least one setting because of zero count strata; the smoothed variance or bootstrap intervals reach 93 to 97 percent at budgets of 400 or more.
- P7 Simple random Wilson intervals with finite population correction cover between 93 and 97 percent at budgets of 200 or more when FOR is at least 1 percent.
- P8 Identical inputs, configuration and seed give identical sample IDs in 100 percent of runs.

## Success criteria

- S1 P2 holds.
- S2 The recommended estimator covers 93 to 97 percent.
- S3 P5 holds.
- S4 P8 holds.
- S5 The claims lint passes.

If S1 fails, the superiority claim is removed from every document and the first line of results/RESULTS.md says so.
