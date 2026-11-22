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
