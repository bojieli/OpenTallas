#!/bin/bash
set -u
R=$(cd "$(dirname "$0")" && pwd)
for mode in old full; do
 EXTRA=(); if [ "$mode" = full ]; then EXTRA=(-l /out/yosys.full.log); fi
 docker run --rm --memory=2g --memory-swap=2g --cpus=1 -v "$R":/out openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -T -v 3 "${EXTRA[@]}" -c /out/read.tcl > "$R/$mode.log" 2>&1
 echo $? > "$R/$mode.exit"
done
python3 - "$R" <<'CHECK'
from pathlib import Path
import sys
r=Path(sys.argv[1]);assert (r/'old.exit').read_text().strip()=='1';assert (r/'full.exit').read_text().strip()=='1'
text=(r/'yosys.full.log').read_text();assert 'missing_child' in text and 'unknown module' in text.lower(),text
print('NATIVE_FULL_LOG_PASS both original exit1; missing module diagnostics present')
CHECK
