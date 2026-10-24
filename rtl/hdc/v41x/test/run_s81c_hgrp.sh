#!/bin/bash
# CORE-S81-SVC reduced bench (one head group): run_s81c_hgrp.sh OUTDIR GID [DEFINE...]  (repo root = cwd). Builds + runs seeds 1..3.
set -euo pipefail
O=$1; GID=$2; shift 2; mkdir -p "$O"
R=rtl/hdc
F="$R/v41x/test/tb_s81c_hgrp.sv $R/v41x/ot_s81c_attn_hcore.sv $R/v41x/ot_hdc_v41x_attn_tile_s.sv $R/v41x/ot_hdc_v41x_kreg.sv
   $R/v41x/ot_hdc_v41x_attn_tile.sv $R/v41x/ot_hdc_v41x_attn_tile_lat.sv $R/ot_hdc_fp32_f12.sv $R/ot_hdc_fp32_add_lat.sv
   $R/ot_hdc_prefix.sv $R/ot_hdc_fastfp.sv $R/v41x/ot_dsrom_su_add6.sv"
D=""; for d in "$@"; do D="$D -D$d"; done
verilator --cc --exe --build -j 16 -O2 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-TIMESCALEMOD \
  --top-module tb_s81c_hgrp -GGID=$GID $D -Mdir "$O/obj" $F $R/v41x/test/tb_s81c_hgrp.cpp > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 2; }
for s in 1 2 3; do "$O/obj/Vtb_s81c_hgrp" +seed=$s +cycles=${CYCLES:-20000} | tail -6; done
