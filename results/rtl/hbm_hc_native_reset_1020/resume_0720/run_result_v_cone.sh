#!/bin/bash
set -euo pipefail
python3 extract_result_v_cone.py
mkdir -p source;tar xzf source.tgz -C source
cp tb_result_v_cone.sv native_result_v_cone.v source/
gzip -dc cells.v.gz > source/cells.v
cd source
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
H=rtl/hbm_accel/generic/peers/static_hc
"$VL" --binary --timing --x-initial unique --x-assign unique -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_result_v_cone \
 +define+OT_FP_DATA_NORST -Mdir ../obj -o Vrv tb_result_v_cone.sv native_result_v_cone.v cells.v \
 $H/ot_hbm_hc_tail_child_static.sv $H/ot_hgi_hc_tail_os_static.sv \
 rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv \
 rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/lib/ot_rst_relay.sv > ../build.log 2>&1
cd ..
./obj/Vrv +PULSE=0 +verilator+rand+reset+0 > heldlow.log
./obj/Vrv +PULSE=1 +verilator+rand+reset+0 > pulse.log
for seed in 17 1020 71;do ./obj/Vrv +PULSE=0 +verilator+rand+reset+2 +verilator+seed+$seed > heldlow_random_$seed.log;done
for f in heldlow.log pulse.log heldlow_random_*.log;do echo "$f";grep -E 'RV_CONE (PASS|FAIL)|RV_CONE_MISMATCH' "$f";done
