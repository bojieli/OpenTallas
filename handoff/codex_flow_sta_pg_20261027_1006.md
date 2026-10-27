# Interim FLOW / STA / PG / S81 PHY packet — 2026-10-27 10:06 PDT

This is an interim packet, not a stop/reset acknowledgment. All owned heavy jobs
are terminal; no half-written source or merge remains.

## S81 native PHY

Branch `codex/s81-phy-digital-1027@b107118ca` pushed to GitHub AND intel2 hub.
- `dbeb4611f`: native parent synthesis preparation + real digital sizing.
- `3f0a76341`: fixes component bench clock quantization. Original 1ps precision
  rounded both clocks to 834ps (0ppm). Corrected fixture measures core833.000ps,
  peer833.250ps = 300.120ppm; zero-offset mutant fails the period assertion.
- `b107118ca`: opt-in actual physical pin-stage model and real digital view aliases.
  Default RTL/plans remain unchanged.

Actual source is `ot_pdie_serdes_col`, with six real digital hard views and TWO
analog-only PMA models. No whole-PHY/controller blackbox or fake top LEF.
Missing native decoder source was independently fixed by TOK-DS `1d5d9adef`:
`rtl/dsrom_sys/s81_link/lp/ot_s81_kp4_dec_native_flat_lp.sv`.
Full isolated source hierarchy lint passes with missing modules/pins fatal.

Measured results (independent NUMBER-CHECK outstanding):
- Actual parent synth exit0: OpenROAD area823,107um2 versus adopted
  3318x1013um lot3,361,134um2 (24.49%). Actual legacy macro outlines816,983.8848um2.
- Real landed/TXL/reset glue has12,115 FFs. Canonical fanout gate PASS, zero over64.
- Alias-view physical-profile parent independently synthesizes to SAME area and
  12,115FF / zero over64: simulation pin FFs are not double-inserted in P&R.
- Full two-PHY exposed-byte/FEC bench at833/833.25ps:6000sent/6000received,bad0,
  both endpoints live/no fault. Landing0-bypass mutant:4483received,4483bad,FAIL.
- Decoder real-stream miter:24,990 field comparisons match q+6 cycles,
  lock/relock+2,counters+4. Five KP4 views have input+1/output+1; rate-match has0.
- Preserved FAIL: encoder raw-PMA waveform is NOT simply global+2 at cold boot;
  reset/frame phase is stateful. Explicit per-port model passes exposed-byte test.

Integration contract:
`tools/s81_link/phy_physical_profile.py` emits top
`ot_pdie_serdes_col_physical_profile`, native landed decoder, simulation-only
pin models and exact per-port metadata. `phy_native_parent_trial.py
--physical-pin-profile` uses renamed copies of the true digital LEF/Liberty
views, keeping FOREIGN original master names; simulation wrappers are separate.
S81 die owner has this contract and owns the ONE S81 event. No source-profile
or physical-view adoption has been silently made.

Remaining physical blockers:
1. Analog shape/orientation: original modeled129.6x2246.4um PMA declares onlyXY;
   it cannot fit1013um height. Neither R270 nor area-square reaspect is qualified.
2. Actual parent plan slice, full pin/reach/clock review, P&R/STA/signoff, and
   current requalification of the six legacy digital views are still required.
   Area fit alone is not physical closure.

OWNER? is in CODEX-LOG.md (09:08). Concrete planning drawing, viewed:
`/srv/opentallas-scratch/claude/codex-s81-phy-profile-1027/rotation_planning.png`
(and JSON; also committed under results/s81_phy_native_codex_1027).
It preserves original analog dimensions with UNDECLARED R270, fits all six real
R0 digital outlines and existing TXL2 stations with zero macro overlaps, and
keeps centre clock entry free. Explicitly NOT approved for route; no full
pin-to-pin census/timing is claimed.

Raw source/synth/bench data on intel1:
`/srv/opentallas-scratch2/claude/codex-s81-phy-digital-1027/`
Relevant files: trial/synth.log, trial_physical_profile/synth.log,
trial_physical_profile/reg_fanout.json, profile2.log (encoder-shift FAIL),
link_precise0.log (PASS), link_precise1.log (mutant FAIL), clock_fixture*.log.
All these jobs are done; do not relaunch them as pending jobs.

