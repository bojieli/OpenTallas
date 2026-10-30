#!/usr/bin/env python3
"""Place existing HEAD mesh collector stages within their exact combinational reach."""
import json
from pathlib import Path
import sys

targets, out = map(Path, sys.argv[1:3])
rows = json.loads(targets.read_text())
lines = ['read_db /work/run/results/asap7/dp_hd_mesh_e/base/3_place.odb',
         'set b [ord::get_db_block]', 'set u [$b getDbUnitsPerMicron]',
         'set saved {}; set moved {}']
for name, data in rows.items():
    x, y = data['target_xy']
    w, h = data['size_um']
    llx = round((x - w / 2) / 0.054) * 0.054
    lly = round((y - h / 2 - 4.32) / 0.27) * 0.27 + 4.32
    lines += [f'set i [$b findInst {{{name}}}]',
              f'if {{$i eq "NULL"}} {{error {{missing target {name}}}}}',
              'dict set moved [$i getName] 1',
              '$i setPlacementStatus NONE',
              f'$i setLocation [expr {{round({llx:.6f}*$u)}}] [expr {{round({lly:.6f}*$u)}}]',
              '$i setPlacementStatus PLACED']
lines += ['foreach i [$b getInsts] {',
          '  if {[dict exists $moved [$i getName]]} continue',
          '  dict set saved [$i getName] [$i getPlacementStatus]',
          '  if {[$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}',
          '}',
          'detailed_placement', 'check_placement -verbose',
          'foreach i [$b getInsts] {',
          '  if {[dict exists $moved [$i getName]]} {',
          '    puts "HEAD_CONTROL_PLACED [$i getName] [$i getLocation]"',
          '    $i setPlacementStatus FIRM',
          '  } elseif {[dict exists $saved [$i getName]]} {',
          '    $i setPlacementStatus [dict get $saved [$i getName]]',
          '  }',
          '}',
          'write_db /out/after.odb',
          'set ::env(OT_GEOM_OUT) /out/geom.tsv',
          'source /out/geom_dump.tcl', 'exit']
out.write_text('\n'.join(lines) + '\n')
