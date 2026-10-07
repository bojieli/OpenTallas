"""Prepare a read-only final SS/FF macro-pin coverage audit on the retained ECO.
Run on the compute host with RUN AUDIT as arguments. Does not edit RUN inputs.
"""
import hashlib
import json
from pathlib import Path
import sys

run, audit = map(Path, sys.argv[1:])
audit.mkdir(exist_ok=False)
eco = run / 'cl/eco-r2/pass1'
route = run / 'routes/dshead_elemB_ss_a318fdf47'
base = next((eco / 'orfs/results/asap7').glob('*/base'))
installed = next((route / 'work/orfs/results/asap7').glob('*/base'))
cs = json.loads((eco / 'corner_sta.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
proof = {'candidate': str(base), 'installed': str(installed), 'binding': {}, 'source_files': {}, 'macros': {}}
for ext in ('odb', 'sdc', 'spef'):
    h = sha(base / ('6_final.' + ext))
    assert h == cs['setup_ss'][ext + '_sha256'] == cs['hold_ff'][ext + '_sha256']
    assert h == sha(installed / ('6_final.' + ext))
    proof['binding'][ext] = h
for rel, h in cs['post_sdc'].items():
    assert sha(run / 'src' / rel) == h
    proof['binding'][rel] = h
physical = json.loads((route / 'physical.json').read_text())
for entry in physical['design']['sources']:
    rel = entry['path']; h = sha(run / 'src' / rel)
    assert h == entry['sha256']
    proof['source_files'][rel] = h
macro = 'physical/asap7_memory_macros/ot_rom_4096x274_m8'
for suffix in ('ss.lib', 'ff.lib', 'lef'):
    rel = macro + '/ot_rom_4096x274_m8_' + suffix if suffix != 'lef' else macro + '/ot_rom_4096x274_m8.lef'
    proof['macros'][rel] = sha(run / 'src' / rel)
for corner in ('ss', 'ff'):
    script = (eco / 'orfs' / f'w18_sta_{corner}.tcl').read_text()
    assert f'ot_rom_4096x274_m8_{corner}.lib' in script
    assert 'read_spef' in script and 'signoff_elemB.sdc' in script
    assert script.rstrip().endswith('exit')
    extra = r'''
set bind_check @CHECK@
set count 0
set worst 1e9
foreach pin [all_registers -data_pins] {
  set name [get_full_name $pin]
  if {![string match {u_rom*/*} $name]} continue
  set slack [get_property $pin slack_$bind_check]
  if {![string is double -strict $slack] || $slack eq "INF" || $slack eq "-INF" || $slack != $slack} {
    error "BIND missing finite @CORNER@ macro slack: $name $slack"
  }
  incr count
  set worst [expr {min($worst,$slack)}]
  puts "OT_BIND_MACRO @CORNER@ [list $name $slack]"
}
if {$count != 26} { error "BIND expected 26 ROM timing-check pins; got $count" }
if {$worst < 15} { error "BIND macro endpoint misses +15 ps: $worst" }
set nout 0
foreach pin [all_outputs] {
  set slack [get_property $pin slack_$bind_check]
  if {![string is double -strict $slack] || $slack eq "INF" || $slack eq "-INF" || $slack != $slack} {
    error "BIND missing finite output slack: [get_full_name $pin] $slack"
  }
  if {$slack < 15} { error "BIND output misses +15 ps" }
  incr nout
}
set period [get_property [get_clocks core_clk] period]
if {abs($period-833.333)>0.001} { error "BIND incorrect signoff period $period" }
write_sdc -no_timestamp /audit/effective_@CORNER@.sdc
puts "OT_BIND_DONE @CORNER@ macro_count $count macro_worst $worst outputs $nout period $period"
exit
'''.replace('@CORNER@', corner).replace('@CHECK@', 'max' if corner == 'ss' else 'min')
    (audit / f'bind_{corner}.tcl').write_text('set_thread_count 1\n' + script.rstrip()[:-4] + extra)
image = 'sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
proof['image'] = image
(audit / 'input_binding.json').write_text(json.dumps(proof, indent=2)+'\n')
body = ['#!/bin/bash', 'set -euo pipefail']
for c in ('ss','ff'):
    body += [f'docker run --rm -v {eco}/orfs:/work:ro -v {run}/src:/src:ro -v {audit}:/audit {image} bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/bind_{c}.tcl" > {audit}/bind_{c}.log 2>&1',
             f'grep -q "^OT_BIND_DONE {c} " {audit}/bind_{c}.log',
             f'! grep -E "\\[ERROR|^Error:" {audit}/bind_{c}.log']
body += [f'echo PASS > {audit}/complete']
(audit/'run.sh').write_text('\n'.join(body)+'\n')
print(audit)
