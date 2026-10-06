#!/usr/bin/env python3
"""Extract boundary launch pins from a completed native QX10 mapped netlist.

This reads retained synthesis output only. Connectivity is not CTS timing or
receiver-load qualification; Verilog identifiers still need ODB resolution.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('netlist', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
data = args.netlist.read_bytes()
text = data.decode()
cells = {}
drivers = {}
pattern = re.compile(r'^  (\\\S+|\w+)\s+(\\\S+|\w+)\s+\(\n(.*?)^  \);', re.M | re.S)
modules = {}
for mod in re.finditer(r'^module (\\\S+|\w+)\s*\(.*?^endmodule', text, re.M | re.S):
    modules[mod[1].lstrip('\\')] = list(pattern.finditer(mod[0]))

def expand(module, path='', ports=None):
    ports = {} if ports is None else ports

    def resolve(net):
        net = net.strip()
        if net in ports:
            return ports[net]
        bit = re.fullmatch(r'(\w+)\[(\d+)\]', net)
        if bit and bit[1] in ports:
            parent = ports[bit[1]]
            if parent.startswith('{'):
                return parent[1:-1].split(',')[-1-int(bit[2])].strip()
            return parent + '[' + bit[2] + ']'
        if not path or re.match(r"\d+'", net):
            return net
        return '\\' + path + '/' + net.lstrip('\\')

    for match in modules[module]:
        master, identifier, body = match.groups()
        master = master.lstrip('\\')
        name = (path + '/' if path else '') + identifier.lstrip('\\')
        pins = {p: resolve(n) for p, n in re.findall(r'\.(\w+)\((.*?)\)', body, re.S)}
        if master in modules:
            expand(master, name, pins)
        else:
            cells[name] = dict(master=master, pins=pins)

expand('ot_v41_qx10_native_parent')
for name, cell in cells.items():
    pins = cell['pins']
    for pin in ('Q', 'QN', 'Y', 'H', 'L', 'GCLK'):
        if pin in pins:
            drivers.setdefault(pins[pin], []).append((name, pin))

def starts(net, seen=None):
    seen = set() if seen is None else seen
    if net in seen:
        raise ValueError('combinational cycle at ' + net)
    result = set()
    for name, pin in drivers.get(net, []):
        cell = cells[name]
        if cell['master'].startswith(('DFF', 'TIE', 'ICG', 'ot_rom_')):
            result.add(name + '/' + pin)
        else:
            for p, upstream in cell['pins'].items():
                if p not in ('Y', 'VDD', 'VSS'):
                    result.update(starts(upstream, seen | {net}))
    return result

prefix = 'u_qx.u_e.'
gate = cells[prefix + 'g_cg.u_cg.u_icg']
assert gate['master'] == 'ICGx1_ASAP7_75t_R'
free = gate['pins']['CLK']
gated = gate['pins']['GCLK']
assert free != gated
families = {}
rails = {}
for name, cell in cells.items():
    if not cell['master'].startswith('DFF'):
        continue
    norm = name.replace('\\', '')
    family = None
    if norm.startswith('u_sp.g_bst.u_bst.g_line.line['):
        if int(re.search(r'line\[(\d+)\]', norm)[1]) >= 3260:
            family = 'D3_final'
    elif norm.startswith('u_ld.'):
        family = 'loader_free'
    elif norm.startswith(prefix + 'g_qb.g_bx.'):
        family = 'XS_gated'
    elif norm.startswith(prefix + 'g_qb.'):
        family = 'config_go_free'
    elif norm.startswith(prefix + 'g_qz_cg.'):
        family = 'gate_enable_free'
    elif '.g_mz.' in norm:
        family = 'reset_free'
    elif re.match(re.escape(prefix) + r'g_mac\[[01]\]\.o_', norm):
        family = 'result_gated'
    elif norm.startswith('u_return.u_n.'):
        family = 'return64_free'
    elif norm.startswith(('u_prv.', 'u_prd.', 'q0_')):
        family = 'root_free'
    if family:
        clock = cell['pins'].get('CLK')
        relation = 'core_clk' if clock == free else 'q_gated' if clock == gated else 'UNRESOLVED'
        entry = dict(instance=name, **cell, clock_relation=relation)
        if family in ('XS_gated', 'config_go_free', 'loader_free', 'result_gated'):
            entry['D_startpoints'] = sorted(starts(cell['pins']['D']))
        families.setdefault(family, []).append(entry)
    if any(x in norm for x in ('g_qo.ff_d', 'g_qo.g_qyf.ffq', 'g_qyb.bkf_r')) or norm == prefix + 'fault$_DFF_PN0_':
        rails[name] = dict(**cell, D_startpoints=sorted(starts(cell['pins']['D'])))

go_name = prefix + 'g_qb.b_go$_DFF_PN0_'
go_starts = sorted(starts(cells[go_name]['pins']['D']))
assert any('u_ld.act' in name for name in go_starts), go_starts
assert any('u_sp.g_bst.u_bst.g_line.line' in name for name in go_starts), go_starts
macros = {n: c for n, c in cells.items() if c['master'] == 'ot_rom_4096x274_m8'}
assert len(macros) == 4
assert all(c['pins']['clk'] == gated for c in macros.values())
assert len(families['D3_final']) == 1630
assert families['XS_gated']
assert families['result_gated']
assert all(c['clock_relation'] == 'q_gated' for c in families['XS_gated'])
assert len(rails) == 5, list(rails)
assert all(c['pins']['CLK'] == free for c in rails.values())
assert all(c['D_startpoints'] and not all('TIE' in cells[n.rsplit('/', 1)[0]]['master'] for n in c['D_startpoints']) for c in rails.values())

record = dict(schema='opentallas.qx10.native.mapped_boundary.v1',
              source_netlist=str(args.netlist), source_netlist_sha256=hashlib.sha256(data).hexdigest(),
              engine_reference='0032b735573af2d24416eee1cf5911c0ac99ff5d',
              loader_sha256='75b916ee433eae2293d1d478909eb513ca89db7cac3c385425c9a54379536ea3',
              gate=gate, gate_enable_startpoints=sorted(starts(gate['pins']['ENA'])),
              mapped_named_family_counts={k: len(v) for k, v in families.items()}, families=families,
              count_scope='Named cells after synthesis merging; counts are not complete logical-port widths. ODB pin-name resolution remains pending.',
              source_boundary_widths=dict(XS=549, result=126),
              go_capture=dict(instance=go_name, **cells[go_name], launch_startpoints=go_starts),
              retained_protective_rails=rails, fq_mapped_alias=prefix+'fault$_DFF_PN0_',
              weight_macros=macros,
              configuration_macro_receivers={n: c for n, c in cells.items() if c['master'] == 'ot_rom_4096x72_m8'},
              cfg_rom_address_receiver_load_qualified=False,
              missing_input_clocks=True, ODB_pin_resolution=False, CTS=False, SPEF=False, SSFF=False,
              scope='Completed technology-mapped native connectivity; no physical-clock arrival, sensitization, external receiver load or full-field qualification.')
assert record['gate_enable_startpoints'], 'missing actual registered gate enable'
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({k: v for k, v in record.items() if k not in ('families', 'weight_macros', 'retained_protective_rails')}, indent=2))
