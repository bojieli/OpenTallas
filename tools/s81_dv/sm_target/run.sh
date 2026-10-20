#!/bin/bash
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$ROOT"
mkdir -p out
VL=${OPENTALLAS_TOOLS_ROOT:-$HOME/.local/opentallas-tools}/verilator-5.050/bin/verilator
"$VL" --version > out/tool.txt
# This is the real original SMS source set: two DUT heads and two independent
# slab-reference heads. All 512 SO dimensions/head and original FP operators.
S=rtl
"$VL" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
 --top-module tb_sm_so_target -Mdir out/obj -j 16 --unroll-count 4 -fno-dfg \
 -GMUT=0 -GTI=5 -GNJOB=12 -CFLAGS -O1 \
 "$S/dsrom_sys/s81_dv/sm_target/test/tb_sm_so_target.sv" \
 "$S/dsrom_sys/s81_dv/sm_target/dsdv_sm_so_target.sv" \
 results/rtl/s81_sm_target_1020/pinned/ot_sram_1r1w_32x64_m1.v \
 "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_sms.sv" \
 "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv" \
 "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_smh.sv" \
 "$S/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv" \
 "$S/hdc/ot_hdc_delay.sv" "$S/hdc/ot_hdc_fastfp_lat_f12.sv" \
 "$S/hdc/ot_hdc_fastfp.sv" "$S/hdc/ot_hdc_fp32_add_lat.sv" \
 "$S/hdc/ot_hdc_fp32_f12.sv" "$S/hdc/ot_hdc_fp32_mul_lat.sv" \
 "$S/hdc/ot_hdc_prefix.sv" "$S/hdc/ot_hdc_sfu.sv" \
 "$S/hdc/v41x/ot_dsrom_fp32_add_l6.sv" "$S/hdc/v41x/ot_dsrom_su_add6.sv" \
 "$S/hdc/v41x/ot_dsrom_su_f12.sv" "$S/hdc/v41x/ot_dsrom_su_fdiv_f12.sv" \
 "$S/hdc/v41x/ot_dsrom_su_softmax_add6.sv" "$S/hdc/v41x/ot_dsrom_su_softmax_add.sv" \
 "$S/hdc/v41x/ot_dsrom_su_softmax_f12r.sv" "$S/hdc/v41x/ot_dsrom_su_softmax_m9.sv" \
 "$S/hdc/v41x/ot_hdc_v41x_sfu.sv" > out/build.log 2>&1
for m in 0 1 2 3 4 5; do
 out/obj/Vtb_sm_so_target +TARGET_MUT=$m > "out/run_$m.log" 2>&1
 tail -4 "out/run_$m.log"
 grep -q '^SMS PASS' "out/run_$m.log"
 if [ "$m" != 0 ]; then grep -q "^TARGET CAUGHT mut=$m " "out/run_$m.log"; fi
done
