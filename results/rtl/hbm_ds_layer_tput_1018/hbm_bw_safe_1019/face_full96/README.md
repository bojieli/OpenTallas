L2H-BW SAFE face successor (source 0842760b3, top ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face + consumer-side RL1 landing ring), production
66-op / 154-GO full96 (G320/PADD8/FETCH96, HBM_SAFE_COMPOSED reset 5, HBM_SAFE_FACE), Verilator 5.050, ep5, JSON checker verdicts:
- face_pos      PASS 66/66, 154 exact GO, 301 results, END 45260 (= n64 legacy bc42f77a8: cycle-identical, 0 added edges)
- face_p192off  PASS END 45260 (positive control: same RTL on the 2c macros; p192 swap is behaviour-neutral)
- face_idmut    FAIL (expected): BW_MUT_ID_TAG through the face top -> FAULT svg cycle 785 feed 1 (fail witness, regex 'SMB_UNIT FAIL')
- face_sameedge PASS (mutant NOT detected): the production fixture's consumer never deasserts kr_rdy, so the RL1-vs-same-edge
  landing contract is not exercised here; the landing ring is the unchanged ot_hbm_svc_kr_ready_bridge (its own stall bench/MUT=1).
  Not used as a witness.
