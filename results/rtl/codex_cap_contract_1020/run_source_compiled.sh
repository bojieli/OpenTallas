#!/bin/bash
set -eu
cd /srv/opentallas-scratch/claude/codex-cap-contract-1020
test ! -e source_compiled
mkdir source_compiled
cp -a candidate/images candidate/expected_xq.mem candidate/expected_reads.mem source_compiled/
cp source_compiled_ctl.txt source_compiled/source_ctl.txt
cp source_compiled_ctl.txt.cap.json source_compiled/source_ctl.txt.cap.json
BASE=/srv/opentallas-scratch/claude/toksim-s81d-wqbp
EXE=/srv/opentallas-scratch/claude/toksim-s81-field/tools/Vtb_fullsix_trace
sha256sum "$EXE" > source_compiled/exe.sha256
sha256sum source_compiled/source_ctl.txt > source_compiled/program.sha256
set +e
(cd source_compiled; /usr/bin/time -v -o run_time.log "$EXE" +DIR=. +OT_ROM_DIR=images > diagnostic.log 2>&1)
rc=$?
set -e
echo "$rc" > source_compiled/simulator.exit
gzip -k source_compiled/diagnostic.log
python3 check_fullsix_cap_capture.py "$BASE/root" "$BASE/root/sid6_fixture" source_compiled "$BASE/wqbp_golden_check.py" source_compiled/capture_check.json > source_compiled/capture_check.stdout
python3 check_fullsix_source_schedule.py source_compiled "$BASE/runs/l0_p126/model" source_compiled/source_schedule_check.json > source_compiled/source_schedule.stdout
python3 check_fullsix_static_capture.py "$BASE/root" "$BASE/runs/l0_p126/model" source_compiled source_compiled/static_capture_check.json > source_compiled/static_capture.stdout
echo "SOURCE_COMPILED_CAPTURE_DONE original_simulator_exit=$rc full_stage_qualified=false"
