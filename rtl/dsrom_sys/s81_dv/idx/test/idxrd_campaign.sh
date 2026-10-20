#!/usr/bin/env bash
# S81-IDXRD (10-19): build tb_dsdv_idx_rg once per build config, then run a set of plusarg cases in parallel.
# Run from the repo root on a fleet host (Verilator 5.050, the closure daemon's version).
#   idxrd_campaign.sh OUT BUILD "<-G build flags>" JOBS "name|+plusargs" ...
#   build flags: -GMUT=<0..5> -GSRAM_MACRO=<0|1> -GCKH_PS=<ps>;  plusargs: +N= +GATHER= +B= +PMAX= +KB= +T0= +P= +K= +SEED= +SLICE=
# Case names: pass_* must print TB_IDXRD PASS, fail_* must print TB_IDXRD FAIL, x_* are informational (sweeps).  Prints one line a case and
# IDXRD_CAMPAIGN PASS when every case met its expectation (exit 0), else IDXRD_CAMPAIGN FAIL (exit 1).
set -u
O=$1; BN=$2; G=$3; J=$4; shift 4
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$O/$BN; mkdir -p "$D"
SRC=(rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv
     physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
     rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv rtl/dsrom_sys/s81_ph/ot_s81ph_ctrl_pc.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg2.sv
     rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_v.sv
     rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg.sv rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_rg.sv)
if [ ! -x "$D/obj/Vtb_dsdv_idx_rg" ]; then
  "$VL" --version > "$D/build.log"
  sha256sum "${SRC[@]}" >> "$D/build.log"
  # shellcheck disable=SC2086
  "$VL" --binary --timing -j 16 --top-module tb_dsdv_idx_rg -O2 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
    -Wno-TIMESCALEMOD -Wno-BLKSEQ -Wno-INITIALDLY $G --Mdir "$D/obj" "${SRC[@]}" >> "$D/build.log" 2>&1 \
    || { "$VL" --binary --timing -j 16 --top-module tb_dsdv_idx_rg -O2 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
         -Wno-TIMESCALEMOD -Wno-BLKSEQ -Wno-INITIALDLY $G --Mdir "$D/obj" "${SRC[@]}" >> "$D/build.log" 2>&1; } \
    || { echo "$BN BUILD_FAILED"; grep -m5 -E '%Error' "$D/build.log"; echo "IDXRD_CAMPAIGN FAIL"; exit 2; }
fi
run_case() {
  local name=$1 args=$2 log=$D/$1.log
  # shellcheck disable=SC2086
  /usr/bin/time -v "$D/obj/Vtb_dsdv_idx_rg" $args > "$log" 2>&1
  local v; v=$(grep -h -E '^TB_IDXRD (PASS|FAIL)$' "$log" | tail -1)
  local ok=BAD
  case $name in pass_*) [ "$v" = "TB_IDXRD PASS" ] && ok=OK ;; fail_*) [ "$v" = "TB_IDXRD FAIL" ] && ok=OK ;; x_*) ok=OK ;; esac
  echo "IDXRD_CASE $ok $BN/$name: $v | $(grep -h TB_IDXRD_STATS "$log" | tail -1) | maxrss_kb=$(grep -h 'Maximum resident' "$log" | awk '{print $NF}') wall=$(grep -h 'Elapsed (wall' "$log" | awk '{print $NF}')"
}
n=0
for spec in "$@"; do
  run_case "${spec%%|*}" "${spec#*|}" > "$D/${spec%%|*}.res" &
  n=$((n + 1)); if [ $n -ge "$J" ]; then wait -n; n=$((n - 1)); fi
done
wait
bad=0
for spec in "$@"; do cat "$D/${spec%%|*}.res"; grep -q '^IDXRD_CASE OK' "$D/${spec%%|*}.res" || bad=1; done
[ $bad -eq 0 ] && { echo "IDXRD_CAMPAIGN PASS"; exit 0; }
echo "IDXRD_CAMPAIGN FAIL"; exit 1
