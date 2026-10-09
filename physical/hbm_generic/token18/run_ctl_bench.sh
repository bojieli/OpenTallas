#!/bin/bash
set -eu
out=$1
mut=${2:-0}
high=${3:-0}
mkdir -p "$out"
/usr/bin/time -v verilator --binary --timing -Wno-fatal --top-module tb_hgi_ctl18_lockstep -GHIGH="$high" -GMUT="$mut" -j 2 --Mdir "$out/obj" rtl/hdc/ot_hdc_accept.sv rtl/hdc/ot_hdc_prefix.sv rtl/gpu/dshbm/ot_dshbm_accept_port.sv physical/hbm_mtp/rtl/ot_dshbm_dspark_ctl_m.sv rtl/hbm_accel/generic/ot_hgi_mtp_ctl18.sv rtl/test/hbm_generic/tb_hgi_ctl18_lockstep.sv > "$out/build.log" 2>&1
/usr/bin/time -v "$out/obj/Vtb_hgi_ctl18_lockstep" > "$out/run.log" 2>&1
