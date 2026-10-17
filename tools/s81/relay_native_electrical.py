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


def collect(directory):
    rec = json.loads((directory / 'stage.json').read_text())
    text = (directory / 'native.log').read_text()
    if 'OT_NATIVE_ELECTRICAL_DONE' not in text:
        raise ValueError('native replay did not complete')
    rows = []
    prefix = None
    failed = False
    width = len(next(iter(rec['cases'].values())))
    for d in sorted(map(float, rec['cases'])):
        if f'OT_NATIVE_ELECTRICAL_END {d}' not in text:
            raise ValueError('incomplete native case')
        m = re.search(r'OT_NATIVE_FINAL_D ' + re.escape(str(d)) + r' count=(\d+) worst_ps=([\d.eE+-]+) pin=(\S+)', text)
        if not m or int(m[1]) != width:
            raise ValueError('missing or incomplete actual native final D coverage')
        report = (directory / f'drv_{d}.rpt').read_text()
        sections = re.split(r'(?m)^max (slew|capacitance)\n', report)
        checks = {}
        for i in range(1, len(sections), 2):
            typ, body = sections[i:i + 2]
            violations = []
            for line in body.splitlines():
                if '(VIOLATED)' in line:
                    words = line.split()
                    violations.append(dict(pin=words[0], limit=float(words[-4]), actual=float(words[-3]), slack=float(words[-2])))
            checks[typ] = dict(violations=len(violations), worst=min(violations, key=lambda r: r['slack']) if violations else None)
        ok = not any(c['violations'] for c in checks.values())
        if not ok:
            failed = True
        if not failed:
            prefix = d
        rows.append(dict(d_um=d, native_final_D_count=int(m[1]), native_final_D_max_slew_ps=float(m[2]),
                         native_final_D_worst_pin=m[3], electrical_checks=checks, electrical_pass=ok,
                         report_sha256=digest(report.encode())))
    result = dict(schema='opentallas.relay_native_electrical_result.v1', job=rec['job'],
                  stage_sha256=digest((directory/'stage.json').read_bytes()), native_log_sha256=digest(text.encode()),
                  rows=rows, sampled_electrical_pass_prefix_um=prefix,
                  usable_as_die_reach_bound=False,
                  collector_sha256=digest(Path(__file__).read_bytes()),
                  limit_source='Actual unchanged archived SDC and loaded native standard-cell Liberty; limits recorded in each violated report',
                  scope='Actual native waveform/load and all-pin DRV replay, not full composed sender-wire-receiver TT/FF timing. No route, clock, input/output delay, exception or electrical limit changed.')
    (directory / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(cases=len(rows), sampled_electrical_pass_prefix_um=prefix,
                         first_fail=next((r for r in rows if not r['electrical_pass']), None)), indent=2))


def main():
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == 'collect':
        collect(Path(sys.argv[2]))
        return
    p = argparse.ArgumentParser(description=__doc__)
    for a in ('archive', 'run', 'views', 'out'):
        p.add_argument('--' + a, type=Path, required=True)
    p.add_argument('--cell', required=True)
    a = p.parse_args()
    stage(a.archive, a.run, a.views, a.cell, a.out)


if __name__ == '__main__':
    main()
