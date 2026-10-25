# PLAN-DELTA/S81 — batched type-reduce delta (2026-10-25)

Branch `claude/plan-delta-s81-1025`. Base: `main` 394765394 (no merged S81 plan2/plan3/P1 plan exists on
main. Those are WIP chains). `delta_s81.py` derives its merges again on each run, so it can be replayed on
the plan2/plan3/P1 lineage when that lineage lands.

## What changed (applied)
`delta_s81.py` = `tools/die_plan/dedup.py` exact TYPE-DEDUP with `--fix-order` (die-wide port bit-order
parity solve) restricted to NON-PATH types:

* Every member/target that is a PATH type is excluded (PATH list in the script; `col_h9_r1__t1` added =
  C1 representative, left as it is).
* Any group whose order repair would touch the pin table of a PATH type is dropped
  (`ot_s81sl_leaf__t9 -> t73`: repair touches `dsdv_slice_lepw_mu_C__t1`).
* The script asserts no PATH type or PATH partition changed; `dedup.verify` = exact.

| merged | into | instance |
|---|---|---|
| ot_s81sl_leaf__t63 | ot_s81sl_leaf__t24 | s_6N_L3 |
| ot_s81sl_leaf__t64 | ot_s81sl_leaf__t25 | s_6N_L4 |
| ot_s81sl_leaf__t49 | ot_s81sl_leaf__t40 | s_5S_L4 |
| ot_s81sl_leaf__t48 | ot_s81sl_leaf__t44 | |
| serdes__t6 | serdes__t2 | |
| serdes__t5 | serdes__t1 | |

The order repair rewrote the bit order (`order` lsb_low/lsb_high, port `bit order`) of 32 die ports.
That touched the pin tables of these non-PATH types: dsdv_slice_c1x_C t3/t4/t6/t7, gunit__t1,
ot_s81sl_leaf t23-t30/t47/t50/t51, slice_station t23/t46. Their netlists, outlines, windows, stations and
hard cores are unchanged; only which track carries which bit changes. All of these types are NEEDS-KIT,
except slice_station__t46 (REVIEW, crashed flow), so no signed kit is invalidated.

## Counts
| | before | after |
|---|---|---|
| partition types | 177 | 171 |
| leaf types | 72 | 68 |
| serdes types | 11 | 9 |
| c1x_C / kv_leaf / col_h* | 9 / 5 / 12 | unchanged |
| plan_items (ownership.py) type / core | 177 / 58 | 171 / 58 |
| distinct netlist keys (dedup) | 166 | 166 |
| partitions / ports / lanes | 398 / 2302 / 869 | unchanged |

Latency, lanes and the census are unchanged by construction: dedup re-maps the instances only.

## Gates
| gate | before | after |
|---|---|---|
| G0 | PASS 0 err / 1280 warn, worst cut 0.1423, worst seg 0.3922 | PASS 0 err / 1258 warn, worst cut 0.1423, worst seg 0.3922 |
| G0C (--completeness) | PASS 0 err / 1280 warn, 177/177 types clean | PASS 0 err / 1258 warn, 171/171 types clean |
| cut audit | worst cut 0.1423 @ horizontal@18750 | same |
| FT per-bit hop audit (`ft_hops.py`) | every touched type: max hop after <= before (e.g. leaf t25 366.5->356.4 um, t27 372.3->363.4 um); none grew |
| IR | n/a (C was not applied) | n/a |

## Images (`img/`): BEFORE | AFTER type frames. Red marks an order flip.
Every touched type shows the same outline, slots and buses; only the order changed (red).
Verdicts: PASS for all of them (t23-t30, t47, t50, t51, c1x t3/t4/t6/t7, gunit t1, station t23/t46,
serdes t5/t6, leaf t48/t49/t63/t64). `die_plan.png` is the die after the delta.

## Deferred (with reasons)
* **A1 drop the 6 `_xm` leaf-core views: not feasible as specified.** The core LEF sits on the M3/M5 track
  lattice (M3 pitch 0.036 / offset 0.009; M5 pitch 0.048 / offset 0.024). An MY placement needs an
  origin u with u = 0.018 (mod 0.036) and u = 0 (mod 0.048), and no such u exists. That is why
  `xmirror.py` and the `gen_plan_v4 mirrored()` guard exist. The fix is to re-pin every N/S vertical pin
  of the 6 cores to M5/M7 only, then shift the MY origin to u = 0 (mod 0.192). That means re-kitting all 6
  cores. PATH leaves t56/57/58/60/61/65-68/71 also use `_xm` views, so this needs PATH-S81 consent. OWNER?
* **A2 LLfu=LLfd, NNfu=NNfd by MX: dropped.**
  - All 4 node cores are already signed off, so the merge saves no sign-off.
  - The nodes sit in all 12 col types, including PATH col_h10_r0_p1/p4.
  - Under MX the fi/fo fault-chain pins swap N/S, and 126 E-face a/b bits reverse their order.
  - The frame RTL (col_h9/col_h10 l4_lp) would need a module rename, and the cores would be re-kitted.
  - Net result: more work and no sign-off saved.
* **B serdes 11->5:** 11->9 is done (exact merges). The remaining pairs are GEOM-BLOCKED: their coll/ft
  windows differ (t1/t16, t2/t14, t3/t15 differ at `coll_i0`). C supersedes them, because moving the coll
  buses off the row makes the windows equal.
* **B c1x_C 9->4, kv_leaf 5->3:** these types follow the leaf ft classes they abut. They fall out of D.
* **B col_h* 12->8 (h9_r0 p1/p4, p2/p5, p3/p6):** needs ft-lane re-population (dedup FT-POP), which is a
  lane move and not mechanical. h10 p1/p4 is PATH. col_h9_r1__t1 (C1) has no ft slots and is in no fold
  pair, so its post-fold form is main's form unchanged: C1 can be kitted from main now.
* **C PHY_SHORT (a) (far coll buses off the SerDes row, lk_WS3 IR):** this is defined on plan2's IR split,
  which is not on main. The SerDes rows abut the col_h9_r2/col_h10_r2 (south) and col_h9_r0_p* (north)
  frames and stations t43/t44/t31/t52/t49. Moving the coll lanes adds ft slots either to frame types (new
  col variants) or to the stations. Do it on the plan2/plan3 lineage, then run IR there with
  phy_ir/pg_domains.
* **D leaf 72->12-16: assessed, cannot be done in this delta.**
  - The exact/order-repair route runs out at 68. After this delta, three more pairs differ only in
    `bit_sites_um`: t74->t10, t8->t72, t9->t73 (t9 also touches PATH lepw_mu).
  - These three can merge if the FT bit sites are regenerated for the target. That gives 66, or 65 with t9 (PATH consent).
  - Going below that needs the misc lanes (ft0..ft7 classes) moved out of the leaves into the slice
    stations/columns, so that leaves differ only in core view, face and orientation (12-16 classes).
  - Blocker: 15 leaves are PATH (t36, t55-t61, t65-t71). Lanes that only pass through them may not be
    moved, so the station-column route is blocked for every lane that crosses a PATH leaf.
  - Plan:
    1. Regenerate bit sites for t74/t8 (to 66).
    2. After the PATH leaves are signed off, move the misc lanes in one batched lane re-route. Per slice
       row: leaf ft slots -> slice_station ft columns. Check the station face load against the
       8,657-pin face budget.
    3. Re-dedup.
