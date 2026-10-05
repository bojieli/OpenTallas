#!/bin/bash
# Lockstep exactness + latency bench of the SU successor against the pinned unit (Verilator 5.050).
# Usage: [R=<src snapshot>] [PLUS=+dump] lockstep.sh <build dir> <LA> <LM> <SW> <LV> [seeds...]
# SW 64 builds the lanes as Verilator hierarchical blocks (hier.vlt), as the HA8 vehicle does.
set -e
R=${R:-/home/ubuntu/hbm-fmax-qcore-20261004}
d=$1; LA=$2; LM=$3; SW=$4; LV=$5; shift 5
mkdir -p $d
python3 -c "import sys; sys.path.insert(0,'$R/tools'); import qwen_rom_rt_core_emit_w12 as E; open('$d/ref_vstream_rt.sv','w').write(E.emit_vstream(open(E.VSTREAM).read()))"
printf '`verilator_config\nhier_block -module "ot_hdc_vstream_lane"\nhier_block -module "ot_hdc_vstream_lane_f12"\n' > $d/hier.vlt
HIER=""; [ "$SW" -ge 32 ] && HIER="--hierarchical $d/hier.vlt"
${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator} --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH \
  --top-module tb_vstream_f12_lockstep $HIER -GLA=$LA -GLM=$LM -GNOPS=300 -GSW=$SW -GLV=$LV --Mdir $d/obj -j 16 --build-jobs 32 \
  -I$R/rtl/hdc $R/rtl/test/hbm_accel_qwen/fmax/tb_vstream_f12_lockstep.sv $d/ref_vstream_rt.sv \
  $R/rtl/hdc/ot_hdc_vstream_lane.sv $R/rtl/hdc/ot_hdc_vreduce.sv $R/rtl/hdc/ot_hdc_sfu_q.sv $R/rtl/hdc/ot_hdc_sfu.sv \
  $R/rtl/hdc/ot_hdc_fastfp.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv \
  $R/rtl/hdc/ot_hdc_prefix.sv $R/rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_f12.sv $R/rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_rt_f12.sv > $d/build.log 2>&1
cd $d; for s in "$@"; do ./obj/Vtb_vstream_f12_lockstep +seed=$s $PLUS | grep -E "^(LAT|RESULT|MISMATCH|FAIL)"; done
