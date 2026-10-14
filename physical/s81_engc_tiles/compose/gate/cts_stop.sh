#!/bin/bash
# dsfd_engram_c CTS-stop gate run (el1013-s81-engram): runs the job spec's OWN route command with --pnr-stop-after cts.
#   cts_stop.sh <spec.json> <snapshot dir (holds src/ = git archive of the spec's commit + SOURCE_COMMIT)> <label>
set -uo pipefail
spec=$1; S=$2; lab=$3
cmd=$(python3 - "$spec" "$S" "$lab" <<'P'
import json, sys
c = json.load(open(sys.argv[1]))["stages"]["route"]["cmd"]
print(c.replace("{SRC}", sys.argv[2] + "/src").replace("{RUN}", sys.argv[2]).replace("{LABEL}", sys.argv[3]))
P
)
cd $S/src && CL_LABEL_SUFFIX= CL_STOP_AFTER='--pnr-stop-after cts' bash -c "$cmd"
rc=$?; echo "CTS_STOP rc=$rc"; cat $S/routes/$lab/exit; exit $rc
