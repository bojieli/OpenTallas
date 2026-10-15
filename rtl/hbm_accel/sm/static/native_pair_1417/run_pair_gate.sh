#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
ROOT=${PAIR_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
OUT=$(realpath -m "${1:?output directory}")
mode=${2:-normal}
mkdir -p "$OUT"
cd "$ROOT"
python3 tools/hbm_coll_static/native_programme_pair.py --out "$OUT/images" > "$OUT/compiler.log"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/sm/static/native_pair_1417
args=()
case "$mode" in
 normal);;
 pc)args+=(-GNSM=1 -GMUT_PC=1);;
 data)args+=(-GNSM=1 -GMUT_DATA=1);;
 seal)args+=(-GNSM=1 -GMUT_SEAL=1);;
 *)echo "bad mode $mode";exit 2;;
esac
"$V" --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_smh_calendar_pair_static --Mdir "$OUT/obj" "${args[@]}" \
 "$P/ot_smh_calendar_pair_static.sv" "$P/tb_smh_calendar_pair_static.sv" \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build.log" 2>&1 || { tail -35 "$OUT/build.log";exit 2; }
exe="$OUT/obj/Vtb_smh_calendar_pair_static"
if [[ "$mode" != normal ]];then
 scenario=0
 [[ "$mode" != seal ]] || scenario=1
 if "$exe" +IMAGES="$OUT/images" +case="$scenario" > "$OUT/run.log" 2>&1;then
  echo "NATIVE_PAIR MUTANT SURVIVED $mode";exit 1
 fi
 grep -q 'NATIVE_PAIR_FAIL' "$OUT/run.log"
 echo "NATIVE_PAIR MUTANT REJECTED $mode"
 exit 0
fi
"$exe" +IMAGES="$OUT/images" > "$OUT/run.log" 2>&1 || { cat "$OUT/run.log";exit 1; }
grep -q '^NATIVE_PAIR PASS SMs=32 actualSRAMs=64 ' "$OUT/run.log"
cat "$OUT/run.log"
for scenario in {1..12};do
 "$exe" +IMAGES="$OUT/images" +case="$scenario" > "$OUT/case-$scenario.log" 2>&1 || { cat "$OUT/case-$scenario.log";exit 1; }
 grep -q '^NATIVE_PAIR_NEGATIVE PASS ' "$OUT/case-$scenario.log"
 cat "$OUT/case-$scenario.log"
done
