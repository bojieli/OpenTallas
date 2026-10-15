#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../.."
build_dir=$(mktemp -d /tmp/hbm-p-ports.XXXXXX)
trap 'rm -rf "$build_dir"' EXIT
iverilog -g2012 -s tb_hbm_p_reduce_ports_static -o "$build_dir/sim" \
 rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv \
 rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_p_reduce_ingress_static.sv \
 rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_p_scalar_publish_static.sv \
 rtl/test/hbm_accel/generic/tb_hbm_p_reduce_ports_static.sv
vvp "$build_dir/sim"
if vvp "$build_dir/sim" +MUTANT_TAG >"$build_dir/mutant.log" 2>&1; then
 cat "$build_dir/mutant.log"
 exit 1
fi
cat "$build_dir/mutant.log"
echo 'PASS tag identity mutant rejected'
