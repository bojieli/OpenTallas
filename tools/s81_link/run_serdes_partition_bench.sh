#!/usr/bin/env bash
# Cycle-exact digital/PHY source partition; MODE base passes, emut must fail.
set -u
mode=${1:?base|emut}; out=${2:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link; M=$R/physical/asap7_memory_macros
case $mode in base) g="";; emut) g="-GMUT=1";; *) exit 2;; esac
verilator --binary --timing -j ${KP4_J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTITOP +incdir+$L \
  --top-module tb_s81_serdes_partition $g --Mdir "$out/obj" -o tb "$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" "$L/ot_s81_kp4_bm.sv" \
  "$L/ot_s81_kp4_dsyn.sv" "$L/ot_s81_kp4_ddly.sv" "$L/ot_s81_kp4_dchn.sv" "$L/ot_s81_kp4_dout.sv" "$L/ot_s81_kp4_dec.sv" \
  "$L/ref/ot_pdie_serdes_before_split.sv" "$L/ot_pdie_serdes.sv" "$M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" \
  "$L/tb_s81_serdes_partition.sv" > "$out/build.log" 2>&1 || { echo "SERDES_PARTITION BUILD_FAIL $mode"; tail -5 "$out/build.log"; exit 2; }
"$out/obj/tb" +verilator+seed+${KP4_SEED:-11} > "$out/run.log" 2>&1
grep '^ERR' "$out/run.log" | head -3
grep '^TB_S81_SERDES_PARTITION' "$out/run.log" | tail -3
grep -q '^TB_S81_SERDES_PARTITION PASS$' "$out/run.log"
