# PVM r3 (HBM-SMATT6 10-20) — bindfirst stages with canonical post-tapcell global_connect

Fleet ep6 /srv/opentallas-scratch/claude/smatt6-pvm-r3-1020 (copy of codex r2 work through 2_2; runner run_stages_r3.py).
- post_tapcell: replay the 5 persisted kit PG rules (asserted identical) + global_connect, then the unchanged
  graph/protection/scoped-TIE guard: PVM_BF_STAGE_PASS post_tapcell all_native_PG=bound.
- census post_tapcell_pg_census.json PASS: empty PG 0 (was 17062 tap + 3918 tie); protected/kernel 112000 bound
  (unchanged), 56000 kernel cells DNT; fixed 17064 bound; wrong role 0.
- pre_pdn / post_pdn PASS all native PG bound.
- 3_3_place_gp FAIL RSZ-3006 (3_3_place_gp.log.gz): net u_core.g_safe.g_madd[0]...u_native.valid_in cannot be
  buffered (DNT load pins). kernel_input_nets.json: ONE INVx1 drives valid_in of all 16 lanes (core reg `ov` ->
  16 kernels), rcore_c[1..4] reset each span 4 lanes, TIEHI _18312_ spans 16. Die-spanning nets into DNT kernels.
NEXT (structural, RTL): per-lane kept valid copy (reg [L-1:0] ov_l, keep, beside each kernel) + per-lane reset leaf
(rst_core_n per lane, not 1+l/4) + 16 compact kernel fences (Codex 2x8 23.76x34.56 direction) with oa/ob/ov_l inside;
re-run benches/mutants + native census + bindfirst r2 transaction, then r3 stages from synthesis.
