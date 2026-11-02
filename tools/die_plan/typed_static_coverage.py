"""Default-OFF, read-only classification of TileIO declared strap captures.

This diagnostic never subtracts a timing coverage count or changes a gate. It
does not prove parent ties. It joins exact native source/SDC/pins and independently
walks each D cone; only the observed single-strap BUF-chain class is supported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_cells(text, module):
    match = re.search(r'^module\s+' + re.escape(module) + r'\s*\(', text, re.M)
    if not match:
        raise ValueError('actual declared top module missing')
    text = text[match.start():]
    text = text[:text.index('endmodule')]
    cells, drivers = {}, {}
    for match in re.finditer(r'^[ \t]+(\S+)[ \t]+(\S+)[ \t]+\((.*?)\);', text, re.M | re.S):
        master, name, body = match.groups()
        name = name.lstrip('\\')
        ports = {p: n.strip().lstrip('\\') for p, n in re.findall(r'\.(\w+)\(([^()]*)\)', body)}
        if name in cells:
            raise ValueError('duplicate native instance')
        cells[name] = dict(master=master, ports=ports)
        for port in ('Y', 'QN', 'Q'):
            if port in ports:
                drivers.setdefault(ports[port], []).append((name, port))
    return cells, drivers


def trace(cells, drivers, capture, strap):
    cell = cells.get(capture, {})
    if not re.fullmatch(r'DFF\w+_ASAP7_75t_R', cell.get('master', '')):
        raise ValueError('capture is not an actual native DFF')
    net = cell.get('ports', {}).get('D')
    if not net:
        raise ValueError('capture D disconnected')
    seen, path = set(), []
    while net != strap:
        if net in seen or len(path) > 64:
            raise ValueError('cyclic or unsupported long cone')
        seen.add(net)
        source = drivers.get(net, [])
        if len(source) != 1:
            raise ValueError('wrong strap, unknown input or multiple driver')
        name, output = source[0]
        c = cells[name]
        if (not re.fullmatch(r'BUFx\w+_ASAP7_75t_R', c['master']) or output != 'Y'
                or set(c['ports']) - {'A', 'Y', 'VDD', 'VSS'} or not c['ports'].get('A')):
            raise ValueError('dynamic, sequential or unsupported functional fanin')
        path.append(name)
        net = c['ports']['A']
    if drivers.get(strap):
        raise ValueError('declared strap has an internal native driver')
    return dict(capture=capture + '/D', launch=strap, buffer_path=path)


def classify(manifest, expected_sha256, *, enabled=False):
    if not enabled:
        return dict(status='DISABLED', coverage_gate_changed=False, parent_tie_qualified=False)
    manifest = Path(manifest)
    if sha(manifest) != expected_sha256:
        raise ValueError('caller-pinned input manifest differs')
    inputs = json.loads(manifest.read_text())
    names = ('6_final.v', 'constraint.sdc', 'straps.json', 'freeze.json', 'pins.json',
             'plan_pins.json', 'budget.json', 'config.mk', 'current_terminal.json',
             'raw_coverage_tt.log', 'raw_coverage_ff.log')
    files = {}
    for name in names:
        row = inputs[name]
        files[name] = Path(row['path'])
        if sha(files[name]) != row['sha256']:
            raise ValueError('pinned actual input changed: ' + name)
    freeze = json.loads(files['freeze.json'].read_text())
    if (freeze.get('schema') != 'opentallas.partition_freeze.v1' or freeze.get('type') != 'hd_tile'
            or freeze.get('die') != 's81_head' or freeze.get('pins_file') != 'plan_pins.json'
            or freeze.get('pins_sha256') != sha(files['plan_pins.json'])):
        raise ValueError('wrong partition or native pin/freeze context')
    declared = json.loads(files['straps.json'].read_text())['straps']
    if not {'strap_row0', 'strap_ten'} <= set(declared):
        raise ValueError('required static strap declaration absent')
    sdc = files['constraint.sdc'].read_text()
    groups = re.findall(r'^set_false_path -from \[get_ports \{([^}]+)\}\]\s*$', sdc, re.M)
    if not any({'strap_row0', 'strap_ten'} <= set(group.split()) for group in groups):
        raise ValueError('actual SDC does not declare both static false-path sources')
    mapping = {'u_core.b_en$_DFF_P_': 'strap_ten[0]'}
    mapping.update({f'u_core.row0_q[{i}]$_DFF_P_': f'strap_row0[{i}]' for i in range(17)})
    expected = {name + '/D' for name in mapping}
    for corner in ('tt', 'ff'):
        log = files['raw_coverage_' + corner + '.log'].read_text()
        matches = re.findall(r'Warning: There are (\d+) unconstrained endpoints\.\n((?:[ \t]+[^\n]+\n)+)', log)
        if len(matches) != 1:
            raise ValueError('missing or ambiguous native raw coverage report')
        count, body = matches[0]
        actual = {line.strip() for line in body.splitlines()}
        if int(count) != 18 or actual != expected or set(inputs[corner + '_native_unconstrained_endpoints']) != expected:
            raise ValueError('raw native endpoint set differs from exact typed class')
    pins = {p['name'] for p in json.loads(files['plan_pins.json'].read_text())['pins']}
    if not set(mapping.values()) <= pins:
        raise ValueError('declared strap bit absent from actual physical pin inventory')
    cells, drivers = native_cells(files['6_final.v'].read_text(), 'ot_s81hd_tile_p')
    traces = [trace(cells, drivers, capture, strap) for capture, strap in mapping.items()]
    return dict(schema='opentallas.typed_static_coverage_diagnostic.v1',
                status='DECLARED_STRAP_ONLY_NATIVE_CONES', input_manifest_sha256=expected_sha256,
                inputs_sha256={n: sha(p) for n, p in files.items()}, traces=traces,
                raw_unconstrained={'tt': 18, 'ff': 18}, raw_verdict_unchanged=True,
                coverage_gate_changed=False, parent_tie_qualified=False, source_qualified=False,
                limitation='Classification only. No parent tie proof, count subtraction, waiver or TT/FF timing pass.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest')
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--enable-diagnostic', action='store_true')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    result = classify(a.manifest, a.expected_sha256, enabled=a.enable_diagnostic)
    Path(a.out).write_text(json.dumps(result, indent=1) + '\n')
    print(result['status'])
