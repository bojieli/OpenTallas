# FABLE-FIX-S81-J8-TAPROWS handoff (live; started 11-22 04:2x PST)
Goal: S81 J8 clock-tap rows bind clean; hand green rows to S81-J6-ASSEMBLY-R5 by 13:30 (rows due 14:00, cut 16:00).
Pairing: TAP-GRID-R5 (keeps QC/KV and its own bind4). Dirs: epyc7 (main) + epyc8 (spare) /srv/opentallas-scratch2/claude/fable-fix-s81-j8-taprows; lane clone repo/.
Local scripts copy: rtx-pro scratchpad j8/ (compose.py, chain.sh, val1.sh, patch_lr.py).

## Findings (04:2x-05:2x)
- TAP-GRID-R5 bind4 (epyc7 unit oth-ubuntu-3692769-1795347965, s81j8/gate4, plan_rm4 0737c66490dd) = J7 a6771d121e95 + rows1650 (103 types, +405 taps) + anchor-mode remap of the 53 types from the J7 reset_tree_anchor. NOT mine; I only read its result (bind4.out, bind_out4/bind_report.json). "REMAP_ANC OK 53 BAD 53" = print bug, plan is updated (checked col pv110cabb8, leaf t1).
- COMPOSE PROBLEM: rows1650 is on the J7 base. Leaf plan e (OPUS-FIX-S81-LEAF-R10 a0a696072693, gate e green) replaces 75 leaf types WHOLE; 61 of them are tap-row types (55 with a changed taps list; 37 of the bad53). Slice v9 (FAM-S81-SLICE-R6 5ef4a74c48a0) changes 54 types, 6 are tap-row types. So 67 of 103 J7-based tap rows do not compose; they must be re-split on the composed base. Col rows (FAM-S81-COL-H9R0-R4) not delivered yet: 30 col row types stay J7-based.
- Slice v9 gate (epyc7 fam-s81-slice-r6/j8bind gate_v9) BIND_RC=1 with 15 HARD_CORE_PARAM_ALL (tree6, no elab) and tree: RESET_ANCHOR slice_station__t46 rst_rl_64; v9t rerun in flight. Slice v9 is not proven clean.

## Done
- main 3e5de95c409b: landing_remap anchor mode reads the BOUND old tree (bound_old_tree: --bound-rtl body, else OLD plan reset_tree_anchor, else rebuild), receipt old_tree, --rebuilt-old; 3 tests in test_landing_remap.py. (Default resel mode already takes anchored START/local refs from the anchor since 4f69f6e241.)
- Composed base plans/base_c1.json 5433ac309bb4 = J7 + leaf e + slice v9 (compose.py 3-way, lanes/latency merged, 0 conflicts; compose_report.json).

## Running
- epyc7 tree fork unit oth-ubuntu-4183102-1795349619 -> tree/ (slow, ~0.7 GB/min of 54 GB; --threads 2). epyc8 second fork (fork.log) -> tree/ for fallback run A.
- epyc7 val1.sh (val1.out, val1/): main remap (resel + anchor) on the J7 base vs TAP-GRID plan_rm4.

## Plan
1. chain.sh on the fork: tools = rt >= 6d2e187f0d65 forked into tree (J7 tools kept as tools.j7), leaf regrid netlist 6017c662 (fable-fix-s81-leaf-taphold/die_netlist.base.v) at bind/inputs/die_j6_h8_gp1076.v, plan = base_c1 -> tap_split --cap 1650 --radius-um 300 -> landing_remap (main) -> elab -> strict bind --all-gaps -> LATCHECK -> G0 vs J7 baseline -> PRE.
2. Fallback A (epyc8): same without slice v9 if v9 causes errors.
3. Hand over rows (added_taps per type on the composed base + remap recipe) to S81-J6-ASSEMBLY-R5 with receipts.
