#!/bin/bash
# S81-IDX3R: build + run tb_dsfd_ctrl_rg3_mux (dsfd_ctrl_rg3 slot mux / tag demux vs the record dsfd_ctrl_rg2).
# Run from the repo root (fleet, Verilator 5.050).  run_ctrl3.sh OUT NAME MUT "case|+plusargs" ...
#   case names: pass_* must print TB_CTRL3 PASS, fail_* TB_CTRL3 FAIL.  Prints CTRL3_CAMPAIGN PASS / FAIL.
set -u
O=$1; BN=$2; M=$3; shift 3
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$O/$BN; mkdir -p "$D"
SRC=(rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv
     rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv
     rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg2.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg3.sv
     rtl/dsrom_sys/s81_ph/ctrl/test/tb_dsfd_ctrl_rg3_mux.sv)
# DRIVE-S81-IDX4-KITS 10-20: S81CTRL_FIFO_IMPL=sram_p192 builds the s81ctrl_rg3 kit configuration (n32s defines
# S81CTRL_SRAM_FIFO + S81CTRL_SRAM_P192 + S81CTRL_NATIVE32, behavioural 16x340 dual-clock SRAM model).
if [ "${S81CTRL_FIFO_IMPL:-flop}" = sram_p192 ]; then
  SRC+=(rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv physical/asap7_memory_macros/ot_sram_1r1w2c_16x340_p192/ot_sram_1r1w2c_16x340_p192.v)
  VL_DEF="${VL_DEF:-} +define+S81CTRL_SRAM_FIFO +define+S81CTRL_SRAM_P192 +define+S81CTRL_NATIVE32"
fi
"$VL" --version > "$D/build.log"; sha256sum "${SRC[@]}" >> "$D/build.log"
"$VL" --binary --timing -j 8 --top-module tb_dsfd_ctrl_rg3_mux -O2 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
  -Wno-TIMESCALEMOD -Wno-BLKSEQ -Wno-INITIALDLY ${VL_DEF:-} -GMUT=$M --Mdir "$D/obj" "${SRC[@]}" >> "$D/build.log" 2>&1 \
  || { echo "$BN BUILD_FAILED"; grep -m8 -E '%Error' "$D/build.log"; echo "CTRL3_CAMPAIGN FAIL"; exit 2; }
bad=0
for spec in "$@"; do
  n=${spec%%|*}; a=${spec#*|}
  # shellcheck disable=SC2086
  "$D/obj/Vtb_dsfd_ctrl_rg3_mux" $a > "$D/$n.log" 2>&1
  v=$(grep -h -E '^TB_CTRL3 (PASS|FAIL)$' "$D/$n.log" | tail -1); ok=BAD
  case $n in pass_*) [ "$v" = "TB_CTRL3 PASS" ] && ok=OK ;; fail_*) [ "$v" = "TB_CTRL3 FAIL" ] && ok=OK ;; esac
  echo "CTRL3_CASE $ok $BN/$n: $v | $(grep -h TB_CTRL3_STATS "$D/$n.log" | tail -1)"
  [ $ok = OK ] || bad=1
done
[ $bad -eq 0 ] && { echo "CTRL3_CAMPAIGN PASS"; exit 0; }
echo "CTRL3_CAMPAIGN FAIL"; exit 1
