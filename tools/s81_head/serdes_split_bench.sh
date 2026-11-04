#!/usr/bin/env bash
# DH58-RFRTL 2026-11-03: hd_serdes split lockstep bench (Verilator 5.050).  usage (repo root cwd):
#   serdes_split_bench.sh OUTDIR -> production (PASS expected) + SPLIT_MUT 1..3 (FAIL expected); exit 0 iff all as expected
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=${1:?outdir}; L=rtl/dsrom_sys/s81_link; T=rtl/dsrom_sys/s81_head; mkdir -p "$O"; rc=0
SRC="$T/ot_s81hd_serdes_link.sv $L/ot_pdie_serdes.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_dec.sv
 $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dsyn.sv
 physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
 $T/ot_s81hd_serdes_split.sv $T/test/tb_s81hd_serdes_split_lockstep.sv"
"$VL" --version | tee "$O/verilator_version.txt"
for m in ${MUTS:-0 1 2 3}; do
  E=$([ $m = 0 ] && echo PASS || echo FAIL)
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -I$L \
    --top-module tb_s81hd_serdes_split_lockstep -GSPLIT_MUT=$m -Mdir "$O/obj_m$m" $SRC --build-jobs ${J:-2} > "$O/build_m$m.log" 2>&1 \
    || { echo "m$m BUILD FAIL"; grep -m10 %Error "$O/build_m$m.log"; rc=1; continue; }
  "$O/obj_m$m/Vtb_s81hd_serdes_split_lockstep" > "$O/run_m$m.log" 2>&1
  r=$(grep -oE '^SERDES_SPLIT (PASS|FAIL)' "$O/run_m$m.log" | awk '{print $2}')
  v=$([ "$r" = "$E" ] && echo OK || echo BAD); [ $v = OK ] || rc=1
  echo "split_mut$m expect=$E got=${r:-NONE} $v | $(grep -E '^SERDES_SPLIT' "$O/run_m$m.log" | tr '\n' ' ' | cut -c1-260)"
done
echo "SERDES_SPLIT_BENCH rc=$rc"; exit $rc
