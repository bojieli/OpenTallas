# Regeneration record: HBM-COLLECT-1/SRC (2026-11-09)

Byte-exact copies of signed HBM kit RTL. They follow the counted_1109 pattern
(fe576b1089). Each one is a reference copy only and replaces no shared main file.
COORD ruling: COUNT-ARCHIVE-2 RESULT RULINGS (3).

Columns: path | git blob | sha256 | origin.

Generator for the seven SM files: physical/die_plan/hbm_arch_cores/sm/gen_sm_kit.py @ eaba5ac4ff (sha256 abafbea375f8914d822fcb9ffa616f01d43e9f2b032e0c0e6fa38f452812a746).
That generator copies the as-built sources from
physical/die_plan/hbm_arch_cores/sm/asbuilt_1108/ into each kit.
The six be/be_seed blobs first appear in 54621045e3. The gu blob is at f085549fcb.
Both commits are ancestors of main 8b3811a02c, where each file is byte-identical.

- rtl/hbm_accel/counted_1109/REGEN_hbm_collect_src_1109.md | 3b67baec526d59e86898c3f7a4b9f7d303ee1239 | f1a351ed1bfa061ce6b18a60aad32225eab670897bd26bca0fa3b12447ee6399 | generated: asbuilt_1108/REGEN_hbm_collect_src_1109.md @ 54621045e3. Kit signed/REGEN_hbm_collect_src_1109.md_*_eco*.
- rtl/hbm_accel/counted_1109/ot_hbm_accel_smh_tcl_gu/ot_hbm_accel_smh_gu.sv | f2dec0116aba1f6967f0c2edbef5c78ce07139d5 | 64578614df397f1be378de9ca3bfa3d3e5b865fc41f49753602fba7eaa219d1a | generated: asbuilt_1108/ot_hbm_accel_smh_gu.sv @ f085549fcb. Kit ot_hbm_accel_smh_tcl_gu_ecd4cf53a976_ecohm.
- rtl/hbm_accel/counted_1109/ot_hbm_sm_attn_be__cd13/ot_hbm_sm_attn_be__cd13.sv | cf6f8fb8a8d0c125bfe4c74217f0d0b153e05321 | f855311d5b25cc1a12e8a5d0e5741cba28b6df99cfc766376a9950284f28c742 | generated: asbuilt_1108/ot_hbm_sm_attn_be__cd13.sv @ 54621045e3. Kit signed/ot_hbm_sm_attn_be__cd13_*_eco*.
- rtl/hbm_accel/counted_1109/ot_hbm_sm_attn_be__cd16/ot_hbm_sm_attn_be__cd16.sv | 79fe830ee434d6e766cda9251f5616f1df7bef7a | c574321d164afb8fed79a2fbc0240bd749147f12480247d95a7f75fa2bd6e243 | generated: asbuilt_1108/ot_hbm_sm_attn_be__cd16.sv @ 54621045e3. Kit signed/ot_hbm_sm_attn_be__cd16_*_eco*.
- rtl/hbm_accel/counted_1109/ot_hbm_sm_attn_be__cd17/ot_hbm_sm_attn_be__cd17.sv | d5616888c65f2b3aaa3f05c01cf7bb85c2d7e826 | b12cb32395cb50dfd30c203a92ed7862a5d4eb1abed955a17a357b211b17f0fd | generated: asbuilt_1108/ot_hbm_sm_attn_be__cd17.sv @ 54621045e3. Kit signed/ot_hbm_sm_attn_be__cd17_*_eco*.
- rtl/hbm_accel/counted_1109/ot_hbm_sm_attn_be__cd9/ot_hbm_sm_attn_be__cd9.sv | 2b481bff218a9e88b5a202c422f139d14fb6bf16 | c2fc651a5771adbc283012dc77870cbfd937560dece0d764b6b605c5172999af | generated: asbuilt_1108/ot_hbm_sm_attn_be__cd9.sv @ 54621045e3. Kit signed/ot_hbm_sm_attn_be__cd9_*_eco*.
- rtl/hbm_accel/counted_1109/ot_hbm_sm_attn_be_seed__cd20/ot_hbm_sm_attn_be_seed__cd20.sv | a9e884c770102696c7ff186adca0e1478d67c3af | a9eb250067cc0258db40e373a27260503f4ea0622fd42335379fac45f9ad52e9 | generated: asbuilt_1108/ot_hbm_sm_attn_be_seed__cd20.sv @ 54621045e3. Kit signed/ot_hbm_sm_attn_be_seed__cd20_*_eco*.
- rtl/hbm_accel/counted_1109/ot_hbm_sm_attn_be_seed__cd21/ot_hbm_sm_attn_be_seed__cd21.sv | 05a1e34090ce7b4764978080b5c29808822611cb | 703f6437728d9895dfde9d268a5c4d2f2615f06c4db3ed8681de419a0db44167 | generated: asbuilt_1108/ot_hbm_sm_attn_be_seed__cd21.sv @ 54621045e3. Kit signed/ot_hbm_sm_attn_be_seed__cd21_*_eco*.
- rtl/hbm_accel/counted_1109/ot_wbq_root_g0/ot_wbq_root_s7.sv | a248b3c8f1f3de88d96126337486bbc40e8ee7e9 | 94a79a2d973c7a100695c11797fc3a8b84a84a7a3c9243a5a53829cc2f589012 | HAND-WRITTEN (no generator). Kit epyc4:codex-hbm-root-s7-1107/kit_g0_vS7/rtl. Private ROOT S7 source; shared ot_wbq_split.sv is untouched.
