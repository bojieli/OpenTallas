#!/usr/bin/env python3
"""Read-only audit of clock ports accidentally selected by generic pin registers.

Reads immutable kit/SDC blobs at --commit, without changing kits or the live gate
helpers. The result is a planned-wrapper diagnostic; an actual synthesis table
and wrapped RTL bench remain necessary to qualify a correction. Unsupported Tcl
clock expressions are reported as unresolved, never treated as proof of safety.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
GET_PORTS = re.compile(r'\[get_ports\s+(?:-\w+\s+)*(?:\{([^}]+)\}|"([^"]+)"|([^\]\s]+))\s*\]')


def base(port):
    return re.sub(r'\[\d+(?::\d+)?\]$', '', port)


def clock_ports(text):
    ports, unresolved = set(), []
    for line in text.replace('\\\n', ' ').splitlines():
        if line.lstrip().startswith('#') or not re.search(r'\bcreate_(?:generated_)?clock\b', line):
            continue
        matches = list(GET_PORTS.finditer(line))
        if 'get_ports' in line and not matches:
            unresolved.append(line)
        for match in matches:
            for port in next(g for g in match.groups() if g is not None).split():
                if re.search(r'[$*?\\]', port):
                    unresolved.append(line)
                else:
                    ports.add(base(port))
    return ports, unresolved


def audit(spec, env, read):
    if not re.search(r'\bOT_PIN_REGS=1\b', env):
        return None
    match = re.search(r'\bOT_PIN_REGS_CLOCK=([^\s\x27"\)]+)', env)
    if not match:
        raise ValueError('enabled generic wrapper has no clock assignment')
    passthrough = {base(p) for p in match[1].split(',')}
    exclude = spec.get('pin_regs', {}).get('exclude', '')
    declared = {base(spec['clock_port'])}
    declared.update(base(p) for p in spec.get('clock_ports', []))
    unresolved, missing = [], []
    for path in spec.get('sdc_extra', []):
        text = read(path)
        if text is None:
            missing.append(path)
            continue
        found, unknown = clock_ports(text)
        declared.update(found)
        unresolved.extend(dict(path=path, command=x) for x in unknown)
    bad = sorted(p for p in declared if p not in passthrough and not (exclude and re.search(exclude, p)))
    return dict(top=spec['top'], clock_ports=sorted(declared), wrapper_clock_passthrough=sorted(passthrough),
                exclude=exclude, planned_registered_clock_ports=bad,
                unresolved_clock_commands=unresolved, missing_sdc=missing,
                status='CLOCK_SELECTED_AS_DATA' if bad else 'UNRESOLVED' if unresolved or missing else 'NO_LITERAL_CLOCK_REGISTRATION_FOUND',
                scope='Immutable planned-wrapper diagnostic; no functional/native qualification')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--commit', default='HEAD')
    ap.add_argument('--kit', action='append', help='Repo-relative kit directory; default all ref_tile kits')
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    ref = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', args.commit], text=True).strip()
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', ref,
                                     'physical/ref_tile'], text=True).splitlines()
    specs = [p for p in paths if p.endswith('/spec.json') and (not args.kit or str(Path(p).parent) in args.kit)]
    # One batch fetch avoids a subprocess per blob on a large kit registry.
    wanted = set(specs) | {str(Path(p).with_name('kit.env')) for p in specs}
    def batch(names):
        names = sorted(names)
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '--batch'],
                                      input=''.join(ref+':'+n+'\n' for n in names).encode())
        result, pos = {}, 0
        for name in names:
            end = raw.index(b'\n', pos); header = raw[pos:end].split(); pos = end+1
            if header[-1] == b'missing':
                result[name] = None
            else:
                size = int(header[-1]); result[name] = raw[pos:pos+size].decode(); pos += size+1
        return result
    blobs = batch(wanted)
    sdcs = {s for p in specs for s in json.loads(blobs[p]).get('sdc_extra', [])}
    blobs.update(batch(sdcs))
    records = []
    for path in specs:
        env = blobs.get(str(Path(path).with_name('kit.env')))
        if env is None:
            continue
        result = audit(json.loads(blobs[path]), env, blobs.get)
        if result:
            records.append(dict(kit=str(Path(path).parent), **result))
    report = dict(source_commit=ref, kits_examined=len(specs), pin_registered_kits=len(records), records=records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(kits_examined=len(specs), pin_registered_kits=len(records),
                          clock_selected_as_data=sum(bool(r['planned_registered_clock_ports']) for r in records),
                          unresolved=sum(bool(r['unresolved_clock_commands'] or r['missing_sdc']) for r in records))))


if __name__ == '__main__':
    main()
