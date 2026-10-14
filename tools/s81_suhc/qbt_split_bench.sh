#!/bin/bash
# Lockstep bench of the split QB tap: qbt_split_bench.sh OUTDIR [MUT]   (MUT 0 exact, 1 / 2 negative controls)
# prints "QBT_SPLIT PASS" / "QBT_SPLIT FAIL" (rtl/dsrom_sys/s81_suhc/test/tb_s81_su_qbt_split.sv)
set -e
O=$1; M=${2:-0}; R=$(cd "$(dirname "$0")/../.." && pwd)
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$O"
verilator --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-MODMISSING --top-module tb_s81_su_qbt_split -GMUT=$M -Mdir "$O/obj_m$M" -j 4 \
    "$R/rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_qb.sv" "$R/rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sw.sv" "$R/rtl/hdc/ot_hdc_delay.sv" \
    "$R/rtl/dsrom_sys/s81_suhc/test/tb_s81_su_qbt_split.sv" > "$O/build_m$M.log" 2>&1 || { tail -30 "$O/build_m$M.log"; exit 2; }
"$O/obj_m$M/Vtb_s81_su_qbt_split"