## PG experiment and owner

`codex/psm-independent-1027@4a042762a` pushed GitHub + intel2 hub.
Tool source `9b5ddff1a`, receipt `014b65660`, final failure `4a042762a`.
Historical KV kitC only, unchanged grid/bumps/power44.931523W/.7V.
160 macros ->47,032 independent supply terminals (23,516 VDD).
VDD/VSS connectivity PASS; numerical process exit0, IR FAIL:
worst drop1,165.654mV at sys_SW, versus original468.441mV.
Negative linear-model voltage is an infeasible constant-current solution,
not a physical operating-point claim. Removing ideal cross-strap shorts
worsens IR. One M1 CSV virtual node was never proof of physical point loading.
Both worst SerDes windows have zero VDD bump targets.
4552s, peak RSS98,169,220KiB (~93.62GiB). No droop table/plan adopted.

Raw terminal data intel1:
`/srv/opentallas-scratch2/claude/codex-sta-pg-1027/`
analyze2.log, distributed2_ir.csv, census2.json, result.json, distributed2.odb.
Old job unit `oth-ubuntu-1283665-1793114230`, container
`codex-psm-analysis2-1027`: TERMINAL, not live.

Current correction ownership is Qwen kv_clock (not me): truthful PHY leaf
footprints and dedicated VDDPHY_SW/SE with original existing micro-bumps,
keeping digital glue on VDD. Their R3 jobs were intel1
`codex-kv-clock-1027/phy_pg_r3/sys_{SW,SE}`; clients716246/716247 on intel2.
R1 narrow-stripPDN0185 and R2 accidental extra HBM island were diagnosed/fixed.
Check KV owner's current notes for newer results; do not duplicate.

## Shared fixes and HEAD diagnostic

`codex/ft-overlay-1027@bae112e24` pushed GitHub + intel2 hub:
- `79a0cfe0a` FT per-port input/output exclusions after bus expansion; sender
  demand retained, ordinary IO floors unchanged.45 tests+mutant,6 default
  sessions byte-identical. Confirmed ancestor of actual intel2 main at10:06.
- `ced7b8d2d` trial GRT/clock exact-exit propagation: both corners run,
  first failure survives logging/later success.5 executed shell controls.
- `bae112e24` infra_pg/phy_ir window failures rethrow before OT_DONE;
  phy_ir EXIT logging preserves status.6 executed generated-Tcl controls.
The latter two were not ancestors of main in the10:06 ancestry check; ROOT/FLOW
owns merge status (content may have been selected into another integration SHA).
Native PHY and PG candidate branch tips were not ancestors of main at10:06.

HEAD stack witness is complete, STRUCTURAL, no shared tool edit:
actual current C128 replay:83no_clock_track+1027no_pin_stack+283reserve_overflow.
Exact existing router state retried with actual stack-window intersection,
same2.5um/8.64um/PG+clock+shield limits: ZERO valid alternates in1027 cases;
all windows were nonempty. Old HEAD source ignored exact_reserve entirely.
Evidence intel2:`/srv/opentallas-scratch2/claude/codex-head-track-witness-1027/`
(witness.json/log/script). HEAD owner informed; no route/limit relaxation.

DIE-STA has no standalone current job: current real-view work belongs per-die
owners. Retired DIE-CI q_su1 orphan wrapper3989734/docker3989737 was still live
when checked; root/FLOW informed, no cancellation or stale rerun by me.

10:09 update from ROOT-MERGE: trialexit `ced7b8d2d` was curated into main as
`3ecb807519`. PGexit `bae112e24` was explicitly not separately taken/approved
in RM intake. Source remains clean/pushed and can be selected independently
now that its logged_stages dependency is on main. No physical rerun required.

10:11 KV owner result update: R3 dedicated PHY source solve114.043mV both;
R4 existing odd5 grid1.728/.48 yields34.319mV both PHYs. Full source event
still FAIL: unchanged digital glue485.370mV SW /493.047mV SE. Their
infra_pg_domains.make uses direct uncaught check/analyze, with explicit PG_OK
for all3 nets and real CSV minima, so no false process-success claim there.
See handoff/codex-kv-clock-interim-1027.md; correction remains KV-owned.
