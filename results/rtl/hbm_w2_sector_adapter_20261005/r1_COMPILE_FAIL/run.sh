#!/bin/bash
set -eu
cd /srv/opentallas-scratch/jobs/hubble-w2-sector-adapter-r1
export TMPDIR="$PWD/tmp" OPENBLAS_NUM_THREADS=1 PYTHONPATH="$PWD/src/tools"
mkdir -p "$TMPDIR"
python3 src/tools/dshbm_w2_sector_fixture.py --service service --weights weights --installed installed --out fixture > fixture.log 2>&1
iverilog -g2012 -s tb_hbm_integrated_w2_sector_adapter -o gate.vvp \
 src/ot_gpu_w6_secded_pkg.sv src/ot_hbm_integrated_prior_debt.sv src/ot_hbm_integrated_sm0_borrow.sv src/ot_hbm_integrated_w2_result_sink.sv \
 src/rtl/gpu_sys/ot_gpu_xbar.sv src/rtl/gpu_sys/ot_gpu_l2_slice.sv src/rtl/gpu_sys/ot_gpu_hbm_partition.sv src/rtl/gpu_sys/ot_gpu_memsys.sv src/rtl/hdc/kv/ot_hdc_hbm_model.sv \
 src/rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_sector_adapter.sv src/rtl/test/hbm_accel/tb_hbm_integrated_w2_sector_adapter.sv > compile.log 2>&1
read -r -a args < fixture/L20/args.txt
vvp gate.vvp +DIR=fixture/L20 "${args[@]}" > runtime.log 2>&1
