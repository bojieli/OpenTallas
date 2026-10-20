# HBM-RATE8 (10-20): current-main token census + COLLFUSE2 PRETREE=1 witnesses

Branch `claude/hbm-rate8-1020` from origin/main 995560419 (rtl/hbm_accel, tools/hgi_sim, tools/hbm_static unchanged since
HBM-RATE7 95d00f526, so the RATE7 rebased SMXL/INT8W RTL re-verifications stand on current main).

## Census on current main (`census/`)
RATE7 ran its census in the older ep6 `hbm-smxl-census-1019` bundle, whose tools/hgi_sim differs from main (timing.py,
toksim_hbm_census_1019.py, collq_gather_1018.py). Re-run with main's tools/hgi_sim (md5-identical overlay), same inputs,
`--measured --bw 98 --bridge 1`, row info_banklat_all + SUFIX delta rule (tok_from_sched.py):

| input | DS AR tok/s | Qwen AR tok/s | RATE7 (old tools) |
|---|---:|---:|---|
| m_base (PRETREE3) | 1148.8 | 1027.5 | 1148.8 / 1000.7 |
| m_xl_i8 (+SMXL2 x path, +INT8W) | **1341.1** | **1028.4** | 1341.1 / 1001.5 |
| m_all (+COLLFUSE2 L1 fuse + TP-8 SU rows) | 1341.1 | 1023.7 | 1341.1 / 1011.3 |

DS is unchanged (894.8k token cycles; 1,650 needs ~727k). Qwen on main: COLLFUSE2 cuts COLL.ALL_REDUCE_SUM 132.0k -> 120.4k
but its as-built 4-row TP-8 SU rows raise SU.VOP 117.1k -> 133.9k, net -4.7 tok/s: the best measured Qwen row is m_xl_i8
1028.4 (COLLFUSE2 L1 fuse alone is the keeper; the TP-8 SU row remap needs the pre-tree form for bf16_p/pv to pay).
All component-bench-bound (not die-bound, not a release token).

## COLLFUSE2 causal witnesses on current main plumbing (`mutf_pt/`)
The ep9 HBM-RATE7 witnesses (frozen packet codex/hbm-rate7-mutf-collect-1020 019e7a7b2, pushed) ran a TB/runner without
PRETREE/tree_cmd (PRETREE0). `run_mutf_pt.sh` re-runs the five qw8_* records on main's run_toksim_su.sh/tb_toksim_su_top.sv,
build mr10 PT=1, vectors from prod_compile.py --pretree; POS must PASS with PRETREE=1, +MUT_FORCE must FAIL.
Fleet: ot-epyc9:/srv/opentallas-scratch/claude/hbm-rate8-1020/suvop/out/verdict.txt (pending). Compiled stream cycles match
the m_all shapes exactly: softmax_max 504.0, bf16_p 380.0, pv_normalize 136.0, round_q 82.67, row_scale_qkv 90.67.
