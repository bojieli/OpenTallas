# FAM-S81-COL-R3 handoff (successor of FAM-S81-COL-R2; started 11-21 03:4x PST; updated 04:3x)
## Goal
One coherent J7 col row set (relay_depth adds + false-fit fix + Codex v3 FT delta fc763d2a07c9 + lever-7 pin-bank rows), proven on representative col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f (strict bind + LATCHECK + G0 0 new, then kit to sign-off), handed to S81-J6-ASSEMBLY-R2 for J7.
## Findings
- relay_depth.py at 405 gives 0 rows on the rep: the 15 failing chains are not in core_conns trace (xo0-3 port->port feed-through x_i0_q -> u_bout_xo_o0; lpl_11/12 from frame_int_i0 pad; so/es/rr not traced). Rows hand-written (intel1 fam-s81-col-r3/mkplan3.py): lpl_11_r o D2, lpl_12_r o D1, y_es_p0_0 o D1, y_rr_1_0 o D1, y_so_1_0/so_3_0 o D1, y_xo0..3_0 o D2 (one 1104-bit bus -> equal D). Function: rr/lpl_11 = valid-tagged dsfd_rstg return; so/es/lpl_12 = sstn status OR inputs (no alignment). +15 cycles.
- 7 false-fit chains = relay_mid FIT checked nominal neighbours. Flow fix: OT_RELAY_MID_FIT_CHAIN (opt-in; plan budgets.relay_mid_fit_chain[_types]) main 39d243610bd + schema 87f8bb96ef.
- NOFIT census intel1 (J5 place logs): only col_h10_r0_p1 has depth fallbacks (15); other col families fb=0. Other hosts not yet censused (script scratch nofit.sh).
- Codex v3 FT delta touches only slice types (no col type) -> no interaction with col rows.
- Codex E8 2930371 = col_h9_r0_p1 pv697f40c9 three-moves place (not h10). Waiter on it.
## Running
- Proof C: tree intel1 fam-s81-col-r3/src3 (J5 + mkplan2 lever-1/RDX + mkplan3 + FIT CHAIN types=[rep]; tools rt f3db2d0e628f + patched relay_mid.tcl/gen_phys.py/schema.py copies). Strict bind+LAT on intel1 (bind_otrun.log); hub chain intel2 fam-s81-col-r3/chain3.sh -> kit_wave run-item spec fam-s81-col-r3/wave/spec.json (src_manifest off) to place; reads relay_mid coverage.
## Next
1. Bind/LAT result -> if LATCHECK fails on xo lane cycles, lanefix.py intended cycles.
2. Place coverage 0 fallback -> CTS/route to sign-off (private), then rows as j6_donor_delta.v1 on J6 plan 44be605129cb for all col_h10_r0_p1 types -> S81-J6-ASSEMBLY-R2.
3. lever-7 rows (FABLE-CLOSURE-STRATEGY row 7: N-strip ft bit sites two rows + frame_int_o bank beside window; xo_i pad two rows) not built yet.
4. OWNERS-SWEEP 5 FAILED col rows: deliberate holds posted 03:5x.
