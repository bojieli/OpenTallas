#!/usr/bin/env python3
"""Read-only clock coverage census of every consumed real master in an S81 kit.

Run via ot-run. This links the exact generated floorplan database and unchanged
kit clock constraints. It proves caller clock topology, not extracted timing or
internal hard-IP characterization. Clock pins come from the consumed Liberty
files; placeholders are explicitly outside this census.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kit', type=Path, required=True)
    ap.add_argument('--odb', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit('Output must be a fresh immutable directory')
    a.out.mkdir(parents=True)
    source = Path((a.kit / 'src_root').read_text().strip())
    index = json.loads((a.kit / 'index.json').read_text())
    clock_pins = {}
    lib_hashes = {}
    for master, row in index['masters'].items():
        if row['view'] not in ('closed', 'macro'):
            continue
        # The index is authoritative for the actual consumed corner library.
        lib = source / row['libs']['ss']
        text = lib.read_text()
        names = re.findall(r'\bpin\s*\(\s*"?([^\s"()]+)"?\s*\)\s*\{[^{}]*?\bclock\s*:\s*true\s*;', text)
        clock_pins[master] = sorted(set(names))
        lib_hashes[master] = {'path': str(lib), 'sha256': sha(lib)}
    original = (a.kit / 'sta_ss.tcl').read_text().split('report_checks ')[0]
    prefix = 'read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef\n'
    prefix += '\n'.join(l for l in original.splitlines() if 'read_spef ' not in l and not l.startswith('link_design ')) + '\n'
    prefix = prefix.replace('read_verilog /kit/die.v', 'read_db /assembly/floorplan.odb')
    body = 'set masters [dict create]\n'
    for master, pins in clock_pins.items():
        body += 'dict set masters {' + master + '} {' + ' '.join(pins) + '}\n'
    body += r'''
set count 0
foreach inst [[ord::get_db_block] getInsts] {
 set master [[$inst getMaster] getName]
 if {![dict exists $masters $master]} {continue}
 incr count
 set name [$inst getName]
 if {![llength [dict get $masters $master]]} {puts "OT_BOUND_NO_DECLARED_CLOCK $master $name"}
 foreach clockpin [dict get $masters $master] {
  set pname "$name/$clockpin"
  set pins [get_pins -quiet $pname]
  if {![llength $pins]} {puts "OT_BOUND_CLOCK_PIN_MISSING $master $pname";continue}
  foreach pin $pins {
   set clocks [get_property $pin clocks]
   if {![llength $clocks]} {puts "OT_BOUND_CLOCK_UNCONSTRAINED $master $pname"}
   foreach c $clocks {puts "OT_BOUND_CLOCK $master $pname [get_full_name $c] [get_property $c period]"}
  }
 }
}
puts "OT_BOUND_INSTANCE_COUNT $count"
puts "OT_BOUND_CLOCK_DONE"
exit
'''
    script = a.out / 'census.tcl'
    script.write_text(prefix + body)
    cmd = ['docker', 'run', '--rm', '-v', f'{source}:{source}:ro', '-v', f'{a.kit}:/kit:ro',
           '-v', f'{a.odb.parent}:/assembly:ro', '-v', f'{a.out}:/audit', 'openroad/orfs:latest',
           '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad', '-no_init', '-exit', '/audit/census.tcl']
    # Mount input filename consistently, without changing its bytes.
    if a.odb.name != 'floorplan.odb':
        script.write_text(script.read_text().replace('/assembly/floorplan.odb', '/assembly/' + a.odb.name))
    run = subprocess.run(cmd, capture_output=True, text=True)
    log = run.stdout + run.stderr
    (a.out / 'census.log').write_text(log)
    rec = {'schema': 'opentallas.bound_leaf_clock_census.v1',
           'scope': 'actual bound clock topology; no extracted timing or internal characterization qualification',
           'command': cmd, 'returncode': run.returncode, 'done': 'OT_BOUND_CLOCK_DONE' in log,
           'kit_hashes': {n: sha(a.kit / n) for n in ('die.v', 'index.json', 'sta_ss.tcl', 'clock_delivery.json')},
           'odb_sha256': sha(a.odb), 'libs': lib_hashes, 'script_sha256': sha(script),
           'log_sha256': sha(a.out / 'census.log'), 'clock_pins': clock_pins,
           'clocks': [{'master': m, 'pin': p, 'clock': c, 'period_ps': float(t)} for m, p, c, t in
                      re.findall(r'^OT_BOUND_CLOCK (\S+) (\S+) (\S+) (\S+)$', log, re.M)],
           'unconstrained': [{'master': m, 'pin': p} for m, p in re.findall(r'^OT_BOUND_CLOCK_UNCONSTRAINED (\S+) (\S+)$', log, re.M)],
           'missing': re.findall(r'^OT_BOUND_CLOCK_PIN_MISSING (.*)$', log, re.M),
           'no_declared_clock': re.findall(r'^OT_BOUND_NO_DECLARED_CLOCK (.*)$', log, re.M),
           'expected_real_instances': sum(row.get('instances', 0) for row in index['masters'].values() if row['view'] in ('closed', 'macro'))}
    counts = re.findall(r'^OT_BOUND_INSTANCE_COUNT (\d+)$', log, re.M)
    rec['observed_real_instances'] = int(counts[0]) if len(counts) == 1 else None
    rec['coverage_pass'] = (run.returncode == 0 and rec['done'] and not rec['unconstrained'] and not rec['missing']
                            and not rec['no_declared_clock'] and rec['expected_real_instances'] == rec['observed_real_instances'])
    (a.out / 'receipt.json').write_text(json.dumps(rec, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: rec[k] for k in ('returncode', 'done', 'coverage_pass', 'expected_real_instances', 'observed_real_instances')}))
    raise SystemExit(run.returncode)


if __name__ == '__main__':
    main()
