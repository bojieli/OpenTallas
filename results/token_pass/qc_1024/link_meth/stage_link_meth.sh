#!/bin/bash
# QC token side 10-25: stage source assembly + link fixtures for tp8 / xdie / ovl4u on the meth bind constants (epyc1).
# = results/token_pass/qc_tok_1024/link/tools_bound/stage_local.sh with ASM = claude/qc-tok-meth-1024 base and L on scratch2.
set -eu
W=/srv/opentallas-scratch2/claude/wt/qc-tok-meth; G="git -C $W"
ASM=${ASM:-a281ceb5ce}; L=/srv/opentallas-scratch2/claude/qc-tok/meth/link/rr
ASMFULL=$($G rev-parse $ASM)
rm -rf $L; mkdir -p $L/src
$G archive $ASM rtl tools configs physical/asap7_memory_macros physical/asap7_memory_macros_v2 | tar -x -C $L/src
echo $ASMFULL > $L/src/ASM_COMMIT
OVLB=967c24eed; RELB=origin/claude/tok-func2-qw-1021; SF7V=545cdd4bc; FIX=f98fd830f; C0=c0f8097f3; MAIN=$ASM
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
$G archive $ASM physical/qwen_kv_die_phy physical/asap7_memory_macros_v2 results/arch/token_path_20261009 \
   results/arch/qwen_split_compute_1014/res_train_decision_1015 | tar -x -C $L/xdie/fx
(cd $L && find tp8/fx ovl4u/fx xdie/fx -type f | sort | xargs sha256sum > link_fixtures.sha256)
# tools (committed copies of the 10-24 link sub-lane)
mkdir -p $L/tools_bound; $G archive $ASM results/token_pass/qc_tok_1024/link/tools_bound | tar -x -C $L/tools_bound --strip-components=5
# bound pair image (regen_constants xdie_pair_image recipe, XDIE_DIE_STAGES of the meth bind + kv41 peer)
( cd $W && D2D_DIE_STAGES=2,2,2,3,2,2/34,34,32,32,32,31,31 D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 \
    bash tools/qwen_split/d2d_cal_image_production.sh $L/xdie/fx/img_bound ) > $L/img_bound.log 2>&1
# static MU calendar recompiled at the implemented LS (COLL_LS / MU_CAL_LS of the meth bind; ls 389 reproduces the
# committed qc_tok_1024/link/tp8/mu_cal_ls389.json apart from its "source" note); run as a package from tools/
( cd $W/tools && python3 - $L/tp8/mu_cal_ls${MU_LS:?}.json ${MU_LS} ) <<PY > $L/mu_cal.log 2>&1
import sys, json
from qwen_static_schedule.mu_calendar import compile_calendar, bench_cases
cal = compile_calendar(dict(users=4, occupancy="measured", head_chunks=8, ls=int(sys.argv[2])), tokens=3, policy="priority")
d = bench_cases(cal)
d["source"] = {"tool": "tools/qwen_static_schedule/mu_calendar.py", "call": "compile_calendar(dict(users=4, occupancy='measured', head_chunks=8, ls=%s), tokens=3, policy='priority'); bench_cases(cal)" % sys.argv[2], "note": "QC token side 10-25: recompiled at the meth bind COLL_LS / MU_CAL_LS"}
json.dump(d, open(sys.argv[1], "w"), indent=1)
print("MU_CAL OK ls", sys.argv[2])
PY
# release OVL bench: the assembly's own copy (main 93985ba5ee real p192 replay master d2d_sram_1r1w_64x137_m1_r2c2_p192 +
# dc11eabc33 kind14 record-witness check; RTL and tb changed together).  The 10-21 tok-func2-qw copy names the old
# ot_sram_..._p192 alias -> MODMISSING on every config (logs/ovl4u_fail1_stale_bench.log)
for f in run_d2d_ovl_mu_rel.sh tb_d2d_ovl_mu_rel.sv; do cp $L/src/rtl/test/qwen_split/$f $L/ovl4u/fx/rel/rtl/test/qwen_split/$f; done
# tp8 lanes record (collector input; the bound top has no GEN coll_lane_latency.json), written from the regen constants:
# contents = link_meth/tp8/lanes/{coll_lane_latency.json,SOURCE}
mkdir -p $L/tp8/fx/lanes
echo STAGED $(wc -l < $L/link_fixtures.sha256) fixture files
