#!/bin/bash
set -euo pipefail
cd source
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_vq_metadata_lease --build-jobs 2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-PINMISSING --Mdir ../obj -f files.f >../build.log 2>&1
set +e
../obj/Vtb_vq_metadata_lease >../base.log 2>&1;b=$?
../obj/Vtb_vq_metadata_lease +MUT_METADATA >../overwrite.log 2>&1;m=$?
printf 'BASE_RC=%d\nOVERWRITE_RC=%d\n' "$b" "$m" >../status.txt
cat ../status.txt
grep VQ_METADATA_LEASE ../base.log ../overwrite.log
if [ "$b" -ne 0 ]||[ "$m" -eq 0 ];then exit 1;fi
