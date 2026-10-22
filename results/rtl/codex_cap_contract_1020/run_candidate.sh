#!/bin/bash
set -eu
cd /srv/opentallas-scratch/claude/codex-cap-contract-1020
BASE=/srv/opentallas-scratch/claude/toksim-s81d-wqbp/runs/l0_p126
EXE=/srv/opentallas-scratch/claude/toksim-s81-field/tools/Vtb_fullsix_trace
test ! -e candidate
mkdir candidate
cp -a "$BASE/images" "$BASE/expected_xq.mem" "$BASE/expected_reads.mem" candidate/
python3 add_fullsix_cap_program.py "$BASE/source_ctl.txt" l0_p126.json candidate/source_ctl.txt
sha256sum "$EXE" > candidate/exe.sha256
sha256sum candidate/source_ctl.txt > candidate/program.sha256
cd candidate
set +e
/usr/bin/time -v -o run_time.log "$EXE" +DIR=. +OT_ROM_DIR=images > diagnostic.log 2>&1
rc=$?
set -e
echo "$rc" > simulator.exit
grep -E 'ACTUAL_CAP_CFG|FULLSIX_SOURCE_CHECK|FULLSIX_PREPARATORY_TRACE_END|QNORM_SOURCE_COUNTS|RETAINED_CONTROL_MISMATCH|QNORM_SOURCE_AGE_MISMATCH' diagnostic.log
gzip -k diagnostic.log
echo "CAP_CANDIDATE_SIM_EXIT $rc (diagnostic only; strict qualification separate)"
