
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
