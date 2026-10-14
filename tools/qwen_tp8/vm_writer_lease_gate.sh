#!/bin/bash
# Admitted only through ot-run; cwd is immutable frozen preparation.
set -euo pipefail
case_name=${1:-positive};mut=${2:-0};sw=${3:-8};top=${4:-tb_qfd_vm_writer_lease_composition}
mkdir -p "out/$case_name"
mapfile -t sources < sources.txt
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 4 --top-module "$top" -GF_MUT="$mut" -GSW="$sw" -GRED_ENTRIES=0 -GALIGN_ENTRIES=1 -GLT=1 -GLMIN=15 -GVL=7 -GRD=2 -GLOFF=1 -GSEED=11 --Mdir "out/$case_name/obj" "${sources[@]}" > "out/$case_name/build.log" 2>&1
set +e
"out/$case_name/obj/V${top}" > "out/$case_name/run.log" 2>&1
rc=$?
set -e
cat "out/$case_name/run.log"
if [ "$mut" = 0 ]; then
 test "$rc" = 0
 grep -q '^PASS qfd_su_vm_bv' "out/$case_name/run.log"
 ! grep -q '^FAIL' "out/$case_name/run.log"
else
 test "$rc" != 0
 grep -Eq 'actual command/writer/commit drain|accepted descriptor replaced|Assertion failed' "out/$case_name/run.log"
fi
