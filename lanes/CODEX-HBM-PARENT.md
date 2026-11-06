# HBM parent q_spb2 — current handoff

Updated 2026-11-06. Owner: hbm_parent. Canonical plan/calendar: hbm. **Bounded real-child PLACE diagnostic complete; no live job, no route, no parent/die signoff.** ROOT=/srv/opentallas-scratch2/claude/codex-hbm-parent-1106.

## Actual result

Intel2 PLACE unit **oth-ubuntu-2114046-1793976245** finished exit 0. Final DB ROOT/prep3_reset_paths/gen/q_spb2/run/results/asap7/dp_q_spb2/base/3_place.odb. Own-run LEC EQUIVALENT:45,403/45,403 points, zero differences/undecided. Actual frontend retained2/2 signed xcal instances and20/20 station instances. DPL violations0.

Reset placement PASS: relayed entry/depth8,103 entry/relay FFs, zero missing/overreach, max380.7µm<=405. Both hard reset pins resolve to taps21/22. Source retains23 native taps.

All4,269 required bank FFs present; six input epochs are proved unobserved. Every payload bank FF retained its planned site; observed epoch movement max1.566µm. Actual hops (µm): L49=394.686,L83=340.623,L75=268.218,L76=272.106,L87=307.260,L40direct=184.896; all<=403, no missing endpoints. Soft interface centers moved up to27.648µm; recheck8.314µm remaining margin after CTS/hold repair/route. All1,770 actual soft-interface sites exported.

Actual image viewed. Zero standard-cell rectangle overlap with macro bodies; zero new station-FF overlap with4.32µm macro clearance.836 other cells (mostly buffers,7FFs) lie within that expanded outline; owner confirms station/allocation clearance is not an undeclared universal keepout. Owner also accepts two data buffers occupying one unused epoch allocation as a capacity reservation; no dummy state/clock load.

## Timing and remaining scope

Fresh same-DB TT reload with calibrated RC,833ps/setup0/hold25, gives worst setup **+39.911ps**,TNS0, on soft Q3 fault_r feedback. Stock DPL report gives−7.275ps on the same path because upstream detail_place.tcl re-sources stock platform RC after calibrated load. Wave_flow owns the future-only generic correction; both reports retained. Modeled250ps clock insertion/zeroed pre-CTS delivery windows are not measured CTS clocks; FF hold is unqualified.

**OWNER? recorded:** extend prior PLACE-only scope to bounded CTS plus TT setup/FF hold and actual clock-interface measurements, without route/global/calendar adoption. No blocking dialog or wait. HBM40 signed-shell/reset phase and HBM42 per-bus calendar remain conditional. Stage vector L75+8,L76+5,L49+3,L83+3,L87+1,L40+0 is not+20 per operation. Canonical event belongs hbm.

## Artifacts and fixes

ROOT/prep3_reset_paths/{RESULTS.md,actual_placement.png,actual_bank_landing.json,actual_payload_reach.json,actual_soft_interface_sites.json,actual_halo_check.json,prep3_timing.log}. Local copies coord/tmp/codex-hbm-parent-1106/prep3_actual. E2 dedicated scratch2 ROOT/postplace_capsule is a490MB read-only diagnostic copy; measurement2373155 and calibrated STA2412092 finished0. Original Intel2 load-wait measurement was cancelled unstarted, ACK NOT RUN.

Shared fixes are released:5736 schema;913 dead-input structural reproof+563 explicit partition inventory (28fc/bj);1bee idempotent bound reset output+6045 source-proved unused epoch handling (7d323/bq);1967 authoritative reset-target projection, isolated46a/main1f23/HBM-bv. Focused actual mutants/refusals passed. Current own branch codex/hbm-parent-resume-1106, Intel2 wt/codex-hbm-view-stage-1106. No main merge by this lane.

Scope stays LOCAL_COMPONENT/source_preparation_only. Original g_t11m79f unrelated q_hub_nw globalFAIL1 remains visible; no native/global PASS stamp or borrowed top. Original m79fp reset context and actual signed views remain unchanged. SU native/signed phase join belongs hbm; no false old plain4 route.

Own cleanup removed3.189GB apparent duplicate failed intermediate ODBs plus earlier~0.74GiB abandoned copies. Each final failed DB, mapped netlist, source/log/receipt and current result are preserved; no healthy job killed. Canonical resume conservatively required FULL for reset Tcl changes; no classifier waiver.
