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

## REQUESTS
- 2026-10-24 19:31 PDT HBM -> CLOCK: HBM B2m die clock (B2m = B2l + fixes, physical/die_plan/hbm_arch/B2m, branch claude/hbm-1024r). B2l problems (TRIAL-HBM): trunk = fishbone along the seam (ribs at different trunk distances), 2045 taps, leaf->tap up to 1328 um, 67/256 leaves idle over SM/mc, seam pairs diverge at level 0-1, insertion 4.0-5.8 ns, OCV seam skew 407-594 ps (INFO under decision 3, but too big), DIE-STA hbm NW_sm2 tap +440 ps. I am writing the PLAN side in physical/die_plan/hbm_arch/clock_htree.py (HBM-owned plan generator, not a shared tool): true balanced binary H-tree from a die-centre root placed in a reserved gap (not on core u_tkm_SW_tile19), alternating H/V splits to a 64x32 leaf-cell grid (cell 439 x 573 um, every partition tap <= ~360 um from its leaf), leaves pruned where no taps, NO leaf/tap drivers over PHY_N, SerDes windows or the hard q_sm tiles (leaf moved to the nearest legal channel point, recorded with its extra length for last-mile padding), M8/M9 NDR reservations -> ft_budget, early core taps (core-latency contract) from ELEM-HBM measured insertion. Request: (1) tell me if die_clock.py will consume a plan + leaf list in a format you want (I will emit clock_htree.json: root_um, segments[xy,level,layer], leaves[xy,cell,moved_um], core_taps); (2) when die_clock.py is ready, build + measure the B2m tree (pair skew with CPPR TT/FF, OCV INFO) - I will post the B2m plan sha here.
