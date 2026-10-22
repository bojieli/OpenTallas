#!/usr/bin/env bash
# S81-RTLGAP/RG-IDX (10-21): build tb_idx72 (record reader bench around idx72_top = the G3 die-netlist cut of the L2
# index transport) once per variant, then run plusarg cases in parallel (case rules = idxrd3_campaign.sh: pass_* PASS,
# fail_* FAIL, closed_* FAIL with nopen 0, x_* informational).  Verilator 5.050 (closure daemon's), split C++ -O1 as the
# record campaign (16 controllers), +define+S81CTRL_NATIVE32 (the record campaign's controller define).
#   run_idx72.sh OUT VARIANT KITDIR TOPSV TB EXTRA_F JOBS "name|+plusargs" ...
#   KITDIR = dv_rtl_kit.py output of idx72_top (kit.f), TOPSV = the idx72_top.sv to build (verbatim cut or variant),
#   TB = tb_idx72.sv (mk_tb72.py), EXTRA_F = file list of the bench-only sources not in the kit (HBM model, ref engine, V decode)
set -u
O=$1; V=$2; K=$(realpath $3); TOP=$(realpath $4); TB=$(realpath $5); XF=$(realpath $6); J=$7; shift 7
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=$O/$V; mkdir -p "$D"
mapfile -t KF < <(grep -v '^+' "$K/kit.f" | grep -v 'src/top/' | sed "s#^#$K/#")
mapfile -t XS < "$XF"
SRC=("${KF[@]}" "${XS[@]}" "$TOP" "$TB")
if [ ! -x "$D/obj/Vtb_idx72" ]; then
  "$VL" --version > "$D/build.log"; sha256sum "${SRC[@]}" > "$D/sources.sha256"; cat "$D/sources.sha256" >> "$D/build.log"
  /usr/bin/time -v -o "$D/build.time" "$VL" --binary --timing -j ${VL_J:-32} --top-module tb_idx72 -O2 +define+S81CTRL_NATIVE32 \
    --output-split 20000 --output-split-cfuncs 2000 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O1" -Wno-fatal -Wno-lint -Wno-style \
    -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -Wno-TIMESCALEMOD -Wno-BLKSEQ -Wno-INITIALDLY \
    --unroll-count 4 -fno-dfg --Mdir "$D/obj" "${SRC[@]}" >> "$D/build.log" 2>&1 \
    || { echo "$V BUILD_FAILED"; grep -m8 -E '%Error' "$D/build.log"; echo "IDXRD_CAMPAIGN FAIL"; exit 2; }
fi
run_case() {
  local name=$1 args=$2 log=$D/$1.log
  # shellcheck disable=SC2086
  /usr/bin/time -v "$D/obj/Vtb_idx72" $args > "$log" 2>&1
  local v; v=$(grep -h -E '^TB_IDXRD (PASS|FAIL)$' "$log" | tail -1)
  local ok=BAD
  case $name in pass_*) [ "$v" = "TB_IDXRD PASS" ] && ok=OK ;; fail_*) [ "$v" = "TB_IDXRD FAIL" ] && ok=OK ;;
    closed_*) [ "$v" = "TB_IDXRD FAIL" ] && grep -q -E 'TB_IDXRD_STATS .* nopen 0 ' "$log" && ok=OK ;; x_*) ok=OK ;; esac
  echo "IDXRD_CASE $ok $V/$name: $v | $(grep -h TB_IDXRD_STATS "$log" | tail -1) | maxrss_kb=$(grep -h 'Maximum resident' "$log" | awk '{print $NF}') wall=$(grep -h 'Elapsed (wall' "$log" | awk '{print $NF}')"
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
