#!/usr/bin/env python3
"""Execute station-generated pin Tcl and reject fixed pins in corner strips."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('station_pin_driver', ROOT/'tools/run_abi3_physical.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
module = ast.parse((HERE/'run_owned.py').read_text())
pins = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'pins')
namespace = dict(os=os, a=SimpleNamespace(core_width=520.0, core_height=160.0),
                 _orig_io_constraints_tcl=driver.io_constraints_tcl)
exec(compile(ast.Module(body=[pins], type_ignores=[]), 'station-pins', 'exec'), namespace)
os.environ.update(OT_PIN_GROUP_MAX='32', OT_PIN_BALANCE_H='M4 M6', OT_PIN_BALANCE_V='M5 M7')
# The real NO3 bus wall has ~10k boundary flops. Exercise every face at that
# density; bottom/top must exclude the W/E strips and left/right the S/N strips.
records = []
for edge in ('bottom', 'top', 'left', 'right'):
    tcl = namespace['pins']([dict(regex='^ACK_frame', edge=edge)], False, [0, 0, 524.104, 164.32])
    prefix, body = tcl.split('set ot_region_pins', 1)
    lo, hi = (2.16, 162.16) if edge in ('left', 'right') else (2.052, 522.052)
    axis = 1 if edge in ('left', 'right') else 0
    mock = '''
proc ot_match_pins {pattern} {
  set names {}; for {set k 0} {$k < 10428} {incr k} { lappend names "ACK_frame\\[$k\\]" }; return $names
}
set checked 0
proc place_pin {args} {
  global checked
  set i [lsearch -exact $args -location]
  set xy [lindex $args [expr {$i+1}]]
  set coordinate [lindex $xy AXIS]
  if {$coordinate < LOWER || $coordinate > UPPER} {error "pin outside core: $xy"}
  incr checked
}
'''.replace('AXIS', str(axis)).replace('LOWER', str(lo)).replace('UPPER', str(hi))
    result = subprocess.run(['tclsh'], input=prefix+mock+'set ot_region_pins'+body+'\nputs "CHECKED $checked"\n',
                            text=True, capture_output=True, check=True)
    if result.stderr or result.stdout.strip() != 'CHECKED 10428':
        raise RuntimeError(result.stdout+result.stderr)
    # Invalid bounded regions must fail before placing any pins.
    try:
        namespace['pins']([dict(regex='^ACK_frame', edge=edge, range_um=[0, 1])], False, [0, 0, 524.104, 164.32])
    except ValueError:
        pass
    else:
        raise AssertionError('corner-only region was accepted')
    records.append(dict(edge=edge, count=10428, allowed_coordinate_um=[lo, hi]))
print(json.dumps(dict(passed=True, faces=records, rtl_change=False)))
