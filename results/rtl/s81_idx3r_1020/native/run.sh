#!/bin/bash
# usage: run.sh rg3|ctrl3|ctrl3s|ctrl2 OUTDIR  (run from a source tree root copy: rtl/ physical/ tools/textbook_lint.py)
set -euo pipefail
W=$1; O=$2; rm -rf "$O"; mkdir -p "$O"
T=$(mktemp -d ${NAT_TMP:-/srv/opentallas-scratch/claude/s81-idx3r-1020}/nat_XXXX); cp -a rtl physical tools results "$T"/
cd "$T"
TOP=$( [ "$W" = rg3 ] && echo idxrg3_native_top || ( [ "${W%s}" = ctrl3 ] && echo dsfd_ctrl_rg3_native_top || echo dsfd_ctrl_rg2_native_top ) )
docker run --rm --memory=64g --memory-swap=64g -v "$PWD:/work" -w /work openroad/orfs:latest bash -lc "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 results/rtl/s81_idx3r_1020/native/prepare.py $W; yosys -l yosys.log -c synth.tcl; python3 tools/textbook_lint.py check --netlist mapped.v --top $TOP --out textbook.json --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 reach_um=405" > "$O/native.log" 2>&1 || echo NATIVE_RC=$?
cp textbook.json yosys.log mapped_attr.v "$O"/ 2>/dev/null || true
grep -A40 "Printing statistics" yosys.log | grep -E "cells|DFF|ot_sram|ot_hdc" | head -12 > "$O/stat.txt" || true
python3 - "$O/textbook.json" <<'PY'
import json, sys
t = json.load(open(sys.argv[1])); r = t.get('refuse', {})
print('NATIVE_REFUSE', {k: len(v) for k, v in r.items()})
for k, v in r.items():
    for x in v[:12]: print('  ', str(x)[:220])
w = t.get('warn')
print('NATIVE_WARN', {k: len(v) for k, v in w.items()} if isinstance(w, dict) else w)
for k in ('hf', 'high_fanout', 'summary', 'stats'):
    if k in t: print(k, str(t[k])[:600])
PY
cd /; rm -rf "$T"
echo NATIVE_DONE
