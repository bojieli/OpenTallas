# CLOCK lane (new 2026-10-24 evening; owns die clock distribution + die-level STA, all dies)
Branch claude/clock-1024 (from origin/main d13ff7c78), worktree rtx-pro:/home/ubuntu/wt/clock-1024r.
tools/die_plan clock tools (spine.py, die_trial clock, die_sta.py, new die_clock.py) have ONE owner from now on: CLOCK.
Other lanes: do not edit them; send requests here (section "REQUESTS").
Rule (BRIEFING decision 5): gate = related launch/capture pair skew with CPPR <= 80 ps at TT and FF + propagated-clock
STA TT setup / FF hold (60/25); spread INFO.

## 2026-10-24 19:28 PDT start
- Adopted DIE-STA v2 reruns (intel2 die-sta/trial/<die>/sta/run_ttff_v2, ot-run pids in DIE-STA PARKED): running, TT
  stage at 19:22 (started ~18:55); s81_head done. Collect, then merge claude/die-sta-1024 via READY.
- Plan: (a) die_sta.py: pair-skew (worst/p99, seam + intra), CPPR on, spread INFO, hier-port SPEF stitch, --spine-tree
  (real die tree netlist so CPPR works); (b) tools/die_plan/die_clock.py: symmetric balanced H-tree on M8/M9 NDR to
  every partition tap, equal-delay padded last mile, equal leaf fanout (dummy loads), core-latency contract;
  (c) re-run 5 trial dies (die STA TT/FF + pair skew); (d) S81 head seam re-measure (decision 6).
