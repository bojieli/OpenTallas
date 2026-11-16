#!/bin/bash
set -eu
cd "$(dirname "$0")"
VL=${VL:-verilator}
export OMP_NUM_THREADS=1
/usr/bin/time -v -o build.time "$VL" --binary --timing --top-module tb -Wno-fatal -Wno-lint -Wno-style -O0 --output-groups 16 -CFLAGS '-O0 -w -fno-var-tracking' -j 1 --Mdir obj src/qfd_dv_s5_su8.sv src/qfd_dv_s5_su8_rst3.sv tb.sv >build.log 2>&1
/usr/bin/time -v -o run.time obj/Vtb >run.log 2>&1
