HBM-MC2 (10-19) daemon-runnable behavioural bench for the SAFE face top (the module the hdie_pc_ctrl_bw_face_* kits route).
tb_hbm_pc_bw_face_txn.sv = tb_hbm_pc_bw_safe_txn.sv with DUT b = ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face #(SRAM_P192=1,
PURE_FACE=1, RESET_LANDING=2); 6000 random requests vs released H9b, every read tag/beat/data and write bank/col/strobe/data
compared in order; Verilator 5.050 on ot-epyc5.
- face_pos.log  PASS reqs=6000 beats=12944 wcols=759 wdone=759 (edges h9b 88783, face 166921 = core 166919 + 2 reset-landing edges)
- face_mut.log  MUT_ID_TAG=1 FAIL errors=12944 (fail witness; regex 'BW_FACE_TXN FAIL errors=[1-9][0-9]* MUT_ID_TAG=1')
RATE_CHECK=0: the random-address strict-rate FAIL of the SAFE core (n64_proofs/txn) is retained and not hidden; production
rate is qualified by face_full96 (66/154 END45260) and the controller-rate benches (91.62..92.94 B/edge).
