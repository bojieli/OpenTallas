#!/bin/bash
# usage: [RG_DEFS=-DOT_<X>_MUT] [RG_OBJ=dir] run_h15_ctrl.sh [NCYC]   (Q-TTH15 h15 controller lockstep bench, gen_h15_ctrl_tb.py)
set -e
N=${1:-200000}; P=physical/qwen_tt_static_cluster_1015; D=rtl/qwen_sys/static_schedule_20261014
O=${RG_OBJ:-/tmp/h15c_$$}; mkdir -p "$(dirname "$O")"
python3 $P/gen_h15_ctrl_tb.py > /dev/null
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Irtl/hdc -DNCYC=$N ${RG_DEFS:-} \
  --top-module tb_h15_ctrl -Mdir $O rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_cg.sv rtl/hdc/ot_hdc_delay.sv \
  rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv \
  $D/ot_qwen_rom_core_ctrl_static.sv $P/tb_h15_ctrl.sv > $O.build.log 2>&1 || { grep -m20 "%Error" $O.build.log; exit 2; }
$O/Vtb_h15_ctrl
