HBM-MC3 (10-19): SAFE face PC controller with the reset forest + local pc_id copies (RST_FOREST=1, PCID_LOCAL=1), the
RTL the hdie_pc_ctrl_mc3_{p540,q648} kits route. Verilator 5.050, ot-epyc5, the kits' daemon bench stages.
- face_txn_mc3_pos.log  PASS reqs=6000 beats=12944 wcols=759 wdone=759 edges_h9b=88783 edges_safe=166921 -- identical edge
  count to the pre-fix face top (face_txn/face_pos.log): the forest keeps the 5 release edges, 0 data cycles added.
- face_txn_mc3_mut_idtag.log  MUT_ID_TAG=1 FAIL errors=12944 (fail witness; regex 'BW_FACE_TXN FAIL errors=[1-9][0-9]* MUT_ID_TAG=1').
