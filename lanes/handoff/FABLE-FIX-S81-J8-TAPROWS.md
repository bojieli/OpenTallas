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

## Status 05:1x PST
- main 58ebc21a5072 also carries the anchor-mode CLI fix (kept count TypeError). val1 (epyc7 val1/): main resel+anchor == TAP-GRID plan_rm4 on all 53 bad types; 27 other types main picks the relay at the bound site (better).
- TAP-GRID-R5 bind4 ended exit 143 (terminated, not by me) at ~05:0x; no result. My gate B supersedes it.
- epyc7 fork DONE: tree/ (manifest 12af64d4f18d, 54 GB). epyc8 spare fork: epyc8 same dir tree/ (unit oth-ubuntu-1178984-1795349979; inputs staged in in/ plans/ toolfix/ chain.sh).
- GATE B RUNNING: epyc7 unit oth-ubuntu-440360-1795351133 = chain.sh GN=gateB BASE=plans/base_c1.json RTS=58ebc21a5072 MODE=resel; log gateB.out, dir gateB/ (rows.json = 104 types +414 taps; plan_rm.json; remap_receipt.json; precheck.json: 324 refs, 0 depth moves, 0 resolve fails, max move 222.76 um). Markers FX_ELAB_RC FX_BIND_RC FX_BIND_ERRORS FX_LAT FX_G0_NEW_ERRORS FX_PRE_RC FX_GATE_DONE. Bind out = tree native_bind/out (J7 bind kept as out.j7, J7 tools as tools.j7).
- Waiter: local background poll on gateB.out.

## Next
1. Gate B green -> build delta (schema opentallas.s81.j6_donor_delta.v1 style: replace ops for the 104 row types on base 5433ac309bb4 + recipe) -> post to S81-J6-ASSEMBLY-R5 with receipts, report to COORD.
2. Errors only from slice v9 -> rerun on epyc8 with BASE=plans/leaf_e_a0a696072693.json (GN=gateA).
3. Col rows arrive (FAM-S81-COL-H9R0-R4, due 14:00): recipe = tap_split --cap 1650 --radius-um 300 on the composed plan, then landing_remap OLD=composed NEW=split --types <row types>.
