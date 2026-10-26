#!/bin/bash
set -euo pipefail
route=/srv/opentallas-scratch/codex/ATT-gather-five-buffer-ECO-r3
src=/srv/opentallas-scratch/claude/ref_gate/hbm_att_bank_gather_compact_1015-20261015-041541/src
out=/srv/opentallas-scratch/codex/ATT-gather-five-buffer-ECO-r3/native_drvs
mkdir -p "$out"
python3 - "$route/work/orfs" "$out" <<'PY'
import sys
from pathlib import Path
root,out=map(Path,sys.argv[1:])
for c in ('tt','ff','ss'):
 s=(root/f'w18_sta_{c}.tcl').read_text();s=s.rsplit('exit',1)[0]+'\nputs "NATIVE_DRV_BEGIN"\nset eco_block [ord::get_db_block]\nforeach inst {place4305 place4384 place4306 place4333 place4402} {set obj [$eco_block findInst $inst]; puts "ECO_FINAL_MASTER $inst [[$obj getMaster] getName] [$obj getLocation]"}\nset ckmin 1e99; set ckmax -1e99; set ckn 0\nforeach cp [all_registers -clock_pins] {\n set a [get_property $cp arrival_max_rise]\n if {[string is double -strict $a]} {incr ckn; set ckmin [expr min($ckmin,$a)]; set ckmax [expr max($ckmax,$a)]}\n}\nputs "ACTUAL_FINAL_CLOCK n=$ckn min=$ckmin max=$ckmax spread=[expr $ckmax-$ckmin]"\nreport_check_types -max_slew -max_capacitance -max_fanout -violators\nputs "NATIVE_DRV_END"\nexit\n';(out/f'{c}.tcl').write_text(s)
PY
for corner in tt ff ss;do
 docker run --rm -v "$route/work/orfs:/work:ro" -v "$src:/src:ro" -v "$out:/audit" openroad/orfs:latest bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/$corner.tcl" > "$out/$corner.log" 2>&1
done
