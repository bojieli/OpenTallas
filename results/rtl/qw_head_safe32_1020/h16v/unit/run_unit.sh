#!/bin/bash
# repo root; QW-H16V unit exactness (iverilog -g2012)
set -u; O=${1:-/tmp/h16v_unit}; mkdir -p $O; S=rtl/qwen_sys/static_schedule_20261014
iverilog -g2012 -o $O/u.vvp results/rtl/qw_head_safe32_1020/h16v/unit/tb_h16v_unit.sv rtl/hdc/ot_hdc_dyn_ttiles.sv $S/safe32/ot_hdc_dyn_ttiles_tab.sv $S/safe32/ot_hdc_ks_helpers.sv $S/ot_qwen_tp8_rom_relocate.sv $S/safe32/ot_qwen_tp8_rom_relocate_pb.sv > $O/build.log 2>&1 || { echo BUILD_FAIL; cat $O/build.log; exit 1; }
vvp -n $O/u.vvp | tee $O/unit.log | tail -12
