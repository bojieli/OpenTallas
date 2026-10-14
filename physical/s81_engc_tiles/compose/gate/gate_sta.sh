#!/bin/bash
# dsfd_engram_c CTS-stop gate STA (el1013-s81-engram): gate_sta.sh <snapshot dir with src/ and routes/> <label> ckpath|pairs
# prints the CKP (clock path per child, TT and FF) or PAIR (worst setup TT / hold FF per launch -> capture child) lines.
S=$1; B=$(ls -d $S/routes/$2/work/orfs/results/asap7/*/base); H=$(cd "$(dirname "$0")" && pwd)
for C in TT FF; do docker run --rm -e CORNER=$C -e DB=${DB:-4_cts.odb} -e SDC=${SDC:-4_cts.sdc} -v $B:/base -v $S/src:/src -v $H:/t openroad/orfs:asap7lock \
  bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /t/$3.tcl" 2>&1 | grep -E "^CKP|^PAIR|^RESET|Error|ERROR"; done
