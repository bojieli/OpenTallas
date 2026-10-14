#!/bin/bash
set -euo pipefail
SRC=$1;OUT=$2;mkdir -p "$OUT"
S=$SRC/rtl/dsrom_sys/s81_ctrl
for mode in base_early base_latest circular latest; do
 case $mode in base_early) P='-GMUT=0 -GFIRST=1';; base_latest) P='-GMUT=0 -GFIRST=0';; circular) P='-GMUT=1 -GFIRST=1';; latest) P='-GMUT=2 -GFIRST=0';;esac
 verilator --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb_s81_queued_head $P --Mdir "$OUT/$mode" -o tb \
 "$SRC/rtl/lib/ot_reset_sync.sv" "$SRC/rtl/lib/ot_async_fifo.sv" "$S/ot_s81_engine_adapter.sv" "$S/test/tb_s81_queued_head.sv" >"$OUT/$mode.build" 2>&1
 "$OUT/$mode/tb" >"$OUT/$mode.log" 2>&1
done
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);rows=[]
for mode,expected in [('base_early','PASS'),('base_latest','PASS'),('circular','FAIL'),('latest','FAIL')]:
 lines=[x for x in (p/(mode+'.log')).read_text().splitlines() if x.startswith('TB_S81_QUEUED_HEAD')]
 if len(lines)!=1 or lines[0].split()[-1]!=expected:raise SystemExit(f'{mode}: {lines}')
 rows+=lines
(p/'verdicts.log').write_text('\n'.join(rows)+'\n');print('\n'.join(rows));print('QUEUED_HEAD_GATE PASS')
PY
