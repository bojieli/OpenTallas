# MU-DQ-D2DUSER (10-19): D2D attention user tag on the Qwen compute MU die

Contract (agreed with MU-TOK-KV, lanes/MU-TOK-KV.md + lanes/MU-DIE-QW.md): compute->KV CMD (kind 1) and Q (kind 2) records
carry epoch = {seq14, user2}; the KV die serves user epoch[1:0] (HBM row 64+l+256u) and answers RESULT (3) / STATUS (4)
with the same epoch; the compute endpoint checks the full epoch on every return. User 0 = the HOST epoch (bit-identical to
single user); filler u = {seq14[u], u} with seq14[u] = the HOST allocator's per-user sequence (MU_SEQ0 = INITIAL_EPOCH[15:2],
+1 per L0 context of that user).

RTL (no new die port, no added edge):
- qfd_tt_ctlm_dv (+ lpf / parts, lp regenerated: +1 landing `hu` core->hr 2 b): native_pos[17:16] = user of the latest head
  start (0 on the face ME start, cmd_user on a LOCAL SEG start).  MUT 32 = not carried.
- qfd_native59_dv_service #(NU, MU_SEQ0): user = native_position[17:16]; stamps the operation epoch; qfd_native59_command
  _context_mu (same file).  MUT 5 = m7 (user 3 tag 0), MUT 6 = filler sequence stuck.  Also restores the Q seat bank
  declarations lost in merge e28fa950f (the file did not elaborate on main / MU branches).

Benches (Verilator 5.050, fleet ot-epyc8, source = claude/mu-dq-d2duser-1019 ebcdb3aa5 + the two fixed files):
- run_native59_dv_mu_bench.sh: positive N59MU_PASS (14 ops, 4 users, CMD 6/3/2/3, Q 192/96/64/96 every beat tagged,
  32 results/op matched, KVN identity tagged, user 0 == NU 1 on 1434 edges); ret_bad PASS (user-2 RESULT with tag 1 ->
  sticky fault, no completion); mut5_m7 FAIL (33 TAG_ERR + fault on the return); mut6_seq FAIL; NU-1 regression
  (run_native59_dv_service_bench.sh) positive/bad_q PASS, mut1-3 FAIL.  Logs n59mu/.
- run_mu_opseg.sh d2duser: C8 (native_pos user carrier on every edge vs the logged starts) mut 0 MU_OPSEG_PASS (red),
  mut 32 MU_OPSEG_FAIL C8 (448,431 bad edges; filler starts u1/u2/u3 60/30/18).  Logs opseg/.
- run_mu_ctlm.sh lp eq: lp audit PASS, unland FAIL, LP_LOCKSTEP MUT 0 PASS, 1/2 FAIL; LPF_EQ OPSEG 0/1 DMUT 0 PASS,
  5/6/29 FAIL; DMUT 32 not observable under eq's random stimulus (no filler LOCAL SEG) -> witnessed by opseg C8 instead.
