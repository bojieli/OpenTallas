#!/bin/bash
set -euo pipefail
ulimit -c 0
cd /var/tmp/smh-native-mapped-1015-v2
# Run only after STACK0 job terminal. Actual Verilator STACK1 specialization;
# keep completed object files and let content-aware generation/make reuse them.
python3 - <<'PY'
from pathlib import Path
import subprocess
s=Path('run.sh').read_text();command=next(l for l in s.splitlines() if l.startswith('verilator '))
command=command.replace('-GSTACK=0','-GSTACK=1').replace('> build.log','> build_stack1.log')
Path('stack1_command.txt').write_text(command+'\n')
r=subprocess.run(['bash','-c',command]);raise SystemExit(r.returncode)
PY
for sm in 08 09 10 11 12; do
 ./obj/native +DIR=inputs/sm${sm} +SM=$((10#$sm)) +TAGBASE=1000 +XFILE=inputs/activation/xw.hex +GFILE=inputs/activation/sm${sm}.gold.hex +CFILE=inputs/sm${sm}/command256.hex +RFILE=inputs/sm${sm}/read256.hex > sm${sm}.log 2>&1
done
printf '%s\n' 0 > exitcode_stack1
