#!/bin/bash
set -euo pipefail
K=$1
cd "$K"
python3 - <<'PY'
from pathlib import Path
p=Path('.')
for group in ['run/results/asap7','run/logs/asap7','run/reports/asap7']:
 for base in Path(group).glob('*/base'):
  for f in base.iterdir():
   if f.is_file() and (f.name.startswith('5_') or f.name.startswith('6_')):f.unlink()
for n in ['signoff','signoff_pre_dx108']:
 if n=='signoff' and Path(n).exists():Path(n).rename('signoff_pre_dx108')
PY
bash ./run_dx108_hbm.sh "$PWD" finish 32 16 > run_dx108.log 2>&1
