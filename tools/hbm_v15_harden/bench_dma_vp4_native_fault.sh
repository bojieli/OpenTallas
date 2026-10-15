#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
iverilog -g2012 -s tb_dma_vp4_native_fault -o "$out/a.vvp" "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$d/tb_dma_vp4_native_fault.sv"
vvp "$out/a.vvp"
