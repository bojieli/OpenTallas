#!/usr/bin/env bash
# run_kp4_dsyn_ampipe_bench.sh MODE OUTDIR [DEFS]: MODE base (PASS) | mut (MUT_B 1, FAIL)
set -u
mode=${1:?base|mut}; out=${2:?outdir}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link
case $mode in base) g="";; mut) g="-GMUT_B=1";; *) echo "AMPIPE BAD_MODE"; exit 2;; esac
verilator --binary --timing -j ${KP4_J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTITOP +incdir+$L \
  --top-module tb_s81_kp4_dsyn_ampipe ${KP4_DEFS:-} $g --Mdir "$out/obj" -o tb "$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" \
  "$L/ot_s81_kp4_bm.sv" "$L/ot_s81_kp4_dsyn.sv" "$L/tb_s81_kp4_dsyn_ampipe.sv" > "$out/build.log" 2>&1 || { echo "AMPIPE BUILD_FAIL"; tail -5 "$out/build.log"; exit 2; }
"$out/obj/tb" +verilator+seed+${KP4_SEED:-11} > "$out/run.log" 2>&1
grep '^ERR' "$out/run.log" | head -3
grep '^TB_S81_KP4_DSYN_AMPIPE' "$out/run.log" | tail -2
grep -q '^TB_S81_KP4_DSYN_AMPIPE PASS$' "$out/run.log"
