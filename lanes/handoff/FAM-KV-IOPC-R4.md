# FAM-KV-IOPC-R4 handoff (11-22 01:4x PST) -- KV io/pc family; successor of FAM-KV-IOPC-R3
Dirs: epyc8 /srv/opentallas-scratch2/claude/fam-kv-iopc-r4 (ROWS_FAM-KV-IOPC-R4.py, tmp/cmp = compose dry run); intel2 ~/tmp/iopcr4 (run logs); specs ~/coord/autopilot/private_specs/FAM-KV-IOPC-R4/.
## State
- D27d3 plan 48b92c30c8f6 sealed (kw45/src_..._d27d3 on epyc7/8/9 + _bind_d27d3_portable). Specs come ONLY from kit_wave.py private-spec (no hand patches; COORD 11-21 19:4x).
- io_cor_v1 D27d3 place fail (OPUS-PIPELINE-R2 ot-build 1122003502): u_cland_ft16_i / ft19_i bands lie INSIDE the ft13_i ring band (790..1000 x 17.28..103.68). D28 row dropped: kv-plan-r6/d28/rows/ROWS_FAM-KV-IOPC-R4.py (ft16_i, ft19_i re-sited east of x=1000, ft4_i grown to 1.25x; compose dry run 1 type, 0 refused; pinclear 0 rows). ROWS-READY posted.
- Proof of the row: private-spec kv3_io_cor_v1_1122010321 (plan_d28.json from tmp/cmp, sealed tree, portable bind) running on epyc8; pc_v3 private-spec kv3_pc_v3_1122010122 on epyc7 (D27d3 bind). Logs ~/tmp/iopcr4/run5_*.log.
- pc_v3 wave attempt on D27d3 (intel1 items/kv3_pc_v3): PLACE-SETUP-STOP wns -966 ps, path u_bin_i_idpc_Q_N_y/q[2] -> u_bound.u_kvpc1, 28 stages path_um 1833.7 span 24 um, TNS -376590. Private proofs are exempt from the -300 stop.
## Next
1. io_cor_v1 proof: pre-place band check passes -> drive to sign-off, rebuild/seal from manifest tree for export.
2. pc_v3: read the worst path from the placed DB, structural fix row for D28 via KV-PLAN-R6.
3. Carry proven rows to siblings (io_cor, pc, pc_v1 variants) via KV-PLAN-R6.
4. Leftovers to ot-delete: intel2 fam-kv-iopc-r4/tree_unsealed (48 GB), R3 list (epyc7 fam-kv-iopc-r2/tree_pc, views_d27b, diag_ioc; tree_a1, tree_s1, proof_a1 on epyc8; tree_d26b).
