HBM-MC3b (10-19): SAFE face PC controller with RST_FOREST=1, RST_LEAVES=256, PCID_LOCAL=1, WROK_COPIES=1 -- the RTL that the
hdie_pc_ctrl_mc3b_{p540,q648} kits route (a575dc283). Verilator 5.050 on ot-epyc5, the kits' daemon bench stages.
- face_txn_mc3b_pos.log  PASS reqs=6000 beats=12944 wcols=759 wdone=759 edges_h9b=88783 edges_safe=166921 (identical to MC3 and to
  the pre-fix face top: 0 data cycles added). The simulation $fatal BW_AQ_WROK_COPY_MISMATCH never fired (the 3 wr_ok cones agree).
- face_txn_mc3b_mut_idtag.log  MUT_ID_TAG=1 FAIL errors=12944 (fail witness; regex 'BW_FACE_TXN FAIL errors=[1-9][0-9]* MUT_ID_TAG=1').
- bank/  tb_hbm_bw_pc4 EXPOSE census with OT_PC_SAFE_MC3 (now includes WROK_COPIES + 256 leaves): rotated ds layout steady
  91.62 / 92.74 / 92.94 B/edge/SM (seeds 1-3), packed 103.89 -- the same as MC2/MC3, above the 90 floor.
Why MC3b: the native census (native_audit.py v5) of the MC3 gate odbs found wr_ok with 53 logical endpoints, reset leaf
l2_q c174 with 34, and on q648 65 nets of 413-437 um (dram_rdata[192:255] -> response_payload M[3]).
