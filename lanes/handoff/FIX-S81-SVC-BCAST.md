# FIX-S81-SVC-BCAST handoff (Opus; started by FIX-LEDGER 11-23 ~02:0x PST)
Goal: ledger rc16 / row SVC-BCAST-STAGE: RTL replication of svc broadcast drivers (one copy per core row, same cycle), LEC maps dups.
Deadline: gated rows to S81-J6-ASSEMBLY-R5 by 10:30 (Wave A, f65f); hard stop 12:30. Co-owner/reviewer FABLE-UNC-S81-SVC (ad36422a39196fd09). Owner lane SVC-R9 acbf5f53765607888. FIX-LEDGER agent acd269758d3b62a53.
Lane clone: epyc10 /srv/opentallas-scratch2/claude/fix-s81-svc-bcast/repo (main 6734f6deff0 at clone). tmp: .../fix-s81-svc-bcast/tmp
Drivers (R8 hi4 place smells, epyc7 opus-fix-s81-svc-r8-north/hi4_place_only/{rest_review/gpl_render,att_review/gpl_render_r9}/smells.json):
- rest: g_u_rsv_u_src_aa4db9e7 = 2-bit sync in dsdv_svc_rs_c (src line ~140 of j7_hi4 form), q[0] fo 9736, q[1] fo 378 (sync reset w_u_rsv_u_3_Y)
- rest: src_99f4c3e7 q[16] fo 1018; driver_pp_v fo 1026; src_235caab2 fo 269
- att: u_bin_i_attn_o0_p q[805] fo 1796 (cut-bus landing bit 805); _059875_ fo 2048
- att: u_eng e_iv / e_ibank[2:0] (ot_hdc_v41x_attn_s E register) fo 32 hcores each
Status: investigating RTL.
