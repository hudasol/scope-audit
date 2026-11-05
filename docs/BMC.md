# Business model canvas 🌸

Every estimate here is an ASSUMPTION to verify with the Ministry and its procurement rules. No price, market size or revenue figure is claimed, because none was sourced.

## Canvas

| Block | Content |
| --- | --- |
| Customer segments | Primary: MOCCAE monitoring and conservation teams. Secondary: emirate environment agencies that run camera traps, protected area managers, conservation NGOs and research groups that need defensible records. |
| Value proposition | A measured, defensible statement of what an automated filter hides, a smaller review burden aimed where hidden animals are most likely, an audit trail from machine suggestion to approved record, and Camtrap DP export that other biodiversity systems accept. It is the audit layer in front of any species classifier. |
| Channels | Direct pilot with the Ministry, introductions through other emirate agencies and conservation partners, open source release, and the Camtrap DP and GBIF community. |
| Customer relationships | Pilot support, reviewer training, a written method that auditors can inspect, and a report of misses against targets. |
| Revenue streams | Candidates, in order of fit with a public body: a funded pilot from an innovation or digital programme budget, an annual support and hosting agreement per programme, and training for review teams. The core stays open source under the MIT licence, so revenue comes from support and delivery and not from licences. Prices to verify. |
| Key resources | The statistical engine, the review log, the export module, the benchmark evidence, and a delivery engineer. |
| Key activities | Pilot delivery, calibration on local data, maintenance, standards alignment and reviewer training. |
| Key partners | The Ministry data and security teams, an adviser for sampling and interval wording, detector and classifier authors, and field teams. |
| Cost structure | See the estimate below. |

## Cost estimate (ASSUMPTION, in effort not money)

| Item | Effort for the ninety day pilot |
| --- | --- |
| Delivery engineer | Full time for thirteen weeks |
| Statistical adviser | One day a week for the first ten weeks |
| Two validators | A few hours a week each, mostly in weeks 7 to 11 |
| Data custodian | Part time in weeks 1 to 4 and week 12 |
| Hosting | Inside the Ministry approved environment, so no new hosting purchase assumed |
| Software licences | None, all components are free and open source |

Converting effort to money needs rates the team has not been given.

## Why the model connects

The value proposition addresses one user group, the monitoring team that must defend filtered data. The channel is a pilot because trust in the audit comes from running it on the user data. The resources and activities are the ones that pilot needs, and the revenue streams follow the same relationship: pilot first, support and training after.

## Assumptions that must hold

1. The Ministry or a partner can supply camera trap images and a deployment registry for a pilot.
2. Validators can give the review hours the audit needs.
3. The detector already in use, or a free one, produces confidences that the audit can stratify on.
4. A public body will pay for support and delivery around open source software.

Each has a first check in the ninety day plan.

## Risks and dependencies

| Risk | Response |
| --- | --- |
| Data access is slow or refused | Rehearse on the benchmark and plan the pilot around the data that is released |
| Local detector behaviour differs from the benchmark | Measure it in the pilot and report it |
| Reviewer capacity is short | Reduce the budget and report the wider interval |
| The Ministry prefers a full custom platform | Offer the audit layer and the export as modules with open formats |
| Procurement rules block a small supplier | Deliver through a partner or an innovation programme route |

## Scaling and impact

Scale by repeating the audit per detector version and per programme, then across emirates that use Camtrap DP. Measures of impact: review hours saved against full screening, the gap between the estimated and the audited false omission rate, share of approved observations exported with full provenance, and time from image batch to approved record. Each is measured in the pilot, not claimed here.
