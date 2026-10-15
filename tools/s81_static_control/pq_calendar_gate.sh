#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh outputdir};mkdir "$out";cd "$out"
PYTHONPATH="$root/tools/s81_static_control" python3 - <<'PY'
from pq_calendar import compile_events,viamap
rows=[]
for i in range(23):
 t=i if i<12 else i*3
 rows.append(dict(timestamp=t,action=dict(vm_req=1,vm_addr=8192+i*64,stream_req=1,stream_addr=8192+i,accept_tag=0)))
rows.append(dict(timestamp=80,action=dict(phase_end=1)))
words=compile_events(rows,[dict(engine=0,issue=0,done=100,native_tag=0)])
open('expected.hex','w').write(''.join(f'{w:025x}\n'for w in words))
open('pq_calendar_action.viamap.hex','w').write(viamap([w&((1<<72)-1)for w in words]))
open('pq_calendar_time.viamap.hex','w').write(viamap([w>>72 for w in words]))
PY
verilator --binary --timing -j 1 -Wno-fatal --top-module tb_s81_pq_calendar_rom --Mdir obj \
 "$root/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" \
 "$root/rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv" \
 "$root/rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv" \
 "$root/rtl/dsrom_sys/s81_static_control/test/tb_s81_pq_calendar_rom.sv" > build.log 2>&1
for mode in 0 1;do obj/Vtb_s81_pq_calendar_rom +OT_ROM_DIR="$out" +mode="$mode" > "mode$mode.log" 2>&1;cat "mode$mode.log";done
# Mutate one actual immutable ROM cell; source scoreboard remains untouched.
cp pq_calendar_action.viamap.hex pq_calendar_action.original.hex
python3 - <<'PY'
p='pq_calendar_action.viamap.hex';rows=open(p).read().splitlines();rows[0]=f'{int(rows[0],16)^(1<<(3*8+1)):0144x}';open(p,'w').write('\n'.join(rows)+'\n')
PY
if obj/Vtb_s81_pq_calendar_rom +OT_ROM_DIR="$out" > data_mutant.log 2>&1;then echo 'FAIL ROM mutant escaped';exit 1;fi
grep -q 'actual ROM action mismatch' data_mutant.log;cat data_mutant.log
# phase_end is action bit72: it lives in bit0 of the SECOND real ROM.
# Mutating that cell tests the widened action across the physical bank split.
cp pq_calendar_action.original.hex pq_calendar_action.viamap.hex
cp pq_calendar_time.viamap.hex pq_calendar_time.original.hex
python3 - <<'PY2'
p='pq_calendar_time.viamap.hex';rows=open(p).read().splitlines();rows[23//8]=f'{int(rows[23//8],16)^(1<<(23%8)):0144x}';open(p,'w').write('\n'.join(rows)+'\n')
PY2
if obj/Vtb_s81_pq_calendar_rom +OT_ROM_DIR="$out" > upper_action_mutant.log 2>&1;then echo 'FAIL upper action mutant escaped';exit 1;fi
grep -q 'actual ROM action mismatch' upper_action_mutant.log;cat upper_action_mutant.log
sha256sum "$root/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" "$root/rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv" "$root/rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv" "$root/rtl/dsrom_sys/s81_static_control/test/tb_s81_pq_calendar_rom.sv" "$root/tools/s81_static_control/pq_calendar.py" > source.sha256
