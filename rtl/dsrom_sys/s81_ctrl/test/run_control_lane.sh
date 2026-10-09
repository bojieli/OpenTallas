#!/bin/bash
set -euo pipefail
SRC=$1;OUT=$2;mkdir -p "$OUT";S=$SRC/rtl/dsrom_sys
for mode in clean replay collision padding data_mut last_mut;do
 case $mode in clean)P="";;replay)P="-GERR=1";;collision)P="-GNEG=1";;padding)P="-GNEG=2";;data_mut)P="-GMUT=1";;last_mut)P="-GMUT=2";;esac
 verilator --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb_s81_control_lane $P --Mdir "$OUT/$mode" -o tb \
 "$S/ot_dsrom_link_ct.sv" "$S/ot_dsrom_link_chan.sv" "$SRC/rtl/link/ot_link_crc32.sv" "$S/s81_ctrl/ot_s81_ctrl_lane_adapter.sv" "$S/s81_ctrl/test/tb_s81_control_lane.sv" >"$OUT/$mode.build" 2>&1
 "$OUT/$mode/tb" >"$OUT/$mode.log" 2>&1
 done
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]);rows=[]
for mode,expected in [('clean','PASS'),('replay','PASS'),('collision','PASS'),('padding','PASS'),('data_mut','FAIL'),('last_mut','FAIL')]:
 r=[r for r in (out/(mode+'.log')).read_text().splitlines() if r.startswith('TB_S81_CONTROL_LANE')]
 if len(r)!=1 or r[0].split()[-1]!=expected:raise SystemExit('gate FAIL '+mode+': '+str(r))
 rows.extend(r)
(out/'verdicts.log').write_text('\n'.join(rows)+'\n');print('\n'.join(rows));print('CONTROL_LANE_GATE PASS')
PY
