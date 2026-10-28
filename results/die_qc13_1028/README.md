# DIE-QC-13 (2026-10-28 09:47-10:55 PDT): QC die owner, slice-head start width

Runs are on intel2:/srv/opentallas-scratch2/claude/die-qc13-1028 (trial11, est/, ca/t11, ca/t11i).
Tools: main 5e316d5fee plus the opt-in below. Numbers are OWN / UNCHECKED-independent unless marked CHECKED.

## 1. Root cause of the 60/871 width start FAILs (trial10)
This was measured with probe_start.py, using main count_align_plan internals on the trial10 proof.
- Every failing port launches from a REAL leaf of the parent region: sl_*_stm, sc, ctl, st_a.
- That leaf sits about 430-441 ps of in-region H-tree below the region root. The region root is also the fork of the child feeds.
- Width-mode retime can only use tree nodes below the fork on the capture path. Even the nearest one, 150-264 ps below the fork, gives a segment width of 209-216 ps, against the limit T/2-2ap = 208.25. So no retime is possible.
- The fit over all 871 ports is w = 73.5 + 0.153 ua + 0.254 ub (resid sd 8.8). The launch-side in-region insertion alone uses up the budget.

## 2. Structural fix: shared feed node (die_trial --tree-opt region_stub=1, opt-in, default byte-identical)
- In every region that feeds other regions, the region's own tree hangs from a stub node at the feed end: a zero-length leg with one even inverter pair in inv2.
- The feed end therefore becomes a pure branch node (the shared feed node, virtual st: node). Every start port leaves it as a retime flop on the clock fork, and no port launches from a region leaf.
- Leaf regions are unchanged.
- Tests: 4 new, 70 die_trial tests PASS.

## 3. ESTIMATE first (synthetic proof, est/stub_proof.py: trial10 arrivals with the own-tree branches moved below a stub)
- base reproduces 60/871 FAIL (tool CHECKED).
- stub 10, 30 and 60 ps: 949-973 start ports, 0 FAIL. Crossings 2537 D4; the 13 D8 become D4.
- DIE-S81-13 --start-retime-up (0c098929f5) on trial10: 0 unclean, but plan() raises "753 nodes not reached".
  - Cause: the climb-up creates one fork retime node per child edge (30 duplicate st: dst, e.g. sl_E0_ctl->st:h000000 x3), so the start graph is not a tree.
  - Its leaf->fork segments are 155-201.8 ps wide.
  - The shared feed node is kept, because it is a tree by construction and needs no leaf climb.

## 4. trial11 BUILT (rt2 + inv2 + dme_feed_centroid + region_stub; kit 10:04-10:29)
- Build: 39,440 cells (trial10 39,086), 177 shared feed nodes, 0 illegal. Clock-only GRT 2W2S TT/FF EXIT 0, overflow 0, 4.665 m (CHECKED, logs).
- Renders trial11_plan_die / E2arms viewed: same feeds and region trees as trial10, no detours (the stubs have zero length).
- Duty (NLDM, both edges): TT 48.5-51.7 %, FF 49.4-54.25 %, 0 taps outside 45-55 (trial10 FF: 36 taps >55 %). MPW 0 at TT and FF.
- Max slew, clock-only GRT, CHECKED from c11 arrays:
  - clock cell pins: TT 247.8 / FF 248.5 ps;
  - taps: <=47.6 / 43.8;
  - 0 cell pins >320; report_check_types -max_slew -max_capacitance prints no violators.
  - trial10 is identical: 247.8 / 248.5.
- Spread: c_* TT 66.2/106.3 (0 >150); su_c 74.7/94.2; FF c_* 62.6/98.4. Unchanged from trial10.
- CA on BUILT arrivals, main model (BUF spice/AOCV, pre CLK-INV-CAL-1):
  - width: 977/977 start ports clean, 0 FAIL, crossings 2537 D4, min lo 104.8;
  - phase: 566/566 clean;
  - die STA count-align TT lo 105.9 / FF 104.6 PASS, start-skew 0/977 (width bind).
- CA with the CLK-INV-CAL-1 model (git archive fccbe1df43, not yet on main; proof tagged clock_cell=inv2; ca_spice 0.9324/0.9380):
  - width 826/826 clean, 0 FAIL, D4, min lo 107.0; phase 549/549;
  - die STA TT lo 108.1 / FF 106.8 PASS, start-skew 0/826.
  - Control: trial10 under the same model has 3 width FAILs (st_a).
- FF hold (hold-buffers none): intra -281.9 / seam -143.3 on the main model; intra -249.0 on the inv-cal model. Not fixed (item 4).

## 5. Findings for COORD
- The lane-local QC proof (die-qc9 mk_proof.py) has no clock netlist and no meta clock_cell. CLK-INV-CAL-1 detect_clock_cell would therefore fall back to the BUF model silently. QC CA reruns must tag the proof (here meta clock_cell=inv2) or use trial_tap_arrivals.
- Re-plan on main after the CLK-INV-CAL-1 + FLOW-ONEMODEL-1 merges and the wander follow-up (COORD 10:4x).

## Not done
- A0 trunk on the real a0k5 layout.
- FF duty spice sizing. FF duty is now inside 45-55 on trial11, but there is no spice check yet.
- FF hold region balance.
