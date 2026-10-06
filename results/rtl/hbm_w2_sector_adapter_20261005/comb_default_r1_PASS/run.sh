#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/jobs/hubble-w2-sector-comb-default-r1
export TMPDIR="$PWD/tmp"
mkdir -p "$TMPDIR" fixture_subset
cp fixture/L20/{memory_addresses.hex,memory.hex,w2_p0.hex,w2_p1.hex} fixture_subset/
head -n 2 fixture/L20/maps.hex > fixture_subset/maps.hex
head -n 2 fixture/L20/expected.hex > fixture_subset/expected.hex
verilator --version > toolchain.log
iverilog -V >> toolchain.log 2>&1
set +e
verilator --lint-only -Werror-LATCH --top-module ot_hbm_integrated_w2_sector_adapter -GENABLE=1 old_adapter.sv > old_lint.log 2>&1
old_rc=$?
set -e
printf '%s\n' "$old_rc" > old_lint.exit
if [ "$old_rc" = 0 ] || ! grep -q LATCH old_lint.log; then echo 'MISSING_OLD_LATCH_NEGATIVE';exit 1;fi
verilator --lint-only -Werror-LATCH --top-module ot_hbm_integrated_w2_sector_adapter -GENABLE=1 src/rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_sector_adapter.sv > new_lint.log 2>&1
iverilog -g2012 -s tb_hbm_integrated_w2_sector_adapter -o gate.vvp \
 src/ot_gpu_w6_secded_pkg.sv src/ot_hbm_integrated_prior_debt.sv src/ot_hbm_integrated_sm0_borrow.sv src/ot_hbm_integrated_w2_result_sink.sv \
 src/rtl/gpu_sys/ot_gpu_xbar.sv src/rtl/gpu_sys/ot_gpu_l2_slice.sv src/rtl/gpu_sys/ot_gpu_hbm_partition.sv src/rtl/gpu_sys/ot_gpu_memsys.sv src/rtl/hdc/kv/ot_hdc_hbm_model.sv \
 src/rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_sector_adapter.sv src/rtl/test/hbm_accel/tb_hbm_integrated_w2_sector_adapter.sv > compile.log 2>&1
read -r -a args < fixture/L20/args.txt
args[1]=+NCASES=2
vvp -v gate.vvp +DIR=fixture_subset "${args[@]}" +CHECK_COMB_DEFAULT > runtime.log 2>&1
