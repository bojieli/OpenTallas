#!/bin/bash
set -euo pipefail
SRC=$1;OUT=$2;mkdir -p "$OUT"
S=$SRC/rtl/dsrom_sys
for mode in base relay stalled data_mut response_mut;do
 case $mode in base) P="";;relay)P="-GRET_DELAY=8";;stalled)P="-GRET_DELAY=8 -GSTALL=1";;data_mut)P="-GRET_DELAY=8 -GMUT=1";;response_mut)P="-GMUT=2";;esac
 verilator --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb_s81_hop_vm $P --Mdir "$OUT/$mode" -o tb \
 "$S/s81_ph/vm/ot_s81ph_vm_mem.sv" "$S/s81_ctrl/ot_s81_vm_adapter.sv" "$S/s81_ctrl/ot_s81_hop_tx.sv" "$S/s81_ctrl/test/tb_s81_hop_vm.sv" >"$OUT/$mode.build" 2>&1
 "$OUT/$mode/tb" >"$OUT/$mode.log" 2>&1
 done
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]);rows=[]
for mode,expected in [('base','PASS'),('relay','PASS'),('stalled','PASS'),('data_mut','FAIL'),('response_mut','FAIL')]:
 r=[r for r in (out/(mode+'.log')).read_text().splitlines() if r.startswith('TB_S81_HOP_VM')]
 if len(r)!=1 or r[0].split()[-1]!=expected:raise SystemExit('gate FAIL '+mode+': '+str(r))
 rows.extend(r)
(out/'verdicts.log').write_text('\n'.join(rows)+'\n');print('\n'.join(rows));print('HOP_VM_GATE PASS')
PY
