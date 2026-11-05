# Prior art and gap check

Time boxed review written before any experiment. Each statement is marked VERIFIED (read in a source during this build) or UNVERIFIED (recalled, not re read). Claims in this repository are limited to what this review supports.

## 1. What already exists

| Topic | Finding | Status | Source |
|---|---|---|---|
| Blank filtering and review of blanks in Wildlife Insights | The platform recommends reviewing images marked blank in bulk through thumbnail pages. It states that the model may occasionally mark an image blank when an animal is present. This is manual checking of all blanks, not a designed sample with an interval. | VERIFIED | Wildlife Insights announcements (Apr 2022, Nov 2022), groups.google.com/g/wildlifeinsights |
| Blank class confidence rule | Wildlife Insights shows "No CV Result" below stated confidence levels, including a high level for blanks. | VERIFIED | wildlifeinsights.org/node/3922 |
| SpeciesNet | Open source ensemble (Apache 2.0) that runs MegaDetector first, then classifies the detected animal. Not a sampling or audit tool. | VERIFIED | github.com/google/cameratrapai |
| MegaDetector | Open source detector of animals, people and vehicles. It does not name species. Licence depends on the model variant. | VERIFIED | microsoft.github.io/MegaDetector |
| MegaDetector accuracy varies strongly by dataset | Published evaluations report occupied image recall from about 62 percent to about 95 percent across datasets, and a provincial report states that a cautious threshold removed 38 percent of images at the cost of missing 1.4 percent of occupied images. These figures come from full manual comparison, not from a sampling design. | VERIFIED (abstract level) | digitalcommons.odu.edu (poster abstract); publicdocs.mnr.gov.on.ca TR 66 |
| Evaluating platforms with manual checks | A review of Wildlife Insights, MegaDetector, MLWIC2 and Conservation AI provides code to evaluate AI performance against manual labels. | VERIFIED (abstract level) | arxiv.org/abs/2202.02283 |
| Camtrap DP | Open standard for camera trap data exchange with deployments, media and observations tables. Observations can be media level or event level. The observation type vocabulary includes animal, human, vehicle, blank, unknown and unclassified. | VERIFIED | Bubnicki et al. 2024, doi 10.1002/rse2.374; tdwg/camtrap-dp observations schema |
| Detector training data overlap | MegaDetector was trained in part on public datasets. Caltech Camera Traps is listed among the public data used since MegaDetector v3. LILA states that its published MegaDetector results should not be used to evaluate detector accuracy for this reason. | VERIFIED | github.com/agentmorris/MegaDetector megadetector.md; lila.science/megadetector-results-for-camera-trap-datasets |

## 2. Statistical prior art (important for honesty about novelty)

| Topic | Finding | Status |
|---|---|---|
| Stratified sampling for estimating classifier performance under a labelling budget | Established. Bennett and Carvalho (2010), Kumar and Raj (2018, PAKDD) and others derive stratified and optimal allocation estimators and show variance reduction against random sampling for accuracy. | VERIFIED (abstract level) |
| Importance sampling for risk and F score estimation | Established. Sawade et al. (2010) active risk estimation; Poms et al. (2021) low shot validation with active importance sampling for rare categories. | VERIFIED (abstract level) |
| Estimating false negatives of a detector with few labels | A paper on interactive detector testing states that random sampling severely underestimates false negatives when objects are rare, and proposes probabilistic methods. This supports the need for risk aware sampling when misses are rare. | VERIFIED (abstract level), arxiv.org/abs/1406.5653 |

## 3. Gap statement supported by this review

The statistical machinery (stratified and importance sampling for estimating error with limited labels) is not new. We do not claim a new estimator.

What this review did not find, within a short search: a free, reproducible protocol and tool, specific to camera trap workflows, that (a) works at the event level rather than the image level, (b) draws a seeded, documented review sample from the detector negative pool, (c) returns an interval for the hidden animal rate, (d) keeps the original machine result, the audit decision and the approved observation as separate append only facts, and (e) exports controlled records in Camtrap DP with a separate audit package. Absence of evidence from a short search is not proof that no such tool exists. Treat the gap as UNVERIFIED beyond this search.

The defensible contribution is therefore an applied, honest, reproducible workflow, with a measured test of whether detector confidence aware allocation finds more hidden animals per review than random sampling.

## 4. Claims downgraded by this review

1. No new statistical method is claimed.
2. No claim that existing platforms lack auditing; only that the guidance found is manual review of all blanks.
3. No UAE accuracy claim. No UAE camera trap data were used.
4. Because Caltech Camera Traps is part of the MegaDetector training data, the absolute error rates measured on it are likely optimistic and are reported as such. The method comparison remains informative about the sampling designs, but not about expected error rates in a UAE deployment.
5. UAE monitoring programme statements (for example Arabian Tahr or Hatta reserve camera trapping) were not verified in this build and are not used as evidence.
