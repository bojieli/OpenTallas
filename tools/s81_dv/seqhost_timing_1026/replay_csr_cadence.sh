#!/bin/bash
# Run ONLY through ot-run in a fresh prepare.py seqhost source directory.
set -euo pipefail
mkdir run
$HOME/.local/opentallas-tools/bin/verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --top-module tb_seqhost_timing --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0' --Mdir run/obj -f defines.f -f files.f >run/build.log 2>&1
for quiet in 0 1 2 3 4 5 6 7; do
 run/obj/Vtb_seqhost_timing +host_quiet=$quiet >run/quiet$quiet.log 2>&1
 printf 'host period %s: ' "$((quiet+2))"
 grep '^SEQ_TIMING' run/quiet$quiet.log
 grep -q '^PASS' run/quiet$quiet.log
done
run/obj/Vtb_seqhost_timing +host_quiet=3 +mut_payload=1 >run/mut_payload_period5.log 2>&1
grep -q '^FAIL' run/mut_payload_period5.log
