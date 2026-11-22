# FAM-S81-DSDV-R1 handoff (Sonnet, started 11-21 22:50 PST)
Family: S81 dsdv_slice_c1x_C__t1,t3..t10; lepw_mu_C, lepw_mu_LP, lepw_mus_C, lepw_mus_LP; iq_C__t1. COORD 23:0x: use ONE shared xg/xf J8 form led by FAM-S81-LEPE-4 (xg placement region + registered xg stage +1 cycle + fixed xf leg sites; c1x_C drafted jointly w/ FAM-S81-SLICE-R4/R5/R6). No second form.
## Census (kit_wave_state, event 224567138ab = J5; all rows ROUTE-HELD at geom, owner holds for J5 monitor-pin; none signed)
- Placed-scan on J5 kits (limit 405 um): c1x t9 112 groups/64 NEED-STATION/10415 bits, max 1406 um; iq_C t1 109/63/16161, max 1551; lepw_mu_LP t2 61/46/5361, max 1448; lepw_mus_C t1 126/63/11058, max 1474. Post-place setup t9 -706, lepw_mu_LP t2 -660 (cannot sign). c1x t1,t6 older STRUCT-STOP (-2605/-1572).
- Common class = long xg/xf legs (xring, leafup, xg row_d/iw), not fixed by J7 (J7 carries no dsdv slice change: col/serdes holds + toolskew pin only). J8 needed.
- c1x t9 is 512k placed (>400k cap): needs strip/body split (SLICE-R6/FLOW-STRIPBODY-R2). Others unknown counts; iq_C ~378k est.
## Plan
1. Read shared xg form from LEPE-4/SLICE-R6 rows; apply to c1x_C representative (non-t9, e.g. t8/t4) + lepw_mus_C + iq_C as J8 rows; hand to S81-J6-ASSEMBLY-R5 before 11-22 14:00.
2. Private kit via kit_wave.py private-spec (model: autopilot/private_specs/FAM-S81-IQF-R1/*/spec.json; fork J7 tree kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work with ot-tree-fork).
3. After J7 apply (04:14): check holds on my 14 types released, wave relaunches siblings.

## STATE 11-22 02:3x PST (after limit resume)
- COORD ruling: iq_C t1 = representative. Owner prefix rows added (COORD-ROUTED-OWNERS.tsv). J8 rows need tools_min_sha 20a713e74d. J7 does NOT release my types; they relaunch on J8 (11-23 04:15).
- Tree fork (real copy of J7 d8j7_1117_work): epyc9 /srv/opentallas-scratch2/claude/fam-s81-dsdv-r1/trees/j7_work (verified).
- iq_C J7 geom kit DONE: epyc9 kw43-wave-1109n/runs/s81/kit-wave/s81/a9ed808a98d/private/FAM-S81-DSDV-R1/dsdv_slice_iq_C__t1_1121230933 (370,912 cells, geom PASS-COND). scan405/ = placed_scan --limit 405 --cycle 405: 103 groups, 15389 bits.
- Generator scratchpad iq/mkrows.py maps groups with u_bin_/u_bout_ ends to bus: station rows (13 rows); 89 inner groups (xg u_r, xf, rrl reset, ist_ existing) flagged for LEPE-4 shared xg/xf form + RAWRST rows. Rows file epyc9 fam-s81-dsdv-r1/iq_rows.json; private plan trees/j7_work/physical/die_plan/s81/plan_iq1.json.
- Strict bind+LATCHECK+G0 running: ot-run unit on epyc9 (gate_iq1.sh, log fam-s81-dsdv-r1/gate_iq1.otrun.log, outputs gate_iq1/, bind out native_bind/out_iq1). Then private-spec iq_C with --plan plan_iq1.json --bind-out out_iq1 --src-manifest off -> route toward sign-off.
- Geom kits launched on J7 fork for lepw_mus_C__t1, lepw_mu_LP__t2, c1x_C__t8 (specs in autopilot/private_specs/FAM-S81-DSDV-R1/*_1122*). Next: same scan->rows for them.

## STATE 11-22 08:2x PST
- iq_C gate GREEN (gate_iq2: bind 0, LATCHECK 873/873, G0 only 9 die-level J7 baseline errors). Plan epyc9 trees/j7_work/physical/die_plan/s81/plan_iq1.json (+sync_fixed_cycles, scripts mkplan2.py), bind out native_bind/out_iq2.
- Sealed route kit RUNNING: spec ~/coord/autopilot/private_specs/FAM-S81-DSDV-R1/s81_dsdv_slice_iq_C__t1_1122081048 (--src-manifest seal --rt-floor-exempt, COORD: counts; do NOT rebind for counting). Durable waiter on result.json. On sign-off: PROVENANCE.json by run-item; check EQUIVALENT routed LEC.
- Geom kits (sealed) for lepw_mus_C t1, lepw_mu_LP t2, c1x_C t8: specs *_1122081* ; next: placed_scan --limit 405 --cycle 405 on geom/geom.tsv -> iq/mkrows.py -> rows -> sync_fixed_cycles plan (mkplan2.py) -> gate -> route kit.
- J8 rows posted: lanes/handoff/FAM-S81-DSDV-R1-iq_C-J8-rows.json (13 bus rows, tools_min_sha 20a713e74d); 89 inner groups listed in same file under unmapped_groups_for_shared_xg_xf_form -> LEPE-4.
- Notes: never run gate/writes in the tree while a kit seals; private-spec swallows stdin in bash -s scripts (use </dev/null).
