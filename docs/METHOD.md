# Method 🌿

## Quantity of interest

The detector divides events into those it flags as containing an animal and those it calls negative. Scope Audit estimates the false omission rate of the negative pool: the share of negative events in which a human reviewer finds an animal. This is the quantity a data manager needs when empty looking images are removed from review. It differs from the miss rate, which divides by the number of animal events.

## Unit and pool

The unit is the event, a sequence of frames from one camera trigger. An event belongs to the negative pool at threshold T only when no frame carries an animal detection of confidence T or higher. Detector output is stored from a low floor so that the threshold can be varied afterwards.

## Review designs

Reviewers inspect a budgeted sample of negative events. Six designs are compared, all drawn without replacement.

- M0, simple random sample, with the Wilson interval and a finite population correction.
- M1, proportional allocation across image condition strata (night, low light, high blur, low resolution, normal). Strata come from image features only.
- M2p, proportional allocation across detector confidence strata, kept as a control for M2.
- M2, allocation across detector confidence strata in proportion to the stratum size times the bin midpoint plus a small constant. The rule was fixed before any label was read.
- M3, the same rule across confidence by night strata.
- M4, a two phase design: a pilot sample, then allocation that favours strata with uncertain pilot rates.

## Estimation

The stratified estimate weights each stratum rate by its share of the pool. Four interval types are reported: Wald with plug in variance, Wald with smoothed variance, a bootstrap, and a beta binomial interval added after the first calibration run (recorded as post hoc and exploratory in DECISIONS.md). Unresolved reviews, where a reviewer cannot decide, are never guessed: sensitivity bounds treat every unresolved event first as empty and then as an animal.

## Evaluation

Experiment A measures detector error on the full benchmark. Experiment B compares the designs on the benchmark working set across thresholds and budgets. Experiment C calibrates the estimators on populations with a known truth. All populations in experiment C are synthetic and labelled so. Predictions were committed before the experiments, and scripts/evaluate_predictions.py scores them without changes.

## Reproducibility

Each random draw uses a generator keyed by seed and design, so identical inputs, configuration and seed give identical sample identifiers. The environment is pinned in ENVIRONMENT.md.
