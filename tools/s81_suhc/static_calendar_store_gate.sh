#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output directory}
mkdir -p "$out"
cd "$root"
sources=(rtl/dsrom_sys/s81_suhc/test/tb_s81_su_calendar_store.sv
 rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_calendar_store.sv
 rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_calendar_ctl.sv rtl/hdc/ot_sram_bank.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
iverilog -g2012 -s tb_s81_su_calendar_store -o "$out/positive" "${sources[@]}"
vvp "$out/positive" > "$out/positive.log" 2>&1
iverilog -g2012 -s tb_s81_su_calendar_store -Ptb_s81_su_calendar_store.MUT=1 -o "$out/mutant" "${sources[@]}"
set +e
vvp "$out/mutant" > "$out/mutant.log" 2>&1
mutant_rc=$?
set -e
if [ "$mutant_rc" -eq 0 ]; then exit 1; fi
python3 - "$out" "$mutant_rc" "${sources[@]}" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1])
row=dict(schema='opentallas.s81.calendar-store-component.v1',qualified=False,
         scope='two actual64x512 SRAMs + fixed control;64consecutiveedges/no bubbles',
         positive_rc=0,mutant_rc=int(sys.argv[2]),
         sources={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sys.argv[3:]},
         logs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')})
(out/'gate.json').write_text(json.dumps(row,indent=2)+'\n')
PY
