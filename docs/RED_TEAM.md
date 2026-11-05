# Red team: five objections and our answers 🌸

## 1. A detector audit by sampling is old news.

Agreed, and we do not claim a new statistical method. Stratified and importance sampling for classifier evaluation under a labelling budget is established, and PRIOR_ART.md lists the sources. The contribution is a tested application to camera trap event pools, with the false omission rate as the quantity, calibrated intervals, honest handling of unresolved reviews, and an approval trail. Whether risk weighting wins on this benchmark is a prediction that results/RESULTS.md reports as held or missed.

## 2. The benchmark was in the detector training data, so the numbers are flattering.

Correct, and it is stated in LIMITATIONS.md and DECISIONS.md. Absolute error rates are probably optimistic. The pilot is designed to produce an unflattering local number. Relative comparisons between sampling designs depend less on this, and the claim is limited accordingly.

## 3. Your reviewer is an oracle. Real reviewers make mistakes.

True. The oracle isolates the sampling and estimation question. The unresolved category and the sensitivity bounds show how conclusions move when reviews fail, and the pilot measures disagreement between two reviewers on a shared subset.

## 4. Southwestern United States images say nothing about the Emirates.

They do not, and the product never claims they do. The images exist to test the software on real camera trap data with expert labels. Desert camera trap data from the Emirates were not available to us, and nothing in the repository is labelled otherwise.

## 5. A rate in a pool is not wildlife monitoring.

Agreed. The product audits the data pipeline that feeds monitoring. It makes no statement about how many animals exist, where a species lives, or whether a species is gone. The effort aware summary reports encounter rates per valid camera day, with a notice repeating this.
