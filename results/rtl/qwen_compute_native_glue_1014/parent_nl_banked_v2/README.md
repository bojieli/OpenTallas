qfd_tile_nl_banked_v2 (PM-H-S, r13 NL helper 2026-10-15): NL banked v1 with face_t_out = qwen_glue_w514 (v514 RTL, W=q,
pins local y 5.292+0.192k) at R0 (5.4, 699.84) and t_out[k] on the tile TB window y = 705.132 + 0.192k (odd TB slots empty).
Benches (Verilator 5.032 EPYC4 /srv/opentallas-scratch/claude/q15-nl-banked-bench4) vs the NL staged reference:
m0 PASS 3499/264; all-banks + split-fault PASS 5959/448 (5176 fault words); mutants m1 (TX) and m4 (to_reg bypass) FAIL.
leaf_benches/: iverilog qwen_glue_x1028 (m0 PASS 3805656 checks, m1/m2 FAIL) and qwen_glue_w514 (m0 PASS, m1/m2 FAIL).
Kit not generated: needs the CLOSED qwen_glue_w514 view (job qwen_glue_w514-pm1-b0610f1ce in intake); hard-face audit
hard_face_binding_nl_v2.tcl must gain the w514 view hashes then. Physical qualification OPEN.
