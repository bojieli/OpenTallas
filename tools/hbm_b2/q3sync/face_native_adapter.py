#!/usr/bin/env python3
"""Expose qualified native q3 ports around exact physical one-clock face shells.

This is a programme simulation adapter. Existing face-shell registers remain in
the datapath; no latency compensation, tie-off or clock duplication is inserted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def emit(face_dir, adapter_dir, assembly, testbench, out):
    faces = json.loads((face_dir / 'face_sources.json').read_text())
    manifest = json.loads((adapter_dir / 'manifest.json').read_text())
    qualification = json.loads((adapter_dir / 'qualification.json').read_text())
    if (qualification['status'] != 'PASS_CLOCK_ADAPTER' or
            qualification['manifest_sha256'] != sha(adapter_dir / 'manifest.json') or
            qualification['native']['clock_bits'] != 147):
        raise ValueError('native clock alias proof is missing')
    if set(faces['cores']) != {'body', 'edge', 'vm', 'reduce', 'ring_ag'}:
        raise ValueError('all five physical views are required')
    for name, digest in faces['files'].items():
        if sha(face_dir / name) != digest:
            raise ValueError('face source changed: ' + name)
    text, wrappers, result = assembly.read_text(), [], {}
    compact = re.sub(r'\s+', '', text)
    tb_compact = re.sub(r'\s+', '', testbench.read_text())
    for port, connection in manifest['native_clock_bindings'].items():
        expected = '.' + port + '(' + re.sub(r'\s+', '', connection) + ')'
        if tb_compact.count(expected) != 1:
            raise ValueError('programme testbench changes qualified clock alias: ' + port)
    for core, face in faces['cores'].items():
        original = manifest['cores'][core]
        for clock in original['clocks']:
            expected = '.' + clock['name'] + '(' + re.sub(r'\s+', '', clock['native_connection']) + ')'
            if compact.count(expected) != 1:
                raise ValueError('assembly changes qualified clock source: ' + clock['name'])
        profile = face['profile']
        if profile.get('common_clock_adapter', {}).get('manifest_sha256') != sha(adapter_dir / 'manifest.json'):
            raise ValueError('face view does not use the selected qualified clock adapter')
        if face['clock'] != 'clk' or face['widths'].get('clk') != 1:
            raise ValueError('face clock must be scalar clk')
        top = original['top']
        name = top + '__physical_faces'
        # Preserve native nonclock directions and widths; native clock aliases
        # are proven equal at the assembly by the qualification above.
        ports = [(p['name'], p['direction'], p['width']) for p in original['data_ports']]
        ports += [(p['name'], 'input', p['width']) for p in original['clocks']]
        if len({p[0] for p in ports}) != len(ports):
            raise ValueError('duplicate native ABI port')
        pmap = profile.get('canonical_pin_map', {}).get('map')
        if pmap is None:
            pmap = {p: {p: w} for p, _, w in ports if p not in {c['name'] for c in original['clocks']}}
            pmap['clk'] = {'clk': 1}
        native = {p: (d, w) for p, d, w in ports}
        connected, conns = set(), []
        clock = original['clocks'][0]
        clock_expr = clock['name'] + ('[0]' if clock['width'] > 1 else '')
        for alias, width in face['widths'].items():
            if alias == 'clk':
                conns.append('.clk(' + clock_expr + ')')
                continue
            target = pmap.get(alias, {})
            if len(target) != 1:
                raise ValueError('ambiguous native data alias: ' + alias)
            port, mapped_width = next(iter(target.items()))
            if (port not in native or native[port] != (face['dirs'][alias], width) or
                    mapped_width != width or port in connected):
                raise ValueError('changed native data ABI: ' + alias)
            connected.add(port)
            conns.append('.' + alias + '(' + port + ')')
        if connected != {p['name'] for p in original['data_ports']}:
            raise ValueError('missing native data/reset ports')
        decls = [d + ' wire ' + (f'[{w-1}:0] ' if w > 1 else '') + p for p, d, w in ports]
        wrappers.append('module ' + name + '(\n  ' + ',\n  '.join(decls) + '\n);\n' +
                        face['module'] + ' u_physical(\n  ' + ',\n  '.join(conns) + '\n);\nendmodule\n')
        pattern = r'\b' + re.escape(top) + r'(?=\s+\w+\s*\()'
        text, count = re.subn(pattern, name, text)
        if count != 1:
            raise ValueError('assembly must instantiate exactly one ' + top)
        result[core] = dict(top=name, native_ports=len(ports), physical_module=face['module'],
                            physical_input_cycles=1, physical_output_cycles=1)
    if out.exists():
        raise ValueError('output exists; preserve previous attempt')
    out.mkdir(parents=True)
    (out / 'native_face_adapters.sv').write_text('\n'.join(wrappers))
    (out / 'asm_faces.sv').write_text(text)
    report = dict(status='EMITTED_UNQUALIFIED', cores=result,
                  clock_qualification_sha256=sha(adapter_dir / 'qualification.json'),
                  face_receipt_sha256=sha(face_dir / 'face_sources.json'),
                  assembly_sha256=sha(assembly), hub52_stations='EXCLUDED_NO_ABI')
    report['testbench_sha256'] = sha(testbench)
    (out / 'adapter.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ['face-dir', 'adapter-dir', 'assembly', 'testbench', 'out']:
        ap.add_argument('--' + arg, type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(emit(a.face_dir, a.adapter_dir, a.assembly, a.testbench, a.out)))
