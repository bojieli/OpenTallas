#!/bin/bash
# KV-BIND 10-24 kv44 re-bind (owner decision 9).  Run on a fleet host (epyc2 used: elab ~10 GB, bind+verify+lint 2,472 s, peak 11.1 GB).
#   mk_kv44.sh SCRATCH OUT [ASBUILT_JSON]
# 1. source tree SCRATCH/t38 = git archive e33504a6f (all but physical/ref_tile; + ref_tile/*/*.json) overlaid with
#    d13ff7c78 tools/die_plan, physical/die_plan, rtl/qwen_sys/kv_plan_leaves_1023, rtl/lib/ot_dp_*.sv (kv44/mk_tree.sh) and
#    the TOK-QK request sources: rtl/qwen_sys/kv_host_obs_20261019/{qkd_host_root_admission_obsx_bo1,qkd_d2d_boot_event_bridge}.sv,
#    rtl/qwen_sys/d2d_static_20261015/{ot_qwen_d2d_sfm,ot_qwen_d2d_safe_fo,ot_qwen_status_observers_v1}.sv,
#    results/rtl/qwen_rom_pair_candidate_1024; kv44/rtl/qkd_d2d_cal_seq_bc4_pair1024.sv = kv44/gen_dcal_pair1024.py t38
# 2. as-built netlist = bind/inputs/kv_bound_rtl6 (reconstructed; see kv44/README.md for the proof)
# 3. ASAP7 cell models from the ORFS image -> SCRATCH/asap7_cells, substituted for @ASAP7_CELLS@
# 4. bind.py all (elab + bind + verify + lint), then bind_post.py
set -euo pipefail
S=$1; OUT=$2; T=$S/t38; K=physical/die_plan/qwen_kvsys/bind
AB=${3:-$T/$K/kv44/asbuilt_kv44.json}
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
sed "s#@ASAP7_CELLS@#$S/asap7_cells#g" $AB > ${AB%.json}_r.json
cd $T
/usr/bin/time -f "%e s %M KB" python3 tools/die_plan/bind.py ${MODE:-all} physical/die_plan/qwen_kvsys/die_plan.json \
  --asbuilt ${AB%.json}_r.json --out $OUT --mem 200
# then (run separately):
#   python3 tools/die_plan/bind.py portbind physical/die_plan/qwen_kvsys/die_plan.json --asbuilt ${AB%.json}_r.json --out $OUT
#   python3 tools/die_plan/bind_post.py --die qwen_kvsys --bound $OUT --smoke submit
