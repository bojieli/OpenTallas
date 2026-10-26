#!/bin/bash
# TOK-QK-XD3 10-26: stage source assembly + link fixtures for tp8 / xdie / ovl4u = the TOK-QK-XD2 method
# (results/token_pass/qc_kv_link_v7_1025/scripts/stage_link_v7.sh) re-pointed at
#   QC  = v7 final strict bind (codex/qc-phase-2209@13f33606a; bound_sha 28380fe5cb7fbf91)
#   KV  = b23h2 strict bind (claude/tok-kv-b23h-1026@c6602a6ae8 = bind-of-record plan c20ef31508 + PATH-KV hook a795ac1cb6
#         + kvchk 0b8b9727a8; the rebase-0010 hook values on the b19-equivalent plan; bound_sha 91a2dc2799e166ed)
# Differences vs XD2: ASM pinned to 5832e6722 (same assembly), seams from regen_constants (kvchk2 aac29eda2d) with peer b23h2,
# tools_bound overlaid with this receipt's tools_bound/ (bound TXDP into both masters, TXDP_BOUND gate + 2 mutants),
# and the BOUND TXDP words read from BOTH bind dirs by tools_bound/bound_txdp.py (env file L/bound_txdp.env).
# usage: QCCONST=<regen_constants QC json> QCB=<qc bind dir> KVB=<kv bind dir> KVB_STALE=<b19 bind dir> D2D_STAGES=.. MU_LS=.. stage_link_xd3.sh
set -eu
W=/srv/opentallas-scratch2/claude/wt/tok-qk-xd3; G="git -C $W"
ASM=${ASM:-5832e672235d955164c31991b09f3cee96ee4de2}; L=/srv/opentallas-scratch2/claude/tok-qk-xd3/link/rr
RCPT=$W/results/token_pass/qc_kv_link_rebase_1026
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
mkdir -p $L/tools_bound; $G archive $ASM results/token_pass/qc_tok_1024/link/tools_bound | tar -x -C $L/tools_bound --strip-components=5
cp $RCPT/tools_bound/* $L/tools_bound/; (cd $L/tools_bound && sha256sum * > ../tools_bound.sha256)
# the BOUND TXDP words of both strict binds (+ the stale b19 KV word = the real defect XD2 found, used as the K mutant)
BC=$(python3 $L/tools_bound/bound_txdp.py --die qwen_compute ${QCB:?} --json $L/bound_txdp_qc.json)
BK=$(python3 $L/tools_bound/bound_txdp.py --die qwen_kvsys ${KVB:?} --json $L/bound_txdp_kv.json)
MK=$(python3 $L/tools_bound/bound_txdp.py --die qwen_kvsys ${KVB_STALE:?} --json $L/bound_txdp_kv_stale.json)
MC=$(printf '%08x' $(( 0x$BC + 1 )))   # compute CMD port 0 one edge late
printf 'XQ_BOUND_TXDP_C=%s\nXQ_BOUND_TXDP_K=%s\nXQ_MUT_TXDP_C=%s\nXQ_MUT_TXDP_K=%s\n' $BC $BK $MC $MK > $L/bound_txdp.env
( cd $W && D2D_DIE_STAGES=${D2D_STAGES:?} D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 \
    bash tools/qwen_split/d2d_cal_image_production.sh $L/xdie/fx/img_bound ) > $L/img_bound.log 2>&1
( cd $W/tools && python3 - $L/tp8/mu_cal_ls${MU_LS:?}.json ${MU_LS} ) <<PY > $L/mu_cal.log 2>&1
import sys, json
from qwen_static_schedule.mu_calendar import compile_calendar, bench_cases
cal = compile_calendar(dict(users=4, occupancy="measured", head_chunks=8, ls=int(sys.argv[2])), tokens=3, policy="priority")
d = bench_cases(cal)
d["source"] = {"tool": "tools/qwen_static_schedule/mu_calendar.py", "call": "compile_calendar(dict(users=4, occupancy='measured', head_chunks=8, ls=%s), tokens=3, policy='priority'); bench_cases(cal)" % sys.argv[2], "note": "TOK-QK-XD3 10-26: recompiled at the QC v7 final bind COLL_LS / MU_CAL_LS"}
json.dump(d, open(sys.argv[1], "w"), indent=1)
print("MU_CAL OK ls", sys.argv[2])
PY
for f in run_d2d_ovl_mu_rel.sh tb_d2d_ovl_mu_rel.sv; do cp $L/src/rtl/test/qwen_split/$f $L/ovl4u/fx/rel/rtl/test/qwen_split/$f; done
mkdir -p $L/tp8/fx/lanes; python3 $RCPT/scripts/lanes_from_constants.py ${QCCONST:?} $L/tp8/fx/lanes/coll_lane_latency.json
cp $RCPT/scripts/run_link.sh $L/run_link.sh
echo STAGED $(wc -l < $L/link_fixtures.sha256) fixture files; cat $L/bound_txdp.env
