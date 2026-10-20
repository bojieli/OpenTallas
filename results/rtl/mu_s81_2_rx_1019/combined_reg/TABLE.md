# S81 MU combined regression (REFILL-0730/MUS81REG, 2026-10-19)

Source: claude/refill-mus81reg-1019 7613ee7f4 = MU die GEN mu1 claude/mu-die-s81-1019 1d43f2c12
+ MU-S81-2/DIE ac336f805 (copy-B AB pair on s_0S, new leaf dsdv_mu_hwin, hslot = CLOSED source)
+ MU-S81-2/RX 9c4227bd9 (RTL ddc529908). Verilator 5.050 via ot-run, ot-agidock128, 8 threads. Driver: leg.sh.

Merge notes:
- Text conflicts (tools/s81_dv/dv_plan.py, bind/mk_table_p4l3_mu.py, bind_table_p4l3_{mu,mab}.json): copy-B endpoint
  s_0N (mu1 stand-in) or s_0S (MU-S81-2 copy-B relay plan). Resolved to ac336f805. The die-plan choice stays with MU-DIE-S81.
- Silent semantic conflict: the clean text merge kept 908a67c18's die masters at the end of ot_s81sl_slice_lep.sv and its
  NEV dsdv_mu_hslot.sv. That gave 6 duplicate modules (lepw_mu/_mus/_mab, lepe_mu, lepe_nh_mus, dsdv_seq_host_mux), and hslot
  was no longer the CLOSED source. Fixed in 7613ee7f4: slice_lep.sv = RX text, hslot = 1f3c59e9 (CLOSED), and
  tb_dsdv_mu_win / run_mu_win_bench.sh were removed (replaced by the hwin bench).

| leg | run | expect | got |
|---|---|---|---|
| lep_base | tb_s81sl_lep_mu s1, s5 (6 users, A/B, land+replay, RETURN phase) | PASS | PASS / PASS (return P 240/240, landed 160/160) |
| lep_mut3 | TAGDROP / WRONGCOPY / LANDOVR (OT_DSDV_MU_LAND_MUT_OVR) | FAIL | FAIL / FAIL / FAIL |
| lep_mut2 | LANDCUT / STALEHD | FAIL | FAIL / FAIL |
| lep_regr | MU_EN 0: lep s1, s7, lep NH ring s1, lep_host s3; SWAP mutant | PASS x4, FAIL | PASS x4, FAIL |
| lep_nh | MU_EN 0: tb_s81sl_lep_nh s5 (proto), lep NH ring s7 | PASS | PASS / PASS |
| hwin | MU_HWIN_GATE: base, BADRT fault, mut3, mut4, die-master lint (8 tops) | PASS, fault, FAIL, FAIL, 0 err | PASS, fault, FAIL, FAIL, 0 err (MU_HWIN_GATE PASS) |
| host | MU_HOST_GATE: hslot NS 8/47 + single, collide/offcal fault, mut1/2; seed NU 4/10, collide, mut1/2; -Wall lint | PASS | MU_HOST_GATE PASS (user 0 identical, all 4 mutants detected) |
| prog | run_mu.sh on real dsdv_seq_host: base, L0_all 46, L2_A 23, L2_B 23 | PASS | SEQHOST_PROG PASS C=11; PASS x3, user0 identical |
| prog | mutants m_shift4 / m_ctx3 / m_raw / m_drop | FAIL (fault 9/5/5/none) | FAIL x4 (fault 9 / 5 / 5 / none) |

All 9 legs give the expected result. No combination regression.
