#!/usr/bin/env bash
# ELEM-CENSUS 2026-10-16 (S81-LINK kit helper): one configuration of the S81 KP4 RS(544,514) FEC gate
# (rtl/dsrom_sys/s81_link/run_kp4_gate.sh, tb_s81_kp4.sv vs the reference tools/s81_link/rs544.py) for the leaf kits
# ot_s81_kp4_enc / ot_s81_kp4_dec.  usage: run_kp4_leaf_bench.sh MODE OUTDIR    (cwd or script-relative source root)
#   base: EMUT 0 DMUT 0 -> TB_S81_KP4 ... EMUT=0 DMUT=0 PASS (16/16 parity exact, frames <= t exact, > t flagged)
#   emut: encoder MUT 1 (parity symbol inverted)  -> TB_S81_KP4 ... EMUT=1 DMUT=0 FAIL
#   dmut: decoder MUT 2 (Forney error value)      -> TB_S81_KP4 ... EMUT=0 DMUT=2 FAIL
set -u
mode=${1:?base|emut|dmut}; out=${2:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link
case $mode in base) g="";; emut) g="-GEMUT=1";; dmut) g="-GDMUT=2";; *) echo "KP4_LEAF BAD_MODE $mode"; exit 2;; esac
python3 "$R/tools/s81_link/rs544.py" selftest > "$out/ref_selftest.log" 2>&1 || { echo "KP4_LEAF REF_SELFTEST_FAIL"; exit 2; }
python3 "$R/tools/s81_link/rs544.py" vectors "$out/vec.hex" --n 16 --seed 5 > /dev/null
verilator --binary --timing -j ${KP4_J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+$L \
  --top-module tb_s81_kp4 $g --Mdir "$out/obj" -o tb "$L/ot_s81_kp4_enc.sv" "$L/ot_s81_kp4_dec.sv" "$L/tb_s81_kp4.sv" \
  > "$out/build.log" 2>&1 || { echo "KP4_LEAF BUILD_FAIL $mode"; tail -5 "$out/build.log"; exit 2; }
"$out/obj/tb" +vec="$out/vec.hex" +verilator+seed+11 > "$out/run.log" 2>&1
grep '^ERR' "$out/run.log" | head -3
grep '^TB_S81_KP4' "$out/run.log" | tail -1
grep -q '^TB_S81_KP4 .* PASS$' "$out/run.log"
