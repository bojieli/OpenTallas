#!/bin/bash
set -u
cd "$(dirname "$0")"
mkdir -p run
printf '%s\n' 045cc74114fcdbaa1576f27fa6fe3537a7890ee4 > run/source_commit.txt
sha256sum rtl/hbm_accel/direct_links/*.sv rtl/hdc/*.sv results/rtl/hbm_accel_ha2_20261003/fixtures_r1/*.hex > run/input_sha256.txt
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_accel_direct_links --Mdir run/obj_gather rtl/hbm_accel/direct_links/ot_hbm_accel_gather_die.sv rtl/hbm_accel/direct_links/ot_hbm_accel_link_stage_model.sv rtl/hbm_accel/direct_links/tb_hbm_accel_direct_links.sv > run/gather_build.log 2>&1
build_rc=$?
printf '%s\n' "$build_rc" > run/gather_build.exit
if [ "$build_rc" = 0 ]; then
 /usr/bin/time -v run/obj_gather/Vtb_hbm_accel_direct_links > run/gather.log 2>run/gather.resources
 printf '%s\n' "$?" > run/gather.exit
fi
iverilog -g2012 -s tb_hbm_accel_snapshot_reduce -o run/reduce.vvp rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/direct_links/ot_hbm_accel_snapshot_reduce.sv rtl/hbm_accel/direct_links/tb_hbm_accel_snapshot_reduce.sv > run/reduce_build.log 2>&1
build_rc=$?
printf '%s\n' "$build_rc" > run/reduce_build.exit
if [ "$build_rc" = 0 ]; then
 /usr/bin/time -v vvp run/reduce.vvp +DIR=results/rtl/hbm_accel_ha2_20261003/fixtures_r1 > run/reduce.log 2>run/reduce.resources
 printf '%s\n' "$?" > run/reduce.exit
fi
sha256sum -c run/input_sha256.txt > run/pins_after.log
printf '%s\n' "$?" > run/pins_after.exit
printf '%s\n' terminal > run/supervisor.exit
