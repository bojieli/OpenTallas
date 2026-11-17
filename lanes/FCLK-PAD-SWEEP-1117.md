# FCLK-PAD-SWEEP-1117
Method: rtx-pro copy /home/ubuntu/signed-export-1114, 6_final.v netlists for s81, s81_head (HEAD), qwen_compute (QC), qwen_kvsys (KV); HBM skipped. Counted delaybuf_otstb, then traced backward from output ports matching fclk_out*/*fwd_fclk*/cland_*fclk* through the buffer chain.
Scope: 250 of 265 view dirs have 6_final.v; 15 have none and were not checked. 41 netlists contain delaybuf_otstb, mostly as interior balance pads.

| die | type | view | pads per fclk_out port | hops | verdict |
|---|---|---|---|---|---|
| HEAD | hd_st_n3_turn | hd_st_n3_turn__nf15_pin_pg_1116 | fclk_out_u1_o 96, fclk_out_d1_o 96 | 106 / 108 | AFFECTED |
| S81 | - | none | - | - | clean |
| QC | - | none (40 pad-bearing views have no fclk port) | - | - | clean |
| KV | - | none | - | - | clean |
