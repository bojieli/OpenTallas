"""Source-bound directed SU split census of the exact s8 wires-only parent.

No synthesis, timing or physical qualification. Reject unsupported expressions rather
than guessing connectivity; expose shared inputs separately from driven crossings.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/landed_parent'))
import lp

FILES = ['rtl/qwen_dv/s5/s8/qfd_dv_s8_flat.sv',
         'rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv',
         'rtl/qwen_dv/s5/s8/qfd_dv_s8_suvm_rp1.sv',
         'rtl/qwen_dv/s5/qfd_dv_s5_red2_leaf.sv']
sources = {f: lp.preprocess((ROOT / f).read_text(), []) for f in FILES}
parent = lp.parse_module(sources[FILES[0]], 'qfd_dv_s8_flat')
wires, assigns, insts = lp.parse_body(parent['body'])
widths = {k: lp.eval_width(v, parent['params']) for k, v in wires.items()}
widths.update({p['name']: lp.eval_width(p['range'], parent['params']) for p in parent['ports']})


def group(name):
    if name in ('u_suvm', 'u_red'):
        return 'su_c'
    m = re.fullmatch(r'u_lrly([0-7])', name)
    return 'su_l' + str(int(m[1]) // 4) if m else None


def bits(expr):
    m = re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?', expr)
    assert m and m[1] in widths, ('unsupported/unknown expression', expr)
    if m[2] is None:
        ids = range(widths[m[1]])
    elif m[3] is None:
        ids = [int(m[2])]
    else:
        lo, hi = sorted((int(m[2]), int(m[3])))
        ids = range(lo, hi + 1)
    assert all(0 <= i < widths[m[1]] for i in ids), expr
    return [(m[1], i) for i in ids]


outputs, inputs = collections.defaultdict(list), collections.defaultdict(list)
selected = []
for ins in insts:
    g = group(ins['inst'])
    if not g:
        continue
    matches = [s for s in sources.values() if re.search(r'\bmodule\s+' + re.escape(ins['module']) + r'\b', s)]
    assert len(matches) == 1, ins['module']
    mod = lp.parse_module(matches[0], ins['module'])
    ports = {p['name']: p for p in mod['ports']}
    selected.append(dict(inst=ins['inst'], module=ins['module'], group=g))
    for port, expr in ins['conns'].items():
        assert port in ports
        assert ports[port]['dir'] in ('in', 'out')
        sink = outputs if ports[port]['dir'] == 'out' else inputs
        for bit in bits(expr):
            sink[bit].append((g, ins['inst'], port))
assert len(selected) == 10
assert all(len(v) == 1 for v in outputs.values()), 'multiple selected-SU drivers'
flows = collections.defaultdict(set)
source_rows = collections.defaultdict(set)
for bit, drv in outputs.items():
    s, si, sp = drv[0]
    for d, di, dp in inputs.get(bit, []):
        if s != d and bit[0] not in ('ck', 'rst_n'):
            flows[(s, d)].add(bit)
            source_rows[(s, si, sp, d, di, dp)].add(bit)
common = collections.defaultdict(set)
for bit, consumers in inputs.items():
    gs = {c[0] for c in consumers}
    if {'su_l0', 'su_l1'} <= gs and bit[0] != 'ck':
        common[bit[0]].add(bit)
# Check every lane-local head/SFU endpoint as well: no additional shared
# L0/L1 signal can hide outside the relay/core interface census above.
all_lane_incidence = collections.defaultdict(set)
all_lane_instances = []
for ins in insts:
    m = re.fullmatch(r'u_(?:lrly|head|exp|rcp|rsq)([0-7])', ins['inst'])
    if not m:
        continue
    g = 'su_l' + str(int(m[1]) // 4)
    all_lane_instances.append(ins['inst'])
    for expr in ins['conns'].values():
        if re.fullmatch(r"(?:\d+)?'[sS]?[bBoOdDhH][0-9a-fA-F_xXzZ]+|\d+", expr):
            continue
        for bit in bits(expr):
            all_lane_incidence[bit].add(g)
assert len(all_lane_instances) == 40
all_shared = collections.Counter()
for (net, bit), groups in all_lane_incidence.items():
    if groups == {'su_l0','su_l1'} and net != 'ck':
        all_shared[net] += 1
assert dict(all_shared) == {'rst_n':1,'gb':500,'gv':3}, dict(all_shared)

# Exact parent aliases used by the existing region census (not new data sources).
aliases = {}
for net in ('sc_win0', 'sc_wd0'):
    match = re.search(r'\bassign\s+' + net + r'\s*=\s*([^;]+);', parent['body'])
    assert match, net
    left, right = bits(net), bits(match[1].strip())
    assert len(left) == len(right)
    aliases.update(zip(left, right))

def canonical(bit):
    return aliases.get(bit, bit)

record = json.loads((ROOT / 'physical/die_plan/qwen_compute/inputs/s8_lp_record.json').read_text())
external = []
for landing in record['landings']:
    if 'r_su' not in (landing['src_region'], landing['dst_region']):
        continue
    netbits = [canonical(x) for x in bits(landing['net'])]
    assert len(netbits) == landing['width'], landing
    split = collections.Counter()
    for bit in netbits:
        if landing['src_region'] == 'r_su':
            assert len(outputs[bit]) == 1, (landing['net'], bit)
            src_group, src_inst, src_port = outputs[bit][0]
            assert src_inst in landing['src_nodes'], (landing['net'], src_inst)
            split[(src_group, landing['dst_region'])] += 1
        else:
            targets = set()
            for reader in landing['readers']:
                inst, port = reader.split('.')
                targets.update(g for g, i, pp in inputs.get(bit, []) if i == inst and pp == port)
            assert targets, (landing['net'], bit, landing['readers'])
            for target in targets:
                split[(landing['src_region'], target)] += 1
    external.extend(dict(landing=landing['name'], net=landing['net'], src=a, dst=b, bits=n)
                    for (a,b),n in sorted(split.items()))
internal = []
for (a,b), bb in sorted(flows.items()):
    per_net = collections.Counter(net for net,i in bb)
    internal.extend(dict(src=a,dst=b,net=net,bits=n)for net,n in sorted(per_net.items()))
result = dict(scope='actual s8 parent directed SU inter-group data; no RTL/physical closure',
              sources={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES},
              selected=selected, all_lane_instances=all_lane_instances,
              all_lane_shared_signals_excluding_clock=dict(all_shared),
              directed_bits={f'{a}->{b}': len(v) for (a, b), v in sorted(flows.items())},
              common_lane_inputs_excluding_clock={n: len(v) for n, v in sorted(common.items())},
              lane_to_lane_bits=len(flows.get(('su_l0', 'su_l1'), set()) | flows.get(('su_l1', 'su_l0'), set())),
              internal=internal, external=external,
              old_cut_counts=dict(core_L0=2435,core_L1=2408,L0_L1=504,
                  meaning='undirected data totals plus one shared reset; shared input overlap is not a driven lane'),
              age_contract=dict(core_boundary='u_suvm gb/gv/lv1/pd1 are group-stage publications; VM answers retain actual VM read age',
                  lane_input='lrly control244/gv/pd1/lv1/answers delay1 then IREG1; gb low256 bypass inbound delay then IREG1',
                  lane_output='lrly head output OREG1; five read requests addRD-1=1, other outputs addRD=2',
                  plan='every new inter-partition lane uses normal source/destination boundary flops and stations; regenerate schedule from produced latency; no original cycle claim'),
              source_rows=[dict(src_group=a, src_inst=si, src_port=sp, dst_group=b, dst_inst=di, dst_port=dp,
                                bits=len(v), parent_nets=sorted({n for n, i in v}))
                           for (a, si, sp, b, di, dp), v in sorted(source_rows.items())])
assert result['directed_bits'] == {'su_c->su_l0':1531,'su_c->su_l1':1531,'su_l0->su_c':903,'su_l1->su_c':876}
assert result['common_lane_inputs_excluding_clock'] == {'gb':500,'gv':3,'rst_n':1}
assert result['lane_to_lane_bits'] == 0
external_totals = collections.Counter()
for row in external:
    external_totals[row['src'] + '->' + row['dst']] += row['bits']
result['external_directed_bits'] = dict(external_totals)
assert dict(external_totals) == {'su_l0->r_ctl':456,'su_l1->r_ctl':456,'su_c->r_ctl':93,
    'r_ctl->su_c':1655,'su_c->r_sc':57,'su_l0->r_sc':38,'su_l1->r_sc':4,
    'su_l0->r_stm':228,'su_l1->r_stm':228}
print(json.dumps(result, indent=2))
