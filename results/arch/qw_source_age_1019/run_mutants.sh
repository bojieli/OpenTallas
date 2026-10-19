#!/bin/bash
set -euo pipefail
ulimit -c 0
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd qw_source_age_1019
for kind in K PHASE FIELD; do
 verilator --binary --timing -j 2 -Wno-fatal +define+MUT_$kind --top-module lane_age_tb --Mdir obj_$kind lane_age_tb.sv source/059_qfd_fwd_lane.sv source/005_ot_hdc_cg.sv >build_$kind.log 2>&1
 set +e
 ./obj_$kind/Vlane_age_tb >mutant_$kind.log 2>&1
 status=$?
 set -e
 if [ "$status" = 0 ]; then exit 1; fi
 grep -q SOURCE_AGE_FAIL mutant_$kind.log
 printf 'CAUSAL_MUTANT_%s_FAIL exit=%s
' "$kind" "$status"
done
