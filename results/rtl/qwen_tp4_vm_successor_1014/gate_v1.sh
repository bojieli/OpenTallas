#!/bin/bash
# Run only through ot-run; cwd is frozen preparation from vm_tp4_successor_prepare.py.
set -euo pipefail
case_name=${1:-positive};mut=${2:-0};seed=${3:-1}
mkdir -p "out/$case_name"
mapfile -t sources < sources.txt
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 4 --top-module tb_qfd_vm_tp4_successor -GCYCLES=6000 -GDEPTH=174 -GLAW=8 -GDEPTHS=695 -GLAWS=10 -GNPP=7 -GLEAF_MUT="$mut" -GSEED="$seed" --Mdir "out/$case_name/obj" "${sources[@]}" > "out/$case_name/build.log" 2>&1
set +e
"out/$case_name/obj/Vtb_qfd_vm_tp4_successor" > "out/$case_name/run.log" 2>&1
rc=$?
set -e
cat "out/$case_name/run.log"
if [ "$mut" = 0 ]; then
 test "$rc" = 0
 grep -q '^PASS' "out/$case_name/run.log"
 ! grep -q '^FAIL' "out/$case_name/run.log"
else
 grep -q '^FAIL' "out/$case_name/run.log"
fi
