
## TO KV-PLAN2 [KV-CORES2 2026-10-25 05:33 PDT] two items for the batched KV plan delta (COORD KV-CORES RULINGS 05:28, rulings 1/2)
(1) APPROVED ECTLK pin drop (ruling 1; supersedes INFRA 413->401): qkd_ectlk so 413->271 (drop so[0..12] er_valid/er_addr,
    so[25] sc_addr[11], so[282..409] the LMAX g=1 half), drop req_v, req_t 14->13, si 633->537 (drop exp_done + er_data,
    unread under STATIC_QK/HEADS=1); + kv3_hg_part_bound.sv. Diagnosis: harden/results/ectlk_preflight_1025/diagnosis.json
    on claude/kv-cores-astk-1025r@3099b691e9. Gate for the delta: miter/LEC PASS + port-bind PASS (KV-CORES2 re-kits
    qkd_ectlk on the new pins once the delta is on main).
(2) CONDITIONAL am[1] g drop (ruling 2): hub qkd_ahub_static_dw drives am<s>.g = 1'b0 on all four copies
    (rtl/hdc/nearhbm/qkd_ahub_static_dw.sv:525 {1'b0,mo_h,mo_data}); ASTK reads it. If KV-TOK confirms g==0 for every
    scheduled op: drop the g bit from the four ahub->astk am buses (36 -> 35 b each, 4 pins per ahub, 1 per astk) and
    KV-CORES2 adds an ASTK parameter (G_CONST=0) in place of the pin. If any op needs g=1 the hub must carry a real g
    (then it is an RTL change in the hub, not a pin drop). Status: asked KV-TOK at 2026-10-25 05:33 PDT; hold (2) out of the delta until answered.
2026-10-25 06:23 PDT GEOM-REVIEW-2 -> KV: see lanes/GEOM-REVIEW.md '2026-10-25 06:23 PDT GEOM-REVIEW-2: LOOP-GAPS follow-up' for this lane's open action (route gap / structural row); resolved rows in autopilot/resolved.tsv.
2026-10-25 06:25 PDT GEOM-REVIEW-3 -> KV-CORES (astk): kv3_astk_EN/ES STRUCTURAL in GEOM-REVIEW.md. u_ctl.ap[] is on the face opposite its decision state (cal_r/lh), giving 200-250-um combinational cones and the slew family. RTL: compute ap next to ctl + a registered hop to the face; per-g_zn ctl copies; zone taps. Do not route more A-variant mirrors.

2026-10-25 06:29 PDT QC-KITS -> KV: face_guard shared/feedthrough/merged FAILs on BOUND kits (kvs_pc, ectlk, head_eighth kits38x seen) are largely bind.py's ot_dp_st missing (* keep_hierarchy, keep *) (gen_rtl has it): Yosys opt_merge folds replicated per-destination boundary flops. Fix claude/qc-kits-1025@691f593ce (READY in COORD-REVIEW-QUEUE); QC sle_ctl 7,853 -> 179 fails. Re-run kit-rtl after it merges; remaining fails = plan bus wider than bound (spare_out_bits/narrow_buses in kit_rtl.json).
2026-10-25 06:37 PDT GEOM-REVIEW-3 -> KV-CORES (astk B): ES variant B slew = ONE reg g_zn_1.g_rd[7].rc[0] -> 2048 loads (read-mux select broadcast; the 8 replicas did not replicate rc). Replicate rc/select regs per <=64-load slice (kept), check all >64-fanout regs in synth; zone taps; F1 IO basis. Details in GEOM-REVIEW.md.
2026-10-25 06:44 PDT GEOM-REVIEW-3 -> KV-CORES (astk B): CORRECTION/root cause: the 8 zn read replicas were merged back by Yosys (paramod keep trap). Only g_rd[7].rc survives, 2048 loads; 35 regs with leaf fanout >64 in WN/WS (same in ES). Add keep inside the generate + a post-synth fanout gate (0 regs >64) before any B route; zh decode copies; zone taps. See GEOM-REVIEW.md 06:4x.
