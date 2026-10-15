#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/ref_gate/hbm_att_bank_gather_compact_1015-20261015-041541
out=/srv/opentallas-scratch/codex/ATT-gather-five-buffer-ECO-r2
mkdir -p "$out/work"
cp -a "$base/native_route/native/work/orfs" "$out/work/orfs"
python3 - "$out/work/orfs" <<'PY'
from pathlib import Path
import sys
w=Path(sys.argv[1]);p=w/'hooks/pre_global_route_pre_grt.tcl'
s='''
# Source-preserving ECO: exact diagnosed noninverting data drivers only.
set ecob [ord::get_db_block]
set ef [open /work/five_buffer_ECO.tsv w]
puts $ef "instance\told_master\tnew_master\told_x\told_y\tnew_x\tnew_y"
foreach n {place4305 place4384 place4306 place4333 place4402} {
 set i [$ecob findInst $n]
 if {$i eq "NULL" || $i eq ""} {error "ECO missing diagnosed instance $n"}
 set old [[$i getMaster] getName]
 if {$old ne "BUFx3_ASAP7_75t_R"} {error "ECO unexpected master $n $old"}
 set xy [$i getLocation]
 replace_cell $n BUFx8_ASAP7_75t_R
 set i [$ecob findInst $n]
 set new [[$i getMaster] getName]
 if {$new ne "BUFx8_ASAP7_75t_R"} {error "ECO master did not change $n $new"}
 puts $ef "$n\t$old\t$new\t[lindex $xy 0]\t[lindex $xy 1]\t[lindex [$i getLocation] 0]\t[lindex [$i getLocation] 1]"
}
close $ef
detailed_placement
check_placement -verbose
# Rebuild placement parasitics after master/placement database mutations.
estimate_parasitics -placement
puts "FIVE_BUFFER_ECO_APPLIED"
'''
p.write_text(p.read_text()+s)
# Preserve synthesis/placement/CTS checkpoints. Only downstream implementation
# targets are invalidated; the immutable baseline work remains untouched.
for folder in ('results/asap7','logs/asap7','reports/asap7'):
 for d in (w/folder).glob('*/base'):
  for f in d.iterdir():
   if f.is_file() and f.name[:1] in ('5','6'):f.unlink()
PY
docker run --rm -v "$base/src:/src:ro" -v "$out/work/orfs:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 finish' > "$out/route.log" 2>&1
python3 "$base/src/tools/w18/corner_sta_ref.py" --orfs-dir "$out/work/orfs" --extra-sdc "$base/src/physical/ref_tile/hbm_att_bank_gather_compact_1015/signoff.sdc" --output "$out/corner_sta.json" > "$out/sta.log" 2>&1
