#!/bin/bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
s=Path('fixture.v').read_text().replace('module fixture(', 'module gold(')
Path('gold.v').write_text(s)
PY
iverilog -g2012 -s tb -o good.vvp gold.v gate.v tb.v
vvp good.vvp > good.log
iverilog -g2012 -s tb -o mutant.vvp gold.v mutant.v tb.v
set +e
vvp mutant.vvp > mutant.log 2>&1
mutant_rc=$?
set -e
if [ "$mutant_rc" -eq 0 ]; then echo 'FAIL mutant not caught'; exit 1; fi
grep -q 'MISMATCH cycle=' mutant.log
cat good.log
printf 'PASS mutant: dropped child write enable caught, rc=%s\n' "$mutant_rc"
