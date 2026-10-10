#!/bin/bash
set -euo pipefail
SRC=$1;OUT=$2;mkdir -p "$OUT"
S=$SRC/rtl/dsrom_sys/s81_ctrl
for mode in base same orphan ninth reset context_mut credit_mut;do
 case $mode in base) P="";;same)P="-GSAME=1";;orphan)P="-GNEG=1";;ninth)P="-GNEG=2";;reset)P="-GNEG=3";;context_mut)P="-GMUT=1";;credit_mut)P="-GMUT=2";;esac
 verilator --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb_s81_engine_adapter $P --Mdir "$OUT/$mode" -o tb \
 "$SRC/rtl/lib/ot_reset_sync.sv" "$SRC/rtl/lib/ot_async_fifo.sv" "$S/ot_s81_engine_adapter.sv" "$S/test/tb_s81_engine_adapter.sv" >"$OUT/$mode.build" 2>&1
 "$OUT/$mode/tb" >"$OUT/$mode.log" 2>&1
 done
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]); rows=[]
for mode,expected in [('base','PASS'),('same','PASS'),('orphan','PASS'),('ninth','PASS'),('reset','PASS'),('context_mut','FAIL'),('credit_mut','FAIL')]:
 r=[r for r in (out/(mode+'.log')).read_text().splitlines() if r.startswith('TB_S81_ENGINE_ADAPTER')]
 if len(r)!=1 or r[0].split()[-1]!=expected:raise SystemExit('gate FAIL '+mode+': '+str(r))
 rows.extend(r)
(out/'verdicts.log').write_text('\n'.join(rows)+'\n');print('\n'.join(rows));print('ENGINE_ADAPTER_GATE PASS')
PY
