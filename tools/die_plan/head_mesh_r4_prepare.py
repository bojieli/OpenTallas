#!/usr/bin/env python3
"""HEAD-36 r4: preserve CTS, fix one overlapping raw pin, use existing MM hold repair."""
import json
from pathlib import Path
import re
import shutil
import sys

root, kit = map(Path, sys.argv[1:3])
sys.path.insert(0, str(root / 'tools/die_plan'))
import signoff
import kit_modes
src = Path('/srv/opentallas-scratch2/claude/die-head-36/mesh_e/signoff_r3fwd/constraint_fwd.sdc')
shutil.copy2(src, kit / 'constraint.sdc')
base = kit / 'run/results/asap7/dp_hd_mesh_e/base'
sdc = base / '4_cts.sdc'
ring = src.read_text().split('# source-synchronous ring inputs', 1)[1]
assert '# OT_FWD_RING_INPUTS' in ring
for p in [sdc, base / '4_1_cts.sdc']:
    if p.exists():
        p.write_text(p.read_text() + '\n# source-synchronous ring inputs' + ring)
signoff.copy_signoff_bundle(kit)
for name in ('orfs_hold_mm.py', 'orfs_hold_mm.tcl'):
    shutil.copy2(root / 'tools' / name, kit / name)
kit_modes.stage(kit, measured_hold=True)
io = kit / 'io.tcl'
text = io.read_text()
line = next(l for l in text.splitlines() if '-pin_name {rst_start_raw_1}' in l)
assert '{558.7520 34.1040}' in line
io.write_text(text.replace(line, line.replace('{558.7520 34.1040}', '{558.8800 34.1040}')))
with (kit / 'config.mk').open('a') as f:
    f.write('\n# HEAD r4: approved 0.128um raw_1 metal-overlap fix; data hold repair only\n'
            'export OT_IO_HOLD_PAD = 1\nexport OT_IO_HOLD_PAD_STAGE = grt\n'
            'export OT_IO_HOLD_PAD_MARGIN_PS = 10\n'
            'export SLEW_MARGIN = 20\nexport CAP_MARGIN = 20\n')
(kit / 'pin_eco.tcl').write_text('''read_db /work/run/results/asap7/dp_hd_mesh_e/base/4_cts.odb
place_pin -pin_name {rst_start_raw_1} -layer M7 -location {558.8800 34.1040} -pin_size {0.0800 0.4320}
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
foreach n {clk_t2 rst_start_raw_1} {
  set bt [$b findBTerm $n]
  set boxes {}
  foreach bp [$bt getBPins] { foreach x [$bp getBoxes] {
    lappend boxes [list [[$x getTechLayer] getName] [$x xMin] [$x yMin] [$x xMax] [$x yMax]]
  } }
  puts "HEAD_R4_PIN $n $boxes"
  if {[llength $boxes] != 1} {error "unexpected pin geometry $n"}
}
write_db /work/run/results/asap7/dp_hd_mesh_e/base/4_cts.odb
''')
(kit / 'r4_receipt.json').write_text(json.dumps(dict(
    source='die-head-34/mesh_e/kit/hd_mesh_e CTS, original failed verdict preserved',
    tools=str(root), new_rtl=False, added_cycles=0, raw_1_xy_um=[558.880,34.104],
    old_raw_1_xy_um=[558.752,34.104], clock_moved=False, io_min_ps=-40,
    hold_pad='existing OT_IO_HOLD_PAD HB4 <=4/bit, margin10 at GRT',
    reference='existing measured-FF two-mode session; GRT clock lock from main'), indent=2)+'\n')
print('HEAD_R4_PREPARED', kit)
