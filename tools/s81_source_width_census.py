#!/usr/bin/env python3
"""Elaborate a named RTL top and census actual ports; optional exact pin-contract check.
This proves source width/direction only, never native functionality or physical fit.
No guessed parameter evaluation or parsing of commented declarations is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def census(top, sources, defines=(), includes=()):
    with tempfile.TemporaryDirectory(prefix='s81-port-census-') as tmp:
        xml = Path(tmp) / 'top.xml'
        cmd = ['verilator', '--xml-only', '-Wno-fatal', '--timescale', '1ns/1ps', '--xml-output', str(xml),
               '--Mdir', str(Path(tmp) / 'obj'), '--top-module', top]
        cmd += ['-D' + d for d in defines] + ['-I' + str(p) for p in includes]
        cmd += [str(p) for p in sources]
        run = subprocess.run(cmd, text=True, capture_output=True)
        if run.returncode:
            raise RuntimeError('RTL elaboration failed:\n' + run.stdout + run.stderr)
        root = ET.parse(xml).getroot()
        types = {n.attrib['id']: n for n in root.findall('./netlist/typetable/*')}

        def width(dtype):
            t = types[dtype]
            if t.tag == 'basicdtype':
                if t.attrib.get('name') not in ('logic', 'bit', 'integer', 'int'):
                    raise ValueError('Unsupported top port basic dtype: ' + str(t.attrib))
                return abs(int(t.attrib.get('left', 0)) - int(t.attrib.get('right', 0))) + 1
            if t.tag == 'refdtype':
                return width(t.attrib['sub_dtype_id'])
            raise ValueError('Unsupported top port dtype; refuse guessed width: ' + t.tag)

        modules = [m for m in root.findall('./netlist/module') if m.attrib.get('topModule') == '1']
        if len(modules) != 1 or modules[0].attrib.get('origName') != top:
            raise ValueError('Elaborated top identity mismatch')
        ports = {v.attrib['origName']: dict(bits=width(v.attrib['dtype_id']), direction=v.attrib['dir'])
                 for v in modules[0].findall('./var') if 'dir' in v.attrib}
        source_files = sorted({Path(n.attrib['filename']).resolve() for n in root.findall('./files/file')
                               if not n.attrib['filename'].startswith('<')})
        return dict(schema='opentallas.source-width-census.v1', top=top, ports=ports,
                    total_port_bits=sum(p['bits'] for p in ports.values()),
                    source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
                    defines=list(defines), elaboration_diagnostics=run.stderr,
                    qualification='elaborated source port widths only; physical and native behavior unqualified')


def compare(actual, expected):
    mismatches = []
    for name in sorted(set(actual) | set(expected)):
        a, e = actual.get(name), expected.get(name)
        if a is None or e is None:
            mismatches.append(dict(port=name, actual=a, expected=e))
        else:
            if isinstance(e, int):
                e = dict(bits=e)
            if any(a.get(k) != e[k] for k in ('bits', 'direction') if k in e):
                mismatches.append(dict(port=name, actual=a, expected=e))
    return mismatches


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--top', required=True)
    ap.add_argument('--src', type=Path, action='append', required=True)
    ap.add_argument('--define', action='append', default=[])
    ap.add_argument('--include', type=Path, action='append', default=[])
    ap.add_argument('--expected', type=Path, help='JSON ports map; exact names and widths required')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    result = census(args.top, args.src, args.define, args.include)
    if args.expected:
        expected = json.loads(args.expected.read_text())
        result['contract_mismatches'] = compare(result['ports'], expected.get('ports', expected))
        result['contract_match'] = not result['contract_mismatches']
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end='')
    return int(result.get('contract_match') is False)


if __name__ == '__main__':
    raise SystemExit(main())
