#!/bin/bash
# run_rrfifo.sh REPO OUT : unit bench of the g1 RPIPE record path (ot_wbq_root_s7_rr_fifo) vs the cdc fifo, 5 clock ratios, + MUT=1 negative control
R=$(realpath "$1"); O=$(realpath -m "$2"); H=$(dirname "$(realpath "$0")"); mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for m in 0 1; do nice -n 10 $V --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_rrfifo -GMUT=$m -Mdir $O/obj$m -o sim \
  $H/tb_rrfifo.sv $H/src_g1_rr/ot_wbq_root_s7_rr_fifo.sv $R/rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv > $O/b$m.log 2>&1 || { grep -m5 %Error $O/b$m.log; exit 2; }; done
for r in "1000 1000 137" "1000 3000 137" "3000 1000 137" "1000 1370 300" "833 1024 200"; do set -- $r
  for m in 0 1; do echo "ratio $1:$2 $($O/obj$m/sim +TF=$1 +TH=$2 +PH=$3 +verilator+seed+$1$2 2>&1 | grep -E 'RRFIFO (MUT|PASS|FAIL)' | tr '\n' ' ')"; done; done
