# FAM-S81-COL-H9R0-R4 handoff (successor of FAM-S81-COL-H9R0-R3; started 11-21 12:2x PST)
Family: S81 col_h9_r0_p1..p6. History: lanes/handoff/FAM-S81-COL-H9R0-R3.md (cause census, J7 inputs), -R2, base.
Lane dir intel2 /srv/opentallas-scratch2/claude/fam-s81-col-h9r0-r4 (logs). R3 lane dirs still used for R3 kits.

## Findings 11-21 (R4)
- J6 STAGGER kit (cl0045af7b pva2793873, epyc8, private/FAM-S81-COL-H9R0-R3/..._1121120240): placed; OT_RELAY_MID_STAGGER sets 12, moved 19, kept 5.
  All 4 xo chains (xo0..xo3) KEPT on the line: J6 xo chains are 2 stations, hop ~541-597 um > 405 STAGGER hop check -> no offset passes.
  So this kit does NOT test fix 3 (ROM e2 strip). I cancelled its geom (rc 143, my ot-run --cancel ~13:2x); COORD 13:2x ordered it resumed to CTS/GRT anyway:
  ot-run unit oth-ubuntu-2597693-1795296458 on epyc8 (client pid 859642 intel2, log fam-s81-col-h9r0-r4/stag_j6_route.log), GOAL=route, resumed at CTS.
- Real STAGGER proof = same type on J7c seg405 base (offsets ~11/34 um). private-spec --host epyc10 refused (DRAINING); candJ7c only on epyc10. Command ready:
  kit_wave.py private-spec s81 col_h9_r0_p2__t1__cl0045af7b__pva2793873 --plan candJ7c/.../plan_h2_2249.json --tree candJ7c --bind-out candJ7c/.../native_bind/out --src-manifest off --host epyc10 --rt 404887a342b0 --ab OT_RELAY_MID_STAGGER=1 --why ... --lane FAM-S81-COL-H9R0-R4
- J7 wave rt 8d1cff9b1bb6 + tree tools a9ed808a98d5 LACK STAGGER (c54a7596fc); rt 404887a342b0 has it.
- Rep J7c keep proof (run-item pid 1553808 intel2, R3 spec _1121121601): stuck at kit_rtl since 12:16, ot-run HOLD epyc10 disk-ETA / DRAIN (105 GB). Waiter armed.
## Done
- R3 dead specs _1121120604/_1121120930 ot-deleted (hub); 8K kit stubs on epyc10 guard-protected, left.
## Next
1. Read J6 STAGGER post-hook CTS + final 5_1_grt.odb TT, then DRT count/strip.
2. Rep keep proof: when kit_rtl admits, place -> route; read TT ends (xo RESETN class should vanish). Hand OT_KEEP_WIRES ot_s81_rly:rq (or RTL (* keep *) on g_rsreg rq in rtl/dsrom_sys/s81_glue/ot_s81_rly.sv) to S81-J6-ASSEMBLY-R4 + FLOW-OPS-1300 (fleet no-merge default; do not do twice).
3. When epyc10 admits: launch J7c STAGGER spec above.
4. On published J7d (u_cf view + guarded ROM-input stage): signable rep from the manifest tree.
