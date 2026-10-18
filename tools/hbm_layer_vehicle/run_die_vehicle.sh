#!/usr/bin/env bash
# TOKEN-PASS-HBMDS (10-18): build + run the d4g die vehicle (stage 0) under Verilator 5.050 in a source bundle.
#   SRC=<bundle root: rtl/ physical/ + die.v + files.f/incdirs.f>  OUT=<dir>  [JOBS=32] [CYCLES=4000] [STAGE=0]
# Writes OUT/build.log, OUT/run.log, OUT/times.json (build/run wall seconds, peak RSS KB from /usr/bin/time).
set -u
SRC=${SRC:?}; OUT=${OUT:?}; JOBS=${JOBS:-32}; CYCLES=${CYCLES:-4000}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"; cd "$SRC"
T0=$(date +%s)
python3 flatten_masters.py --bundle . --views views.json --hier ${HIERMARK:-1} --verilator "$VL" > "$OUT/flatten.log" 2>&1 || { cat "$OUT/flatten.log"; exit 3; }
/usr/bin/time -v -o "$OUT/build.time" "$VL" --binary --timing ${HIER:---hierarchical} -j "$JOBS" --build-jobs "$JOBS" -O1 --unroll-count 16384 --unroll-stmts 4000000 \
  --top-module tb_hbm_d4g_die_vehicle -Mdir "$OUT/obj" \
  -Wno-fatal -Wno-lint -Wno-style -Wno-MODDUP -Wno-PINMISSING -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
  -Wno-INITIALDLY -Wno-COMBDLY -Wno-BLKANDNBLK -Wno-SELRANGE -Wno-WIDTH -Wno-CASEINCOMPLETE \
  --x-initial unique --x-assign unique \
  -f masters.f die.v rtl/test/hbm_layer/tb_hbm_d4g_die_vehicle.sv > "$OUT/build.log" 2>&1
BRC=$?
T1=$(date +%s)
RRC=-1
if [ $BRC -eq 0 ]; then
  /usr/bin/time -v -o "$OUT/run.time" "$OUT/obj/Vtb_hbm_d4g_die_vehicle" +CYCLES=$CYCLES +verilator+rand+reset+2 > "$OUT/run.log" 2>&1
  RRC=$?
fi
T2=$(date +%s)
rss() { awk -F': ' '/Maximum resident/{print $2}' "$1" 2>/dev/null || echo 0; }
printf '{"build_rc": %d, "run_rc": %d, "build_s": %d, "run_s": %d, "build_peak_rss_kb": %s, "run_peak_rss_kb": %s, "host": "%s", "jobs": %d}\n' \
  $BRC $RRC $((T1-T0)) $((T2-T1)) "$(rss $OUT/build.time)" "$(rss $OUT/run.time 2>/dev/null || echo 0)" "$(hostname)" $JOBS > "$OUT/times.json"
cat "$OUT/times.json"; tail -3 "$OUT/run.log" 2>/dev/null; grep -m5 '%Error' "$OUT/build.log"
exit $(( BRC != 0 ? 2 : (RRC != 0 ? 1 : 0) ))
