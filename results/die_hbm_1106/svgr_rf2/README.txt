DIE-HBM-82-SVGR 11-06: ot_svgr_own RF2 proof (rtl/hbm_accel/cores_split/reform_1105b/ot_svgr_split.sv, define OT_SVGR_OWN_RF2)

1. Default-off identity: vpp.py resolves the file for (RF1) and (no define): byte-identical to main before RF2.
2. System bench (epyc5 /srv/opentallas-scratch2/claude/die-hbm-82-svgr/bench): mk2.sh NAME STALL MUT builds the
   HBM-GAPS-5-LEC smb_unit tree with the RF2 split; one2.sh runs smb_unit.  rf2_rc.txt:
   rf2 (stall bench) PASS, rf2n (no stall) PASS: ops 20/20, gos 29/29, results 81, cycles 12764 (= RF1).
   Mutants MUT 1-11, 13 FAIL (caught).  MUT 12 and MUT 14 PASS in this bench (stimulus gap, see 3).
3. Owner lock-step (tb_owner_ls.sv, iverilog, 200k cycles x 2 seeds, ~11k random blocks, random pcs/total/banks,
   k_ready, stop, in-order K responses): ot_svgr_owner_rf2 == ot_svgr_owner_rf (RF1) with block_active delayed one
   edge (the declared +1 hbm_pc_clk), every output every cycle (k_addr/k_len compared while k_v): MUT0 0 mismatches;
   MUT12 (stale per-block registers on the first edge) and MUT13 (one-hot lookup off by one) FAIL.  rf2_ls.txt.
   MUT14 (take count from the live, not the registered, bank) is NOT caught by any bench yet: open item.
