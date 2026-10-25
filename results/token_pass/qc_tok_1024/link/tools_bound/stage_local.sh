#!/bin/bash
# QC-TOK link (10-24): stage the source assembly (origin/main 3e05af806b) + link fixtures (stage_link_fixtures.sh sources by
# commit) for tp8 / xdie / ovl4u on the QC bound_r8 constants, into a local RUNROOT, then rsync to intel1.
set -eu
ASM=${ASM:-3e05af806b}; L=$HOME/scratch/qc-tok-link/rr; G="git -C $HOME/OpenTallas"
ASMFULL=$($G rev-parse $ASM)
rm -rf $L; mkdir -p $L/src
$G archive $ASM rtl tools configs physical/asap7_memory_macros physical/asap7_memory_macros_v2 | tar -x -C $L/src
echo $ASMFULL > $L/src/ASM_COMMIT
# --- link fixtures (stage_link_fixtures.sh, same commits; lanes: the bound top has no coll_lane_latency.json -> tp8 uses
# the bind's COLL_BENCH_ARGS fixed lanes instead)
OVLB=967c24eed; CTXB=origin/codex/qw-token-pickup-takeover3-1019; MAIN=$ASM
RELB=origin/claude/tok-func2-qw-1021; SF7V=545cdd4bc; FIX=f98fd830f; C0=c0f8097f3
PHY=(physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2 physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv)
mkdir -p $L/tp8/fx $L/ovl4u/fx/overlay $L/ovl4u/fx/rel $L/xdie/fx
$G archive $MAIN results/rtl/mu_qwen_1018/coll/mu_cal.json | tar -x -C $L/tp8/fx
$G archive $C0 "${PHY[@]}" results/arch/qwen_kv_static_programme_1017/die | tar -x -C $L/ovl4u/fx
$G archive $OVLB rtl/test/qwen_split/run_d2d_ovl_mu.sh rtl/test/qwen_split/tb_d2d_ovl_mu.sv | tar -x -C $L/ovl4u/fx
$G archive $OVLB rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv | tar -x -C $L/ovl4u/fx/overlay
$G archive $RELB rtl/test/qwen_split/run_d2d_ovl_mu_rel.sh rtl/test/qwen_split/tb_d2d_ovl_mu_rel.sv | tar -x -C $L/ovl4u/fx/rel
$G archive $C0 physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p288 | tar -x -C $L/ovl4u/fx/rel
$G archive $SF7V physical/asap7_memory_macros_v2/ot_sram_1r1w_64x137_m1_r2c2_p192 | tar -x -C $L/ovl4u/fx/rel
$G diff $C0 $FIX -- tools/qwen_static_schedule/mu_calendar.py > $L/ovl4u/fx/mu_calendar_attwin.patch
# xdie fixtures: PHY model + macros_v2 views + results/arch token path + res_train decision (from the assembly commit)
$G archive $ASM physical/qwen_kv_die_phy physical/asap7_memory_macros_v2 results/arch/token_path_20261009 \
   results/arch/qwen_split_compute_1014/res_train_decision_1015 | tar -x -C $L/xdie/fx
(cd $L && find tp8/fx ovl4u/fx xdie/fx -type f | sort | xargs sha256sum > link_fixtures.sha256)
echo STAGED $(wc -l < $L/link_fixtures.sha256) fixture files
