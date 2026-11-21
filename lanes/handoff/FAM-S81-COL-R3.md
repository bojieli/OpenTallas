# FAM-S81-COL-R3 handoff (updated 11-21 04:5x PST)
Scope after COORD split (04:4x): col_h9_r1 + col_h9_r2 (118 types held for J7) + shared J7 col rows. col_h9_r0_* -> FAM-S81-COL-H9R0, col_h10_* -> FAM-S81-COL-H10.
Work dir intel1 /srv/opentallas-scratch2/claude/fam-s81-col-r3 (hub chains intel2 same path). Lane clone intel1 .../lane (branch claude/fam-s81-col-r3-fitchain, pushed).
## Shared J7 col rows
1. relay_mid depth rows (col_h10_r0_p1 only; other families fb=0 in J5 place logs): mkplan3.py (10 rows, +15 cycles; xo0-3 equal D2). -> H10 lane.
2. False-fit (joint seats) = flow fix OT_RELAY_MID_FIT_CHAIN, main 39d243610bd + schema 87f8bb96ef; plan budgets.relay_mid_fit_chain[_types].
3. XALIGN (TOKEN-1121 L02 e1 x1 vs go/cfg 2): RLYBR-1 keeps bsM on original xa/xb relay while cc_K_0 has relay_depth D. Generator mkxalign.py IN OUT ROWS -> 96 rows / 42 col types on J5 (xalign_rows_j5.json). Gate: bind4 (src4 = J5 + XALIGN) running intel1 bind4_otrun.log. After green: TOKEN-1121 regenerates L02 schedule from bind4; J7: run mkxalign.py on the J7 base plan.
4. Codex v3 FT delta fc763d2a: only slice types, no col overlap -> pass through to J7 as is.
5. lever-7 pin-bank rows (FABLE-CLOSURE-STRATEGY row 7): NOT built.
## Proofs in flight
- proof C (h10_r0_p1, handed to FAM-S81-COL-H10): src3, bind_otrun.log, hub chain3.sh/chain3.log (chain tied to my session; H10 lane re-run chain3.sh if it died).
- h9_r1 rep col_h9_r1__t1__cl49d7a23e__pv047ea3b3: src5 = J5 + mkplan2 lever-1 ROM input (104) + RDX q (35) rows + XALIGN; bind5_otrun.log; hub chain5.sh (setsid) -> run-item wave5/spec.json (gen_env copied from h10 spec: diff vs h9_r1 kit_wave item_env before trusting a fail) -> posts result. Then CTS (R2 pattern: tg_cts.sh) and route to sign-off. NOTE RDX q rows need the signed RDX cfg7 view for a signable build; private proof only.
- Codex E8 2930371 (h9_r0_p1 three moves) placed rc0, geom running -> FAM-S81-COL-H9R0.
## Open
- h9_r1/h9_r2 relay_mid: expected=0 groups (rows 1-2 do not touch them). Their J5 failure class = post-CTS setup triage (ROM go_tag half-cycle) -> lever-1 is the lever.
- J6 C1n packed (event dc92652f0d5, plan 44be605129cb). After J6 apply: lanefix.py + strict bind of J7 delta; derive t4.xai/t5.xbi rows (relay_depth.py).
