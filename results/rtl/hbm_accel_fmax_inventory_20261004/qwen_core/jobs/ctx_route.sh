#!/bin/bash
# Route the die-control context (generated core + stream gating + unit stubs): ctx_route.sh <label> <snapshot> <GATE_OPT> <tp2|tp4> [core source]
R=${QC_ROOT:-/srv/opentallas-scratch/claude/hbm-fmax-qcore}
lab=$1; src=$2; opt=$3; tp=$4; core=${5:-rtl/hdc/ot_hdc_core_vector_weight.sv}
cd $R/$src || exit 2
python3 tools/qwen_hbmacc_core_ctx_emit.py --core $core --out gen_$lab/ot_qwen_rom_core.sv || exit 3
if [ $tp = tp4 ]; then SP="--param SMIN=7 --param TCUT=7 --param BD=41 --param NWS=5 --param TWS=38 --param ORD=7 --param MEM_EXTRA=1"
else SP="--param SMIN=6 --param TCUT=6 --param BD=31 --param NWS=4 --param TWS=30 --param ORD=4 --param MEM_EXTRA=0"; fi
exec $R/jobs/route.sh core $lab $src --top ot_qwen_hbmacc_core_ctx --source gen_$lab/ot_qwen_rom_core.sv \
  --source rtl/hbm_accel/qwen/fmax/ot_qwen_hbmacc_core_ctx.sv --source rtl/hbm_accel/qwen/fmax/ot_qwen_core_ctx_stubs.sv \
  --source rtl/hbm_accel/qwen/fmax/ot_qwen_hbmacc_gate_f12.sv --source rtl/hdc/ot_hdc_cg.sv --source rtl/hdc/ot_hdc_dyn_ttiles.sv \
  --source rtl/hdc/ot_hdc_stream.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_reduce_q.sv --source rtl/hdc/ot_hdc_sfu_q.sv --source rtl/hdc/ot_hdc_sfu.sv \
  --source rtl/hdc/ot_hdc_fastfp_lat.sv --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv --source rtl/hdc/ot_hdc_fp32_mul_lat.sv \
  --false-path-from 'seg_*' --false-path-from 'w_a_gray*' --param GATE_OPT=$opt --param ME_ISSUE_RE=${MEIR:-1} --param DEC_FAST=${DECF:-1} $SP
