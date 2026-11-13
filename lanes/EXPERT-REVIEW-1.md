# EXPERT-REVIEW-1: why sign-offs stalled (276 at 11-13 03:00)

Read-only. Sources: `~/coord/lanes/SIGN-RATE.tsv`, `tools/failure_breakdown.py` (03:02), `autopilot/log.txt`, `autopilot/structural.tsv`, `lanes/TIMING-CLASS.tsv`, `lanes/STALE.tsv`, `lanes/VISUAL-QUEUE.tsv`, `lanes/GEOM-REVIEW.md`, `lanes/COORD-REVIEW-QUEUE.md`, `ot-run --status`.

**Verdict:** this is not a physical-design stall. Builds die in kit staging before any place and route, the survivors queue for a visual verdict, and plan events cancel the rest. The fleet is 13% loaded (120 of 896 threads, 70 jobs). The true count is worse than +8: +3 was a counter re-key (11-12 04:40 row), so real gain is +5, and the log has no `KIT-WAVE COUNTED` event after 11-09 20:30.

## Top 5 levers (next 48 h; gains are my estimates, not measurements)

1. **One batch fix for the kit staging classes, then relaunch. ~20-40 sign-offs.** Five signatures are 865 of 1,484 FAILs on 11-10..13 (58%): `KIT_NOT_SELF_CONTAINED` 438, "bind names HDL sources that are gone (pruned bind worktree)" 166, `KIT_TOPOLOGY_BIND_STALE` 121, `KeyError 'col_h…__pv…'` at gen 86, "gen phys: plan invalid" 54. All fail in under 1 h. Fix: the kit carries a content-addressed snapshot of src, bind and plan, made at enqueue. Cost: one tooling lane, about a day. Risk: low.
2. **Make the visual verdict gate sign-off, not route. ~10-20.** 45 builds are held now (27 S81, 9 KV); 425 of the ROUTE-HOLD events on 11-12/13 are WAIT-VISUAL. Verdicts arrive in bursts (about 93 on 11-12, about 2 on 11-10/11, none yet on 11-13). With 87% of threads idle, a wasted route costs nothing. The "1-in-5 sample, route already enqueued, FAIL demotes" mode already exists in GEOM-REVIEW.md; make it the default. This keeps the owner rule's wording (visual before sign-off). Risk: some routed BAD builds are thrown away.
3. **48 h plan-event freeze per die; builds past place finish. ~10-15 preserved.** See churn numbers below. Owner rules "re-floor, re-sign OK" and "comprehensive plan fix" are being applied as a licence for continuous events; re-sign is not fast when nothing reaches sign-off. Cost: none. Risk: a known plan defect lives two more days.
4. **Exempt live-kit inputs and STA reports from aggressive cleanup. ~5-10.** Cleanup causes the 166 pruned-bind failures, and TIMING-CLASS.tsv shows "run dir pruned / number not kept" on most rows, so failures are rebuilt instead of diagnosed. The owner's cleanup rule is the problem here; keep it, but add a `reports/` keep-set of a few MB per attempt.
5. **Cap retries at 3 per failure signature and send the item to a named owner. ~5 direct.** 4,769 launches on 534 items (8.9 each); 347 items have 5 or more; the worst has 47 (`qwen_compute/sle_su_l0__cl7a55c676`). STALE.tsv lists 253 items with no live job; 19 are unowned and 160 belong to "KIT-WAVE-1", which is a scheduler, not an owner.

## Q1. Where the time goes
Median LAUNCH-to-FAIL from the log, 11-09..13: bind 0.16 h (n=389), kit_rtl 0.15 h (340), kit_topology 0.34 h (192), gen 0.75 h (129), place 0.91 h, p90 4.7 h (329). Compute time is not the bottleneck: a type does not reach route. I could not time route or sign-off because almost nothing got there; RECORDED on 11-10..13 is 207 STRUCTURAL, 93 CRASH, 4 NEAR-MISS and no sign-off. The real waits are relaunch loops on staging errors, the visual hold (memory note: 46 builds waited about 6.5 h with no reviewer alive), and supersede.

## Q2. Unsigned items (about 464: 429 types, 35 cores)
- **Tooling, about 215 (46%)**: "other flow error" 154, kit_rtl 33, port mismatch 14, infra 14. I infer the 154 are mostly the lever-1 signatures; I did not map row by row.
- **Process, about 190 (41%)**: HBM types waiting on a child core 52, held for visual 45, cancelled-superseded 30, running 32, no kit-wave row 14, the rest stale or unowned.
- **True technical, about 50-60 (12%)**: timing after route 14, QC hold after CTS 7, HBM congestion/placement/macro cores about 11, PDN-0006 6, cell caps 3, LEC and lint about 10.

## Q3. Churn: yes
368 CANCEL-SUPERSEDED events on 205 items, plus 893 SUPERSEDED-KEEP, in 4.5 days. New events landed on 11-11 for QC (`hcut1111`, 1,278 launches), HBM (`hcut1111`) and HEAD (`l48uj`), then S81 (`7073a6b4a59`) on 11-12; the STALE list shows about 45 S81 leaf types "SUPERSEDED gen" in a single two-hour window (11-12 05:18-07:17). The 11-06..09 climb (+89) came from waves left alone for three days.

## Q4. What a PD lead would do differently
- **GRT overflow** (103 CLASSIFY events, the largest structural class): the visual notes keep finding the same thing, station columns in roughly 25 um alleys between macro and edge. Put a macro halo and edge street of at least 43 um in the generator as a family rule; lower density and pad cells near pin bars. Do not find it per type by eye.
- **Hold** (post-CTS 14, structural 9): allow `repair_timing -hold` with a buffer budget after CTS; check boundary hold at die STA on real views (owner rule 12.19), not as a block gate against ideal boundaries.
- **Slew/DRV** (about 100 structural.tsv reason hits; 381 ps leaf slew on `ot_hidx_s3_q`): flow settings. Smaller CTS sink clusters, a stronger leaf buffer, `repair_design` after GRT.
- **Setup**: `serdes__t2` at -870 to -1,076 ps and paths of 22-27 logic cells in 833 ps are RTL pipelining work. Stop rebuilding them (serdes is on attempt 27, `slice_station__t47` on 20).
- **Cell caps**: partition as now; no change.

## Busywork to cut
- 968 READY, 826 RESULT, 279 ASK and 278 RULING posts in 3.5 days for no kit-wave sign-off.
- 2,440 AUTO-RESIGN PRESTAGE events for 37 launches.
- Hourly forced counts that time out at 280-560 s.
- Paragraph-length visual verdicts on builds that then sit.
- HBM is phase 2 but holds 80 of the unsigned types: park it.

## Not checked
METHODOLOGY §12 and AGENTS.md were not read in full. Visual-verdict-per-day counts come from a rough grep. Sign-off gains are estimates from the 11-06..09 rate of about 30 per day.
