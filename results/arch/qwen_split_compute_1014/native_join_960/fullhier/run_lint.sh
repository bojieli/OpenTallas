#!/bin/bash
set -uo pipefail
python3 - <<'CHECK'
import json,hashlib,pathlib
for p,r in json.load(open('source.json'))['sources'].items():
 assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==r['sha256'],p
CHECK
check=$?; if [ "$check" != 0 ]; then exit "$check"; fi
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
/usr/bin/time -v $VL --lint-only --timing -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -DOT_QFDS_LU=53 -DOT_QFDS_LS=376 -Wno-fatal -Wno-TIMESCALEMOD -Irtl/hdc --top-module qfd_native_compute_join_960 -f native_join.f > lint.log 2>&1
rc=$?; echo "$rc" > command_exit.txt; exit "$rc"
