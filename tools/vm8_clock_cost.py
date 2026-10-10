#!/usr/bin/env python3
"""Measure a VM8 half's actual CTS clock-buffer area/power and mapped VT inventory.

Placement-parasitic TT clock power is evidence about this half, not full-die
power signoff. The clock topology is walked from all ck* source ports; sequential
cell power is excluded from the clock-buffer subtotal. Run on the artifact host.
"""
import argparse
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
TCL = r'''
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $PLAT/lib/NLDM/*RVT_TT* $PLAT/lib/NLDM/*_LVT_TT_* $PLAT/lib/NLDM/*_SLVT_TT_*] {
 if {![string match *FAKE* $l]} {read_liberty $l}
}
foreach l [glob -nocomplain /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/*_tt.lib] {read_liberty $l}
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source $PLAT/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set fo [open /t/clock_inventory.txt w]
set blk [ord::get_db_block];set dbu [$blk getDbUnitsPerMicron]
set counted [dict create];set cells {}
foreach bt [$blk getBTerms] {
 set n [regsub {\[0\]$} [$bt getName] {}]
 if {![regexp {^ck([wens][0-9]*)?$} $n]} {continue}
 set todo [list [$bt getNet]];set seen [dict create]
 while {[llength $todo]} {
  set net [lindex $todo 0];set todo [lrange $todo 1 end]
  if {$net eq "NULL" || [dict exists $seen [$net getName]]} {continue}
  dict set seen [$net getName] 1
  foreach it [$net getITerms] {
   if {[$it isOutputSignal]} {continue}
   set inst [$it getInst];set m [$inst getMaster]
   if {[$m isSequential]} {continue}
   set nm [$inst getName]
   if {![dict exists $counted $nm]} {
    dict set counted $nm 1
    set area [expr {double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]
    puts $fo "BUFFER $n $nm [$m getName] $area"
    lappend cells [get_cells -quiet $nm]
   }
   foreach o [$inst getITerms] {if {[$o isOutputSignal]} {lappend todo [$o getNet]}}
  }
 }
}
close $fo
set fo [open /t/mapped_inventory.txt w]
foreach inst [$blk getInsts] {
 set m [$inst getMaster];set mn [$m getName]
 if {![regexp {_ASAP7_75t_([A-Z]+)$} $mn -> vt]} {continue}
 puts $fo "$vt $mn [expr {double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]"
}
close $fo
report_power -instances $cells -digits 6 > /t/clock_power.rpt
report_power -digits 6 > /t/component_default_activity_power.rpt
'''


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', required=True, type=Path)
    ap.add_argument('--source', required=True, type=Path)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--image', default='openroad/orfs:latest')
    a = ap.parse_args()
    base, src, out = a.base.resolve(), a.source.resolve(), a.out.resolve()
    for name in ('4_1_cts.odb', '4_cts.sdc'):
        if not (base/name).is_file():
            ap.error(f'missing completed CTS artifact {base/name}')
    out.mkdir(parents=True, exist_ok=False)
    (out/'clock_cost.tcl').write_text(TCL)
    cmd = ['docker', 'run', '--rm', '-v', f'{base}:/base:ro', '-v', f'{src}:/src:ro', '-v', f'{out}:/t',
           a.image, 'bash', '-lc', '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/clock_cost.tcl']
    with (out/'openroad.log').open('w') as log:
        subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
    taps = defaultdict(lambda: {'buffers': 0, 'area_um2': 0.0})
    for line in (out/'clock_inventory.txt').read_text().splitlines():
        _, tap, inst, master, area = line.split()
        taps[tap]['buffers'] += 1
        taps[tap]['area_um2'] += float(area)
    power = 0.0
    for line in (out/'clock_power.rpt').read_text().splitlines():
        fields = line.split()
        if len(fields) != 5:
            continue
        try:
            power += float(fields[3])
        except ValueError:
            pass
    vt = defaultdict(lambda: {'cells': 0, 'area_um2': 0.0})
    for line in (out/'mapped_inventory.txt').read_text().splitlines():
        kind, master, area = line.split()
        vt[kind]['cells'] += 1
        vt[kind]['area_um2'] += float(area)
    total = sum(r['cells'] for r in vt.values())
    summary = dict(schema='opentallas.vm8-clock-cost.v2', source_commit=a.source_commit,
        scope='TT CTS, placement parasitics; actual clock buffers, excluding sequential cells; not die power signoff',
        base=str(base), artifact_sha256={name: sha256(base/name) for name in ('4_1_cts.odb', '4_cts.sdc')},
        reporter_sha256=sha256(Path(__file__)), per_tap=dict(taps),
        clock_buffer_count=sum(v['buffers'] for v in taps.values()),
        clock_buffer_area_um2=sum(v['area_um2'] for v in taps.values()),
        clock_buffer_power_w=power, mapped_vt=dict(vt),
        mapped_lvt_fraction=vt['L']['cells']/total if total else None,
        notes='Component power uses default data activity; clock-buffer power uses defined clocks. Final die clock drops and routed capacitance remain required.')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
