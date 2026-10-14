#!/bin/bash
set -euo pipefail
SRC=$1;OUT=$2;mkdir -p "$OUT";S=$SRC/rtl/dsrom_sys/s81_ctrl
for mode in base unrebase; do
 case $mode in base) P=0;;unrebase)P=1;;esac
 verilator --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb_s81_native_slot_program -GMUT=$P --Mdir "$OUT/$mode" -o tb \
 "$SRC/rtl/lib/ot_reset_sync.sv" "$SRC/rtl/lib/ot_async_fifo.sv" "$S/ot_s81_engine_adapter.sv" "$S/ot_s81_stage_seq.sv" "$S/test/tb_s81_native_slot_program.sv" >"$OUT/$mode.build" 2>&1
 "$OUT/$mode/tb" >"$OUT/$mode.log" 2>&1
done
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);rows=[]
for mode,expected in [('base','PASS'),('unrebase','FAIL')]:
 lines=[x for x in (p/(mode+'.log')).read_text().splitlines() if x.startswith('TB_S81_NATIVE_SLOT_PROGRAM')]
 if len(lines)!=1 or lines[0].split()[-1]!=expected:raise SystemExit(f'{mode}: {lines}')
 rows+=lines
(p/'verdicts.log').write_text('\n'.join(rows)+'\n');print('\n'.join(rows));print('NATIVE_SLOT_PROGRAM_GATE PASS')
PY
