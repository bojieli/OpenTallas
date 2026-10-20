#!/bin/bash
set -eu
cd /srv/opentallas-scratch/claude/codex-cap-contract-1020
LAYER=$1
test "$LAYER" = L2 -o "$LAYER" = L14
TAG=$(echo "$LAYER" | tr '[:upper:]' '[:lower:]')
BASE=/srv/opentallas-scratch/claude/toksim-s81d-wqbp
SRC=$BASE/runs/${TAG}_p126
OUT=capture_${TAG}
test ! -e "$OUT"
mkdir "$OUT"
cp -a "$SRC/images" "$SRC/expected_xq.mem" "$SRC/expected_reads.mem" "$OUT/"
python3 add_fullsix_cap_program.py "$SRC/source_ctl.txt" l0_p126.json "$OUT/source_ctl.txt"
EXE=/srv/opentallas-scratch/claude/toksim-s81-field/tools/Vtb_fullsix_trace
sha256sum "$EXE" > "$OUT/exe.sha256"
sha256sum "$OUT/source_ctl.txt" > "$OUT/program.sha256"
(cd "$OUT"; sha256sum images/*.viamap.hex > images.sha256)
set +e
(cd "$OUT"; /usr/bin/time -v -o run_time.log "$EXE" +DIR=. +OT_ROM_DIR=images > diagnostic.log 2>&1)
rc=$?
set -e
echo "$rc" > "$OUT/simulator.exit"
gzip -k "$OUT/diagnostic.log"
python3 check_fullsix_cap_capture.py "$BASE/root" "$BASE/fixtures/$LAYER" "$OUT" "$BASE/wqbp_golden_check.py" "$OUT/capture_check.json" > "$OUT/capture_check.stdout"
python3 check_fullsix_source_schedule.py "$OUT" "$SRC/model" "$OUT/source_schedule_check.json" > "$OUT/source_schedule.stdout"
grep -E 'FULLSIX_SOURCE_CHECK|FULLSIX_PREPARATORY_TRACE_END' "$OUT/diagnostic.log"
echo "LAYER_CAPTURE_COMPONENT_DONE layer=$LAYER original_simulator_exit=$rc full_stage_qualified=false"
