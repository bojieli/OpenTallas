# DIE-QC-15 (2026-10-28 11:17- PDT): QC die owner, successor of DIE-QC-14

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc15-1028. OWN / UNCHECKED-independent unless marked CHECKED.

## Task 1: routed recheck of the A0 nk trunk (contract: spread <=60 TT/FF on routed RC, duty 45-55 %, MPW, slew <=320)
Method (rq4/grt.tcl): the DIE-QC-14 db tr_q4.odb (q4 trunk inserted on cl_nkr.odb). Clock pre-route as in the
infra-first method: GRT on the 1220 CLOCK nets only (M4-M7 clock layers, 0.25 adjustment), the 57,241 signal nets are
flagged special for this step so FastRoute skips them (clock arrivals do not depend on them). Then
`estimate_parasitics -global_routing` with the calibrated setRC_rcx (GRT -> RCX fit), NLDM RVT, propagated, TT and FF.
The tile port net `ck` (port -> ICG, ~3 um, common to every sink) is not routed (netprobe.tcl, CHECKED).
A first full-net GRT was stopped: the placed parent has no signal-routing closure, 50 congestion iterations at ~2 min each.
Duty = (T/2 + k_spice * (fall - rise - T/2)) / T with k 1.0485 TT / 1.0552 FF (DIE-QC-11 duty_eval method); MPW =
DFFHQNx1 lib table at the sink slew. Spread = all 15,013 glue registers + 19 child pins + 250/202.5 (evr.py).

| build | TT min-max (spread) | FF min-max (spread) | regs mean TT/FF | duty TT / FF | MPW | max clk slew TT/FF |
|---|---|---|---|---|---|---|
| q4 placement RC (QC-14) | 735.3-763.3 (28.0) | 628.6-670.7 (42.2) | 748.2 / 649.6 | | | |
| q4 ROUTED | 689.6-788.5 (**99.0**) | 593.5-682.1 (**88.5**) | 744.0 / 645.7 | 49.9-51.5 / 49.1-51.2 | 0 | 134.7 / 139.8 |
| q5 routed corr | 702.6-751.5 (48.9) | 602.8-659.2 (56.4) | 727.8 / 631.1 | 50.2-51.6 / 49.9-51.3 | 0 | 122.5 / 122.3 |
| **q6 routed corr** | **720.1-759.2 (39.1)** | **617.8-657.8 (40.0)** | **736.1 / 638.7** | 50.0-51.7 / 49.6-51.4 | **0** | **121.9 / 123.0** |

- q4 FAILS on routed RC (99 / 88.5). Cause: the trunk legs, not the local cluster trees. Cluster-root input arrival
  routed minus placement is -40.3 .. +8.8 ps (local tree part only +0.3 .. +9.7); child pins up to -55.5 ps. Long and
  elongated legs route on M4-M7 and are faster than the placement-RC stage table predicts.
- Fix = the accepted plan iteration on the same topology (corr), now from ROUTED TT arrivals, with the SHARED tool
  (tools/die_plan/parent_trunk_dme.py corr + parent_trunk_insert.tcl, rq4/step.sh). Two iterations: q6 meets the
  contract with 20 ps margin at TT and FF. 213 INV (q4 205), 11.39 mm, elongation 1563 um on 41 legs, 0 odd parity,
  0 repeaters inside macros, check_placement clean (ins_q6.log). Duty 0 outside 45-55 %, MPW 0, max slew 123 <= 320.
- Insertion (routed q6, regs mean): **736 TT / 639 FF** (QC-14 placement 748 / 650). c_* plans the A0 early tap with
  these routed values.
- Render a0trunk_q6.png VIEWED: no repeater on a macro; elongated (red) legs run in the channels and along the E column;
  the rawleaf/node legs still cross their own macros to the centre (fixture) pins as in q4 (PASS-COND, same as QC-14).
- Placement-RC rule of thumb is not enough for a trunk with long upper-layer legs: re-balance on routed arrivals is the
  closing step. NOTE: the trunk2 stage table segments are documented `<= sp` but legalisation stretched 2 segments to
  143 / 159 um (q4); routed slew stays 135 ps.

## Task 2: trunk2 upstream (shared, opt-in)
tools/die_plan/parent_trunk_dme.py (plan / corr / tcl) + parent_trunk_insert.tcl + parent_trunk_stage_table_ckinvdcx16.json
+ test_parent_trunk_dme.py (9 tests). Same algorithm as trunk2.py, QC hard codes made explicit options
(`--entry`, `--pin-offset MODULE=dx,dy`, `--orient-rule`, fail closed without orientation / budgets / measured sinks).
Byte identity with trunk2.py CHECKED on the real A0 nk inputs: plan q0 and corr q1, q2, q3, q4 and the tcl emit all
`cmp`-identical. Nothing calls it by default (no existing file changed except the README section).
