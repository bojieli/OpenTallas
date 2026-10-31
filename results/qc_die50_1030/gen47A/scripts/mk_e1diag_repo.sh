#!/bin/bash
# DIE-QC-50/gen47A: DIAGNOSTIC repo copy for the E1-style run. tools/die_plan/die_clock_128.py copy records its
# no_clock_track rows to $OT_G47A_E1DIAG_OUT and RETURNS the wires (never a qualification; shared tool untouched).
set -euo pipefail
A=/srv/opentallas-scratch2/claude/die-qc-50/gen47A; W=/srv/opentallas-scratch2/claude/wt/die-qc-50-gen47A
R=$A/e1diag_repo; rm -rf $R; mkdir -p $R/tools; cp -r $W/tools/die_plan $W/tools/clk $R/tools/
python3 - $R/tools/die_plan/die_clock_128.py <<'PY'
import sys
p=sys.argv[1];s=open(p).read()
old="    if errs:\n        raise PlanError(errs)\n    if port_on_trunk:"
assert s.count(old)==1
s=s.replace(old,"    if errs:\n        import os as _o, json as _j\n        _j.dump(errs,open(_o.environ['OT_G47A_E1DIAG_OUT'],'w'))  # DIE-QC-50/gen47A E1DIAG copy\n    if port_on_trunk:")
open(p,'w').write(s);print('E1DIAG repo ready')
PY
