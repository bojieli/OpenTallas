#!/bin/bash
set -euo pipefail
src=$1;out=$2;mkdir -p "$out"
for mut in 0 1 2;do
 iverilog -g2012 -s tb_s81_hland_fallback -Ptb_s81_hland_fallback.MUT=$mut -o "$out/m$mut.vvp" "$src/rtl/dsrom_sys/s81_suhc/ot_s81_hc_hland.sv" "$src/rtl/dsrom_sys/s81_ctrl/test/tb_s81_hland_fallback.sv" > "$out/m$mut.build" 2>&1
 vvp "$out/m$mut.vvp" > "$out/m$mut.log"
done
python3 - "$out" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);rows=[]
for m,w in [(0,'PASS'),(1,'FAIL'),(2,'FAIL')]:
 lines=[s for s in (p/f'm{m}.log').read_text().splitlines() if s.startswith('HLAND_FALLBACK')];s=lines[0] if len(lines)==1 else ''
 if not s.startswith('HLAND_FALLBACK') or s.split()[-1]!=w:raise SystemExit(s)
 rows.append(s)
(p/'verdicts.log').write_text('\n'.join(rows)+'\n');print('\n'.join(rows))
PY
