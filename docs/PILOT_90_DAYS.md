# Ninety day pilot plan 🌿

Everything numeric below is a TARGET proposed for agreement with the Ministry. None is a result. Roles, not named people, own each item.

## Roles

| Role | Responsibility |
| --- | --- |
| Sponsor, MOCCAE monitoring lead | Approves scope, data access and the final decision. |
| Data custodian, MOCCAE data and security team | Provides the hosting environment, access rules and the deployment registry. |
| Validator, field technician or species expert | Reviews sampled events and approves observations. Two validators take part. |
| Delivery engineer, Team IZZA | Installs, configures, fixes defects and runs the audits. |
| Statistical adviser, university or agency partner | Checks the sampling plan and the interval wording. |

## Timeline with milestones

| Week | Milestone | Output | Owner |
| --- | --- | --- | --- |
| 1 | Kickoff, scope and data access agreed | Signed scope note, list of pilot deployments, detector version named | Sponsor |
| 2 | Environment ready | System installed in the approved environment, roles configured, coordinate visibility rules set | Data custodian, delivery engineer |
| 3 | Registry loaded | Deployment registry with real coordinates and dates, integrity report on a first historical batch | Data custodian |
| 4 | Metadata corrected | Flags from the integrity report resolved or recorded as unresolved with reasons | Validator, data custodian |
| 5 | First detector run | Detector output stored from a low confidence floor for the pilot batch | Delivery engineer |
| 6 | First audit plan | Seeded review sample at the chosen threshold and budget, plan checked by the adviser | Delivery engineer, adviser |
| 7 | Reviewer training | Both validators trained on animal, empty and unresolved, with a shared practice set | Validator |
| 8 | First audit reviewed | Reviews recorded, first false omission estimate with interval and bounds | Validators |
| 9 | Agreement check | Both validators review the same shared subset, agreement measured | Validators, adviser |
| 10 | Design comparison | Simple random against confidence strata on the pilot batch, using the benchmark code | Delivery engineer |
| 11 | Threshold study | Estimate repeated at more than one threshold, cost of review against hidden events found | Delivery engineer |
| 12 | Export test | Approved observations exported as Camtrap DP and read by a partner system | Data custodian |
| 13 | Decision | Decision memo and a report that states every miss against the targets | Sponsor, delivery engineer |

## Exit criteria (TARGETS)

1. Integrity: every pilot deployment has coordinates and dates, and the share of images with unresolved flags is reported.
2. Precision: the false omission estimate for the chosen threshold has an interval half width of at most one percentage point with a budget of no more than 800 events, or the report states what budget would be needed.
3. Reviewer agreement: the two validators agree on animal or empty for at least nine of ten shared events. A lower figure is reported and the audit design is revised.
4. Effort: review minutes per event are measured, and the report states the total review time for the audit against the time needed to screen the filtered images in full.
5. Interoperability: the exported package validates against the Camtrap DP schemas and a partner system reads it without manual repair.
6. Honesty: the report lists each target as met or missed with the measured value.

## Dependencies and risks

| Risk | Effect | Response |
| --- | --- | --- |
| Data access approval is slow | Weeks 3 to 5 slip | Start the approval request before week 1, use the benchmark for rehearsal meanwhile |
| Detector version changes | Estimates not comparable | Fix and record the version for the whole pilot |
| Few validators available | Review budget not met | Reduce the budget, report the wider interval |
| Cameras with missing dates | Effort aware summaries unusable | Report encounter rates only for valid deployments |
| Local detector behaviour differs from the benchmark | Threshold advice from the benchmark fails | The pilot exists to measure this, and the report says so |

## Failure is allowed to be reported

If a target is missed, the report says which one, what the data showed, and what would change in the next phase.
