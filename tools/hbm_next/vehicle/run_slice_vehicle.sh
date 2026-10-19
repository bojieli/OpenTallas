#!/usr/bin/env bash
# LAYERBENCH-HBM (10-18): build + run a cut d4g slice (cut_slice.py + gen_slice_tb.py) under Verilator 5.050.
#   SRC=<bundle root (make_bundle.py: rtl/ physical/ files.f incdirs.f master_files.json views.json) + slice/>  OUT=<dir>
#   [NOHIER=hfd_vms_bank_native_q0_faces (masters built flat: the VM backdoor reaches the bank macros)] [JOBS=8] [CYCLES=] [REPLAY=slice/replay/<name>] [HBM_IMG_DIR=] [BUILD_ONLY=0] [REUSE=0: 1 = skip the build if OUT/obj exists]
# slice/ holds slice.v, tb_slice.sv, masters.txt (from the cutter) and replay/<name>/*.mem.  The HBM PHY blackbox master is
# replaced by the off-chip PHY+DRAM model rtl/hbm_next/vehicle/ot_hbm3e_phy_rc_e8p5_dram_model.sv; every other slice
# master is the die's real bound RTL (one flattened namespace per master, as the die vehicle).
# Writes OUT/build.log, OUT/run.log, OUT/times.json.
set -u
SRC=${SRC:?}; OUT=${OUT:?}; JOBS=${JOBS:-8}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"; cd "$SRC"
T0=$(date +%s); BRC=0
if [ "${REUSE:-0}" = 1 ] && [ -x "$OUT/obj/Vtb_hbm_slice" ]; then echo "REUSE build $OUT/obj"; else
  python3 flatten_masters.py --bundle . --views views.json --hier ${HIERMARK:-1} --nohier "${NOHIER-hfd_vms_bank_native_q0_faces}" --verilator "$VL" > "$OUT/flatten.log" 2>&1 || { cat "$OUT/flatten.log"; exit 3; }
  sed 's#^#masters/#; s#$#.sv#' slice/masters.txt | grep -v '^masters/ot_hbm3e_phy_rc_e8p5\.sv$' > slice/masters.f
  for f in $(cat slice/masters.f); do [ -f "$f" ] || { echo "MISSING $f"; exit 4; }; done
  # Verilate WITHOUT --build: the hier blocks are verilated serially (make -j1 hier_verilation) -- Verilator 5.050's
  # _hier.mk two-target rule runs a block twice under make -j (PCH race + double memory, HBM-TKM3 47debc90b) -- then
  # the C++ is built in parallel (hier_build -j JOBS).
  /usr/bin/time -v -o "$OUT/build.time" bash -c '"$0" --cc --exe --main --timing ${HIER:---hierarchical} -j "$1" -O1 \
    --unroll-count 16384 --unroll-stmts 4000000 --top-module tb_hbm_slice -Mdir "$2/obj" \
    -Wno-fatal -Wno-lint -Wno-style -Wno-MODDUP -Wno-PINMISSING -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
    -Wno-INITIALDLY -Wno-COMBDLY -Wno-BLKANDNBLK -Wno-SELRANGE -Wno-WIDTH -Wno-CASEINCOMPLETE \
    --x-initial unique --x-assign unique \
    -f slice/masters.f rtl/hbm_next/vehicle/ot_hbm3e_phy_rc_e8p5_dram_model.sv slice/slice.v slice/tb_slice.sv &&
    make -C "$2/obj" -f Vtb_hbm_slice_hier.mk -j1 hier_verilation &&
    make -C "$2/obj" -f Vtb_hbm_slice_hier.mk -j "$1" hier_build' "$VL" "$JOBS" "$OUT" > "$OUT/build.log" 2>&1
  BRC=$?
fi
T1=$(date +%s); RRC=-1
if [ $BRC -eq 0 ] && [ "${BUILD_ONLY:-0}" != 1 ]; then
  ARGS="+verilator+rand+reset+2"
  [ -n "${REPLAY:-}" ] && ARGS="$ARGS +REPLAY=$REPLAY"
  [ -n "${CYCLES:-}" ] && ARGS="$ARGS +CYCLES=$CYCLES"
  [ -n "${HBM_IMG_DIR:-}" ] && ARGS="$ARGS +HBM_IMG_DIR=$HBM_IMG_DIR"
  /usr/bin/time -v -o "$OUT/run.time" "$OUT/obj/Vtb_hbm_slice" $ARGS > "$OUT/run.log" 2>&1
  RRC=$?
fi
T2=$(date +%s)
rss() { awk -F': ' '/Maximum resident/{print $2}' "$1" 2>/dev/null || echo 0; }
printf '{"build_rc": %d, "run_rc": %d, "build_s": %d, "run_s": %d, "build_peak_rss_kb": %s, "run_peak_rss_kb": %s, "host": "%s", "jobs": %d, "replay": "%s"}\n' \
  $BRC $RRC $((T1-T0)) $((T2-T1)) "$(rss $OUT/build.time)" "$(rss $OUT/run.time)" "$(hostname)" $JOBS "${REPLAY:-}" > "$OUT/times.json"
cat "$OUT/times.json"; grep -E 'SLICE_(PASS|FAIL|SUMMARY)' "$OUT/run.log" 2>/dev/null | tail -3; grep -m5 '%Error' "$OUT/build.log"
exit $(( BRC != 0 ? 2 : (RRC > 0 ? 1 : 0) ))
