HBM-MC3c (10-19): MC3b + POST_REG=1 (register stage on the post-metadata SRAM read data) + AQ ACT_HEAD=1. The RTL the
hdie_pc_ctrl_mc3c_{p540,q648} kits route (parallel fallback of mc3b). Verilator 5.050 on ot-epyc5 (kit bench stages).
Why: the MC3 gates' placement-TT macro->reg misses at 833 ps (p540 -113.2 ps, q648 -148.0 ps) -- all 400 worst paths
start at METADATA[*].u_post rd_out[63] (302 ps SRAM clk->q, the entry's write flag) -> push_read -> enqueue_aq -> AQ wr_v
-> bank_n / bank_n_word_local / look_row / head_local / unposted (path report: physical STA of the mc3 4_1_cts odbs).
Fix: the post entry (bank, col, row, read flag, 8 regional bank + row copies) is captured in kept stage flops and enters
the AQ one edge later; wr_v = 9 kept copies (wr_v_regions); posting is no longer a function of the SRAM output (the
read-reservation check covers every entry); wr_r2 guards the in-flight entry (redundant with the K credit count<=QD).
ACT_HEAD: with the shifted timing the fixed bank-0-first ACT order starved a closed bank-31 head for ever (REFpb re-closed
low banks every 118 cycles): face_txn stalled at 7909/12944 beats (mut_noacthead witness). ACT candidates now start at the
v2 fix: head-bank ACT override -- when the head entry's bank is closed and not refresh-blocked, the row command issues
ACT(head bank, head row) ahead of the per-group candidate (one 32:1 select on the registered head; head row = look_row[hb]).
(v1 6005d1419 rotated the candidate order from the head bank: gate WARN/GRT 0 but native census OVER32 123/136 from the
rotation selects -- ac_hg_local 228 loads -- so it was replaced.)
- face_txn_mc3c_pos.log  PASS reqs=6000 beats=12944 wcols=759 wdone=759 edges_h9b=88783 edges_safe=107782
  (MC3b 166921: the random-address stream is 35% faster -- the old ACT order also starved heads there).
- face_txn_mc3c_mut_idtag.log  MUT_ID_TAG=1 FAIL errors=12944 (witness).
- face_txn_mc3c_mut_noacthead.log  -DBW_AQ_MUT_NO_ACT_HEAD FAIL errors=3 (stall 7909/12944 beats; witness).
- bank/  tb_hbm_bw_pc4 EXPOSE census, rotated ds layout, --mc3c: steady 91.68 / 92.76 / 91.70 B/edge/SM (MC3b 91.62 /
  92.74 / 92.94), packed 103.86 (103.89) -> >= 90 floor kept.
- price (results/arch/hbm_reprice_1019/reprice3c_mc3c_*.json, d4g_reprice3c --bw 90.67 --bridge 2 = +1 edge on every HBM
  operand record, same tool run for MC3b: reprice3c_mc3b_p540_sametool.json): DS AR 1598.1 -> 1597.1 tok/s (-0.06 %),
  Qwen 757.0 -> 756.8 (-0.03 %). BW floor kept at 90.67 (census did not drop).
- full96/face_mc3c_pos  (v1 source 6005d1419; post stage identical in v2) SMB_UNIT PASS 66/154 END 45260 = MC3b: the +1 post
  edge is hidden by the production static calendar.
