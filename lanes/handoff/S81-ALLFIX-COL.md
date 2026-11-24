# S81-T2-REFLOOR handoff (Opus 5.5; from 11-23 19:15 PST). FAMILY lane under S81-ALLFIX-INT.
Task: die re-floor giving kv_leaf t2 (s_3N_L0) its slot; price (a)/(b), choose, build row, PRE+G0+scoped strict, ROW-REBASED to INT by 11-24 08:00.
Lane dir epyc10 /srv/opentallas-scratch2/claude/s81-t2-refloor (repo/ = ot-lane-clone of main; tool repo/tools/die_plan/rigid_refloor.py; specs spec_*.json; price/*.json).
Base B1 ae3101241d6b = epyc10 s81-j9-r6/b1_tree/physical/die_plan/s81/plan_j9_b1_exact_1123_ae3101241d6b.json. Tail recipe = s81-allfix-slice/row.sh.
## 19:55 PRICE (posted)
- (a) two-row: not buildable (no free 5.3 mm2, die 856.6/858; E-W partners change). (b) east: 42 parts, 21 types, seal ring/IO/PG blocked.
- CHOSEN (c) C2: stack cols2-4 (C,L1,L3,L4) +699.84; t46/47/48 -> 527.04 tall (top kept); col1 L0+C (s_1N_L0,s_1N_C) -155.52; t2 rect [13452.48,17236.8,18135.36,19163.52] = 4682.88x1926.72. 13 types repinned, 44 ports. Full 4700.16 (spec_C) = +6 types incl lepw C/LP.
## Next
- tool: grid-quantize slides; test; push. apply C2 -> tail (row.sh copy) -> PRE + G0 -> scoped strict on touched types.
## 19:4x
- My E10 probe bind DIED rc143 (E10 kills binds; MULTI too). Not relaunched: INT gate_c7a (E9, amd1_tree, gate_allfix.sh) runs scoped strict on 12 p5 + serdes t13 after elab (~21:00), sc_out = <amd1_tree>/physical/die_plan/s81/plan_of_record/native_bind/allfix_c7a_out_scope.
- Waiter E9 tmp/w2.sh (task brrq5dw3k). On p5 EMIT 0: launch E9 `ot-run --mem 8 --hosts epyc9 -- bash /srv/opentallas-scratch2/claude/s81-allfix-col/tmp/kits.sh <amd1_tree> <S>/j9tail_c7a/p5_deadin.json <sc_out or full bind_out> epyc9` (kits.sh on E9; capture json copied).
## 22:1x
- gate_c7a died/abandoned after elab (unit inactive, no scope_bind.log); INT moved to c8 (ba9b277a852b, tail running; gate_c8.sh scope_c8.txt has the 12 p5). Waiters w3.sh on E9 + epyc11 (tasks b0duterma / b1z77xhsk) watch gate_c8/scope_bind.log. kits.sh + capture copied to epyc11 too.
- On p5 EMIT 0: ot-run --mem 8 --hosts <gate host> -- bash .../s81-allfix-col/tmp/kits.sh <amd1_tree> <plan from gate_c8 RT.txt> <bind_out>_scope <host>.
## 23:5x
- COORD ruled (reply to ASK 146f37ce): epyc11 probe bind ONLY may use OT_PLAN_GATE_PRE=warn iff fresh PRE = exactly the 12 p5 ANCHORDRY; label PROBE, counts nowhere, gates nothing; 13th finding = stop + post. 60 col_h9_r0 stay HELD until gate_c8 (probe cannot release them).
- E9 probe outputs were mis-matched (allfix2 as-built on B1 plan): invalid, deleted via ot-delete. E11 s81-allfix-col/tmp/{stage_e11,probe_e11}.sh: B1 as-built wavea 555d3793bb64, baseline ae3101241d6b, plan 77d6f4f47270, elab bcd82ea338fc; OUT fs1/probe_out; logs fs1/pre_fresh.log, fs1/probe_bind.log, tmp/probe_e11.out.
- Then kits on epyc11 only (kits.sh; --why text says c7a, edit a COPY before use).

## 03:5x 11-24 S81-COL-H9R0-R5
Alias of this lane for the 60 FAM-S81-COL-H9R0-R4 rows (TAKING 80da15d5). All 60 ride c8/c8r, HELD for gate_c8 (INT). Live: epyc8 p2 pva4376595 ECO i2t (i1 NOT SIGNED setup -225, DRC 5); never relaunch. Next: on gate_c8 EMIT launch p5/p3 route on epyc10 (load<80) else epyc9, read rc72 corridor.
