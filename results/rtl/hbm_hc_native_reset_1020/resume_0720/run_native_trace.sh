#!/bin/bash
set -euo pipefail
mkdir -p source;tar xzf source.tgz -C source
cp tb_native_trace.sv source/rtl/test/tb_hbm_hc_tail_child_eq.sv
cp native.v source/native.v;gzip -dc cells.v.gz > source/cells.v
cd source
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
H=rtl/hbm_accel/generic/peers/static_hc
"$VL" --binary --timing --x-initial unique --x-assign unique -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hbm_hc_tail_child_eq \
 +define+MUT=0 +define+NATIVE_DUT +define+OT_FP_DATA_NORST -Mdir ../obj -o Vtrace \
 rtl/test/tb_hbm_hc_tail_child_eq.sv native.v cells.v $H/ot_hbm_hc_tail_unit_static.sv $H/ot_hgi_hc_tail_static.sv \
 rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv \
 rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv \
 rtl/lib/ot_rst_relay.sv > ../build_native_trace.log 2>&1
cd ..
./obj/Vtrace +N=48 +SEED=1 +PULSE=0 +verilator+rand+reset+0 > original_heldlow.log
./obj/Vtrace +N=48 +SEED=1 +PULSE=1 +verilator+rand+reset+0 > explicit_pulse.log
for seed in 17 1020 71;do
 ./obj/Vtrace +N=48 +SEED=$seed +PULSE=0 +verilator+rand+reset+2 +verilator+seed+$seed > heldlow_random_$seed.log
done
for f in original_heldlow.log explicit_pulse.log heldlow_random_*.log;do echo "$f";grep -E 'TAILC (PASS|FAIL)|NATIVE_TRACE cyc=[012] ' "$f";done
