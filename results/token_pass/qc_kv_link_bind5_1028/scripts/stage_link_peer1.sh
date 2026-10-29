#!/bin/bash
# TOK-QK-PEER-1 10-28: the TOK-QK-XD4 link stages (xdie / ovl4u) re-pointed at the CURRENT binds:
#   QC  = codex/qc-bind-1027 fresh_v6 strict bind (latest QC bind; no ONEQC bind yet)
#   KV  = DIE-KV-16 bind5 (claude/die-kv-16-1028@7505ca76e0, intel1 die-kv-16-1028/bind5)
# Same assembly (ASM 5832e6722) + fixtures as XD4 (results/token_pass/qc_kv_link_b48_1026/scripts/stage_link_xd4.sh);
# the pair image is produced by ASM tools/qwen_split/d2d_cal_image_production.sh at D2D_STAGES (from regen_constants --peer).
# Control: STAGES_CTRL (B48 seams) must reproduce the XD4 image sha ac290539... (tool-equivalence proof).
# K mutant word = the stale B48 word 03030489 (what XD4 / the last pair image assumed) -- the real drift.
# usage: QCCONST=.. QCB=.. KVB=.. D2D_STAGES=.. MU_LS=.. L=RUNROOT stage_link_peer1.sh
set -eu
REPO=/srv/opentallas-scratch2/claude/moved/home__ubuntu__OpenTallas; G="git -C $REPO"
HERE=$(cd "$(dirname "$0")/.." && pwd)
ASM=${ASM:-5832e672235d955164c31991b09f3cee96ee4de2}; L=${L:?RUNROOT}
rm -rf $L; mkdir -p $L/src
$G archive $ASM rtl tools configs physical/asap7_memory_macros physical/asap7_memory_macros_v2 \
   results/rtl/qwen_layer_tput_1018/compiled_L1 results/arch/qwen_split_compute_1014/res_train_decision_1015 results/arch/qwen_kv_static_programme_1017 | tar -x -C $L/src
$G rev-parse $ASM > $L/src/ASM_COMMIT
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
mkdir -p $L/tools_bound; $G archive $ASM results/token_pass/qc_tok_1024/link/tools_bound | tar -x -C $L/tools_bound --strip-components=5
cp $HERE/tools_bound/* $L/tools_bound/; (cd $L/tools_bound && sha256sum * > ../tools_bound.sha256)
BC=$(python3 $L/tools_bound/bound_txdp.py --die qwen_compute ${QCB:?} --json $L/bound_txdp_qc.json)
BK=$(python3 $L/tools_bound/bound_txdp.py --die qwen_kvsys ${KVB:?} --json $L/bound_txdp_kv.json)
MK=${MUT_TXDP_K:-03030489}      # the B48 word the last pair image / XD4 carried (stale vs bind5)
MC=$(printf "%08x" $(( 0x$BC + 1 )))
printf "XQ_BOUND_TXDP_C=%s\nXQ_BOUND_TXDP_K=%s\nXQ_MUT_TXDP_C=%s\nXQ_MUT_TXDP_K=%s\n" $BC $BK $MC $MK > $L/bound_txdp.env
img() {  # img OUTDIR STAGES
  ( cd $L/src && D2D_DIE_STAGES=$2 D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 \
      bash tools/qwen_split/d2d_cal_image_production.sh $1 ) ; }
img $L/xdie/fx/img_bound ${D2D_STAGES:?} > $L/img_bound.log 2>&1
img $L/xdie/fx/img_ctrl_b48 ${STAGES_CTRL:-2,2,2,3,2,2/68,68,66,66,66,67,67} > $L/img_ctrl_b48.log 2>&1
[ -n "${STAGES_MUT:-}" ] && img $L/xdie/fx/img_mut ${STAGES_MUT} > $L/img_mut.log 2>&1
(cd $L && sha256sum xdie/fx/img_*/d2d_cal_image.svh > pair_image.sha256)
( cd $L/src/tools && python3 - $L/tp8/mu_cal_ls${MU_LS:?}.json ${MU_LS} ) <<PY > $L/mu_cal.log 2>&1
import sys, json
from qwen_static_schedule.mu_calendar import compile_calendar, bench_cases
cal = compile_calendar(dict(users=4, occupancy="measured", head_chunks=8, ls=int(sys.argv[2])), tokens=3, policy="priority")
d = bench_cases(cal)
d["source"] = {"tool": "tools/qwen_static_schedule/mu_calendar.py", "call": "compile_calendar(dict(users=4, occupancy=measured, head_chunks=8, ls=%s), tokens=3, policy=priority); bench_cases(cal)" % sys.argv[2], "note": "TOK-QK-PEER-1 10-28 (= XD4 recipe)"}
json.dump(d, open(sys.argv[1], "w"), indent=1)
print("MU_CAL OK ls", sys.argv[2])
PY
for f in run_d2d_ovl_mu_rel.sh tb_d2d_ovl_mu_rel.sv; do cp $L/src/rtl/test/qwen_split/$f $L/ovl4u/fx/rel/rtl/test/qwen_split/$f; done
mkdir -p $L/tp8/fx/lanes; python3 $HERE/scripts/lanes_from_constants.py ${QCCONST:?} $L/tp8/fx/lanes/coll_lane_latency.json
cp $HERE/scripts/run_link.sh $L/run_link.sh
echo STAGED $(wc -l < $L/link_fixtures.sha256) fixture files; cat $L/bound_txdp.env; cat $L/pair_image.sha256
