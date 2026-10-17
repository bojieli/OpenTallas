#!/usr/bin/env python3
"""Stage an immutable archived station for a native electrical waveform/load replay.

No placement, routing, clock or path exceptions change. Each distance applies its
measured per-bit receiver slew and external source load to the actual CLOSED
native cell graph/SPEF. This isolates electrical validity; archived IO arrival
constraints do NOT establish composed sender-wire-receiver setup/hold.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stage(archive, run, views, cell, out):
    manifest = json.loads((archive / 'manifest.json').read_text())
    binding = json.loads((views / 'stage.json').read_text())['classes'][cell]
    if manifest['job'] != binding['job'] or manifest['block'] != cell:
        raise ValueError('CLOSED archive and exact bound job disagree')
    out.mkdir(parents=True, exist_ok=True)
    base = out / 'base'
    base.mkdir(exist_ok=True)
    consumed = []
    for f in manifest['files']:
        name = Path(f['path']).name
        if not f['path'].endswith('/base/' + name) or name not in ('6_final.odb', '6_final.sdc', '6_final.spef', '6_final.v'):
            continue
        p = archive / 'run' / f['stored']
        raw = subprocess.run(['zstd', '-dc', str(p)], check=True, stdout=subprocess.PIPE).stdout if f.get('compression') == 'zstd' else p.read_bytes()
        if digest(raw) != f['sha256']:
            raise ValueError('archive checksum mismatch: ' + str(p))
        (base / name).write_bytes(raw)
        consumed.append(dict(path=f['path'], sha256=f['sha256']))
    if len(consumed) != 4:
        raise ValueError('missing exact archived ODB/SDC/SPEF/netlist')
    export = archive / 'run' / 'record' / 'views' / cell
    raw = (export / f'{cell}_tt.lib').read_bytes()
    if digest(raw) != binding['files']['tt']['sha256']:
        raise ValueError('archive ETM differs from measured component ETM')
    model = json.loads((views / 'views' / cell / 'model.json').read_text())
    pairs = model['pairs']
    if len(pairs) != 1 or pairs[0]['dir'] != 'fwd':
        raise ValueError('this diagnostic supports exactly one forward data bus')
    mp = json.loads((run / 'map.json').read_text())['sinks']
    if {r['cls'] for r in mp.values()} != {cell}:
        raise ValueError('run must contain exactly the selected class')
    slk = {s[0]: float(s[2]) for line in (run / 'tt833.slk').read_text().splitlines() if len(s := line.split()) == 3}
    spef_path = run / 'reach.spef.gz'
    spef = gzip.decompress(spef_path.read_bytes()).decode() if spef_path.exists() else (run / 'reach.spef').read_text()
    if '*C_UNIT 1 FF' not in spef:
        raise ValueError('unknown extracted capacitance unit')
    # GRT emits PIN_CAP NONE: add actual receiving ETM input capacitance to wire cap.
    if '"PIN_CAP NONE"' not in spef:
        raise ValueError('unknown extracted pin-capacitance convention')
    caps = {}
    for b in spef.split('*D_NET ')[1:]:
        header = b.splitlines()[0].split()
        drv = re.search(r'^\*I (\S+) O\b', b, re.M)
        if not drv:
            raise ValueError('missing source terminal in SPEF')
        caps[drv[1].replace(':', '/', 1)] = float(header[1])
    text = raw.decode()
    input_caps = {}
    for m in re.finditer(r'pin\("?([^")]+)"?\)\s*\{(.*?)\n    \}', text, re.S):
        cap = re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)', m[2])
        if cap:
            input_caps[m[1]] = float(cap[1])
    cases = {}
    for pin, r in mp.items():
        inp = pin.split('/', 1)[1]
        bit = re.search(r'\[(\d+)\]$', inp)[1]
        op = pairs[0]['out_pins'][bit]
        load = caps[r['drv']] + input_caps[inp]
        if pin not in slk or not 0 <= slk[pin] < float('inf') or not 0 <= load < float('inf'):
            raise ValueError('missing/non-finite measured slew/load')
        cases.setdefault(r['d'], []).append(dict(input=inp, output=op, slew_ps=slk[pin], external_load_ff=load))
    if any(len(rows) != pairs[0]['width'] for rows in cases.values()):
        raise ValueError('incomplete per-distance payload')
    lines = []
    for d, rows in sorted(cases.items()):
        lines.append(f'puts "OT_NATIVE_ELECTRICAL_BEGIN {d}"')
        for r in rows:
            lines.append(f'set_input_transition {r["slew_ps"]} [get_ports {{{r["input"]}}}]')
            lines.append(f'set_load {r["external_load_ff"]} [get_ports {{{r["output"]}}}]')
        lines += [f'report_check_types -max_slew -max_capacitance -violators > /work/drv_{d}.rpt',
                  'set n 0; set worst 0; set wp {}',
                  'foreach p [all_registers -data_pins] {set x [get_property $p slew_max]; if {![string is double -strict $x] || $x == Inf} {error "non-finite native D slew"}; incr n; if {$x > $worst} {set worst $x; set wp [get_full_name $p]}}',
                  f'puts "OT_NATIVE_FINAL_D {d} count=$n worst_ps=$worst pin=$wp"',
                  f'puts "OT_NATIVE_ELECTRICAL_END {d}"']
    header = (export / 'export_tt.tcl').read_text().split('read_db ', 1)[0]
    tcl = header + '''read_db /work/base/6_final.odb
read_sdc /work/base/6_final.sdc
read_spef /work/base/6_final.spef
set_propagated_clock [all_clocks]
report_clock_properties [all_clocks]
''' + '\n'.join(lines) + '\nputs OT_NATIVE_ELECTRICAL_DONE\n'
    (out / 'native.tcl').write_text(tcl)
    (out / 'run.sh').write_text('''#!/bin/bash
set -eu
B=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus=1 -v "$B":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 1 -no_init -exit /work/native.tcl > /work/native.log 2>&1; chmod -R a+rwX /work'
grep -q OT_NATIVE_ELECTRICAL_DONE "$B/native.log"
''')
    rec = dict(schema='opentallas.relay_native_electrical_stage.v1', archive=str(archive), job=manifest['job'],
               archive_manifest_sha256=digest((archive/'manifest.json').read_bytes()), consumed=consumed,
               component_etm=binding['files']['tt'], component_map_sha256=digest((run/'map.json').read_bytes()),
               tcl_sha256=digest(tcl.encode()), cases=cases,
               scope='Native waveform/load electrical diagnostic; actual archived clock and IO constraints preserved. No composed setup/hold or die-safe reach inference.')
    (out / 'stage.json').write_text(json.dumps(rec, indent=1))
    shutil.copy2(archive / 'manifest.json', out / 'archive_manifest.json')
    print(f'staged {len(cases)} actual per-bit waveform/load cases, {len(consumed)} immutable native files')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for a in ('archive', 'run', 'views', 'out'):
        p.add_argument('--' + a, type=Path, required=True)
    p.add_argument('--cell', required=True)
    a = p.parse_args()
    stage(a.archive, a.run, a.views, a.cell, a.out)


if __name__ == '__main__':
    main()
