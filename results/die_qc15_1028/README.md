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

## Task 3a: nl variant (same flow, shared tool end to end)
nl/prep.sh: QC-A0-KITS-3 nl 3_place.odb (13,982 glue regs, 10 romleaf + 8 rawleaf, no node), 49 clusters <=160 um
(clusters.py, kid orientation taken from the placed macros: MY/R0), TritonCTS local trees, clins from the cluster build,
romleaf a0k5 pin by LEF/DEF round trip (pins CHECKED: MY x 173.652 / R0 x 284.268, y = y0 + 15.12). nl/step.sh: shared
parent_trunk_dme plan (geometry orient, no --orient-rule) -> parent_trunk_insert.tcl -> clock GRT TT/FF -> evr; corr on
ROUTED TT arrivals (q3/q4 with --damp 0.7: q1/q2 oscillated).

| build | TT min-max (spread) | FF min-max (spread) | regs mean TT/FF | duty TT / FF | MPW | max clk slew |
|---|---|---|---|---|---|---|
| q0 plan (routed) | 758.9-837.4 (78.5) | 661.7-735.3 (73.6) | 790.8 / 690.6 | 48.5-50.5 / 47.9-50.1 | 0 | 224 / 229 |
| q1 | 772.0-836.7 (64.7) | 671.7-736.7 (65.0) | 801.4 / 699.1 | | 0 | 211 / 214 |
| q2 | 763.6-820.8 (57.1) | 662.2-718.8 (56.6) | 795.7 / 692.8 | | 0 | 138 / 140 |
| **q3 (damp 0.7)** | **776.7-812.6 (35.9)** | **677.0-713.3 (36.3)** | **796.4 / 693.8** | 49.2-50.8 / 48.9-50.3 | **0** | **137 / 139** |
| q4 (damp 0.7) | 777.1-812.3 (35.2) | 671.2-720.3 (49.1) | 792.3 / 688.4 | | 0 | 139 / 141 |

- nl q3 meets the contract with ~24 ps margin: 191 INV, 12.87 mm, elongation 3431 um on 39 legs (2x nk: the nl
  clusters are farther from the trunk merge points), 0 odd parity, 0 repeaters in macros, legalisation max 3.5 um,
  GRT overflow 0. Render a0trunk_nl_q3.png VIEWED: PASS-COND. Repeaters sit in the 20 um romleaf row channels and at
  the macro edges, but long elongated legs run OVER the W romleaf column on M5-M7 (x~153, y 130-1140) and over
  the rawleaf macros. Same class as the nk centre-pin legs. GRT routes them with 0 overflow.
- nl insertion (routed q3 regs mean): **796 TT / 694 FF**, ~60 TT / 55 FF above nk (736/639). Both variants are
  balanced inside, but the die must tap nl and nk A0 centres early by different amounts. c_* uses per variant values.

## Task 4: FF hold (intra -282 / seam -143), ESTIMATE only, nothing built
hold/hold_est2.py on the DIE-QC-13 trial11 proof (tap_arrivals_FF) + the K2b plan.
- The worst FF intra pairs (gate: -281.85, damage 250.43) are all in sl_*_su_c, between the prog early tap c4
  (u_suvm_u_vm8q_u_pg) and the glue/common taps. c4 hangs about 219 ps early at FF BY DESIGN (CORELAT-SQ-1 early tap,
  SIGNED prog 472.7 / 363.3).
- The gate block model is declared-budget: 250 / 202.5 core latency on BOTH sides of every pair. So it counts the
  early tap as skew and never adds the prog core's own +161 FF.
- With the plan's own per-tap insertion (insertion_ff_ps = the signed views: prog 363.3, btab 295.2, crh 240.6), the
  su_c intra damage falls from 219 (max) / 200 (median) to **91 / 66**.
- The worst partition is then c_* (98.4, in-region tree). Estimated intra FF hold is ~ -144, scaled with the gate's
  remainder of 31.4 ps. UNCHECKED.
- Structural fix order:
  - (1) Bind the signed core views (`--core-view`, existing gate input) for prog/btab/crh, or have the gate honour the
    plan per-tap insertion. This is a gate input/model question, so it goes to COORD as an ASK. It is not a new rule.
  - (2) c_*: the A0 centre entry (task 3b) replaces the c_* in-region taps for A0 by one early tap per A0 instance at
    the routed nk/nl insertion. That removes most c_* intra pairs.
  - (3) su_c residual 91: region DME balance of the c-taps against the t-taps in the plan.
  - HB4 only as a ledgered residual after (1)-(3).
- Seam -143 (damage 110.6, kit contract W 40) was not decomposed in this slice.
- hold/hold_est.py (first try, nearest-tap core map) is kept as a NEGATIVE control: map_cores_to_taps maps cores by
  distance, so it put prog on t4, not c4. The plan core tap order (c<k> = k-th core tap) is the right map.

## Not done
- c_* centre-entry die delta (3b): needs a die_trial re-plan of the c_* regions with one early A0 tap per instance
  (nk 736/639, nl 796/694 routed). Not started.
- Task 5 (CA/STA re-plan with clock_cell=inv2 declared): BLOCKED. Main 9644a2fed still lacks the CLK-INV-CAL-1 rework
  (RM165) and region_stub (QC-13).
- ICG enable RTL + gated bench + LEC (required before the trunk is adopted).
