#!/bin/bash
set -euo pipefail
SRC=$1;OUT=$2;mkdir -p "$OUT";S=$SRC/rtl/dsrom_sys/s81_ctrl
for mode in base ignore_reuse;do
 case $mode in base) P=0;;ignore_reuse)P=1;;esac
 verilator --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb_s81_htransfer_slots -GMUT=$P --Mdir "$OUT/$mode" -o tb \
 "$S/ot_s81_htransfer.sv" "$S/test/tb_s81_htransfer_slots.sv" >"$OUT/$mode.build" 2>&1
 "$OUT/$mode/tb" >"$OUT/$mode.log" 2>&1
done
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);rows=[]
for mode,expected in [('base','PASS'),('ignore_reuse','FAIL')]:
 lines=[x for x in (p/(mode+'.log')).read_text().splitlines() if x.startswith('TB_S81_HTRANSFER_SLOTS')]
 if len(lines)!=1 or lines[0].split()[-1]!=expected:raise SystemExit(f'{mode}: {lines}')
 rows+=lines
(p/'verdicts.log').write_text('\n'.join(rows)+'\n');print('\n'.join(rows));print('HTRANSFER_SLOT_GATE PASS')
PY
