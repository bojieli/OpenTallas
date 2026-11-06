# HBM parent q_spb2 — current handoff

Updated 2026-11-06. Owner: hbm_parent. Canonical plan/calendar: hbm. **Bounded real-child CTS diagnostic complete; PARKED after Claude reset; no live jobs, route or parent/die signoff.** ROOT=/srv/opentallas-scratch2/claude/codex-hbm-parent-1106.

## Actual result

Intel2 PLACE unit **oth-ubuntu-2114046-1793976245** finished exit 0. Final DB ROOT/prep3_reset_paths/gen/q_spb2/run/results/asap7/dp_q_spb2/base/3_place.odb. Own-run LEC EQUIVALENT:45,403/45,403 points, zero differences/undecided. Actual frontend retained2/2 signed xcal instances and20/20 station instances. DPL violations0.

Reset placement PASS: relayed entry/depth8,103 entry/relay FFs, zero missing/overreach, max380.7µm<=405. Both hard reset pins resolve to taps21/22. Source retains23 native taps.

All4,269 required bank FFs present; six input epochs are proved unobserved. Every payload bank FF retained its planned site; observed epoch movement max1.566µm. Actual hops (µm): L49=394.686,L83=340.623,L75=268.218,L76=272.106,L87=307.260,L40direct=184.896; all<=403, no missing endpoints. Soft interface centers moved up to27.648µm; recheck8.314µm remaining margin after CTS/hold repair/route. All1,770 actual soft-interface sites exported.

Actual image viewed. Zero standard-cell rectangle overlap with macro bodies; zero new station-FF overlap with4.32µm macro clearance.836 other cells (mostly buffers,7FFs) lie within that expanded outline; owner confirms station/allocation clearance is not an undeclared universal keepout. Owner also accepts two data buffers occupying one unused epoch allocation as a capacity reservation; no dummy state/clock load.

## Current CTS result and next step

HBM owner explicitly approved CTS-only continuation. Intel2 unit **oth-ubuntu-741506-1793982726** completed exit 0 at ROOT/cts1/gen/q_spb2. Canonical resume reused immutable PLACE; exact shared completed-LEC transfer retained 45,403 equivalent points. No routing occurred.

Actual calibrated post-CTS estimates: TT setup **−189.03 ps**, FF hold **−244.05 ps** (14,276 negative endpoints). Structural hold guard passes its −260 ps threshold; this is not actual hold closure. Pin-register clock range TT222.45–408.66 ps / FF184.28–340.69 ps, means289.52/235.84 versus targets250/202.5. Ordinary t16/t17 have8,360/6,448 sinks; t17 spans320–488 ps. Hard-child clock report decomposes pin0+ETM max-bound399.59=effective~400 ps versus250 target; current early shift is0. core_latency marks this legacy_etm_max_bound, signed=false/release_qualified=false; do not adopt it as a signed mean contract. Full ordinary and both hard clocks retained.

Post-CTS all4,269 required bank FFs remain present; no missing/extra payload. Worst payload reach stays L49=394.686µm<=403; L40 changes only to185.166µm. No geometry repair is justified by these measurements. E2 diagnostic unit3194827 finished0; exact failing TT/FF path extraction unit3207298 finished0 in ROOT/postcts_capsule. Exact setup is Q3 kv_desc[17] falling→first L76 bank(−189.032); first hop261.501µm adds114.30ps after529.49ps C→Q. Exact FF hold is L83final bit26(t16)→softQ3 act_q[1](t17):98.73ps actual cross-tap skew plus160ps source window and52.65ps data. Next: qualified child clock reference, heavy-tap repair, first-output-bank timing optimization, actual hold repair. Hbm owns canonical geometry/calendar. No route authorized.

Pre-CTS calibrated TT+39.911ps and stock DPL−7.275ps are preserved. Upstream DPL overrode calibrated RC; wave_flow owns generic future-only fix f7747f4351. CTS used calibrated RC. HBM40 shell/reset phase and HBM42 calendar remain conditional; L75+8,L76+5,L49+3,L83+3,L87+1,L40+0 is not+20 per operation. Canonical event belongs hbm.

## Artifacts and fixes

ROOT/prep3_reset_paths/{RESULTS.md,actual_placement.png,actual_bank_landing.json,actual_payload_reach.json,actual_soft_interface_sites.json,actual_halo_check.json,prep3_timing.log}. Local copies coord/tmp/codex-hbm-parent-1106/prep3_actual. E2 dedicated scratch2 ROOT/postplace_capsule is a490MB read-only diagnostic copy; measurement2373155 and calibrated STA2412092 finished0. Original Intel2 load-wait measurement was cancelled unstarted, ACK NOT RUN.

Shared fixes are released:5736 schema;913 dead-input structural reproof+563 explicit partition inventory (28fc/bj);1bee idempotent bound reset output+6045 source-proved unused epoch handling (7d323/bq);1967 authoritative reset-target projection, isolated46a/main1f23/HBM-bv. Focused actual mutants/refusals passed. Current own branch codex/hbm-parent-resume-1106, Intel2 wt/codex-hbm-view-stage-1106. No main merge by this lane.

Scope stays LOCAL_COMPONENT/source_preparation_only. Original g_t11m79f unrelated q_hub_nw globalFAIL1 remains visible; no native/global PASS stamp or borrowed top. Original m79fp reset context and actual signed views remain unchanged. SU native/signed phase join belongs hbm; no false old plain4 route.

Own cleanup removed3.189GB apparent duplicate failed intermediate ODBs plus earlier~0.74GiB abandoned copies. Each final failed DB, mapped netlist, source/log/receipt and current result are preserved; no healthy job killed. Canonical resume conservatively required FULL for reset Tcl changes; no classifier waiver.

## Claude reset handback

Parked on HBM owner instruction; all own jobs finished, no new launch or mutation. SOURCE: ROOT/prep3_reset_paths/gen/q_spb2 (immutable original PLACE); CTS: ROOT/cts1/gen/q_spb2; exact measured path logs and TT/FF JSON: E2 dedicated ROOT/postcts_capsule/{cts_paths_TT.log,cts_paths_FF.log,postcts_gate_tt.json,postcts_gate_ff.json,actual_bank_landing.json}. Local actual geometry/reach/path logs: coord/tmp/codex-hbm-parent-1106/cts1_actual. Final path unit3207298 finished0.

**No early150 clock update, clock-plan change, or bank geometry change adopted.** ETM rise399.59/fall431.11 is UNSIGNED legacy MAX-bound, not mean. Actual historical signed child report at Intel2 /srv/opentallas-scratch2/claude/die-hbm-72/resign/xcal/signoff/signoff.json has mean TT325.113421/FF262.961909, spreads149.37/141.0 marked info-only; it does not establish current<=80ps clock closure. Preserve exact per-bit ETM timing and old advisory scope. Proposed geometry/tap repairs remain unadopted suggestions. TT−189.03/FF−244.05 are real open timing; geometry/reach positive. Original globalFAIL1/LOCAL component scope unchanged.
