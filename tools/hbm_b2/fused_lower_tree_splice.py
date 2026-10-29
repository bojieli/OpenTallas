#!/usr/bin/env python3
"""HBM-BIND-6: apply / prove the opt-in lower FUSED tree (fused_lower_tree.py) on an elaborated as-built Yosys JSON.

  splice BASE.json OUT.json RECEIPT.json   add the 2 x (16 lanes + 14 tnodes) leaf cells to the native top exactly as
        current_native_top.py --fused-lower-tree composes them (same compose_side()), without re-elaborating the die (a
        re-elab renumbers Yosys primitives die-wide; HBM-BIND-5 splice_qhub precedent).  n4 ua/ub move from their
        native_required__ top ports to the n3 outputs; n4 da/db stop being top outputs; new obligations become top input
        ports, unconsumed lane VM outputs top output ports; ot_hnx_fused_lane is added as a blackbox leaf stub.  Every
        other top cell, every other module, every existing net bit is unchanged (checked, fail closed).
  prove REF.json SPLICED.json REPORT.json [--mutant swap_2_4]
        bit-level structural equivalence of the composed FUSED tree against the Yosys elaboration of the reference
        integration ot_hnx_fused_tree_top (N4EXT = 1): for every lane / tnode / root data input bit (lane dn_*, r_*, lid;
        node ua, ub, dn; root up_nw/up_ne <-> hub uq0/uq2) the driver (instance, port, bit) or constant must be equal under
        the instance-name map, with the reference's ot_hnx_fused_link relays (pure fixed delays = die stations) read as
        wires.  Excluded and listed: clk (must be the root's clock), rst_n, pad_k/pad_b straps, lane rr_* (reference top inputs; native obligations).
        --mutant applies the mutant to the composition in memory before comparing (must FAIL).
"""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fused_lower_tree as F  # noqa: E402

TOP = 'hbm_current_native_top'
CLOCK = 'hb_ckgen__pll_stream'
LANE_PORTS = dict(clk=('input', 1), rst_n=('input', 1), lid=('input', 5), rq_v=('output', 1), rq_s=('output', 16),
                  rr_v=('input', 1), rr_d=('input', 256), wq_v=('output', 1), wq_s=('output', 16), wq_d=('output', 256),
                  dn_v=('input', 1), dn_op=('input', 3), dn_x=('input', 8), dn_d=('input', 128), r_v=('input', 1),
                  r_d=('input', 32), up_v=('output', 1), up_t=('output', 1), up_x=('output', 10), up_d=('output', 256),
                  fin=('output', 1), flt=('output', 1))
LANE_DEFAULTS = dict(D=5120, KX=4, RR=10, MUT=0)


def b32(v):
    return format(v, '032b')


def params(text):
    return {k: b32(int(v)) for k, v in re.findall(r'\.(\w+)\((\d+)\)', text)}


def composition(mutant=None):
    obligations, insts, n4 = [], {}, {}

    def required(name, port, width, reason):
        net = f'native_required__{name}__{port}'
        obligations.append(dict(instance=name, port=port, net=net, width=width, reason=reason))
        return dict(direction='input', segments=[('n', net, 0, width - 1)])

    def output(name, port, width):
        return dict(direction='output', width=width, segments=[('n', f'{name}__{port}', 0, width - 1)])
    for side in F.SIDES:
        i, n4[side] = F.compose_side(side, [('n', CLOCK, 0, 0)], required, output, mutant=mutant)
        insts.update(i)
    return insts, n4, obligations


def splice(B, mutant=None):
    T = B['modules'][TOP]
    before = {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for k, v in B['modules'].items()}
    old_cells = copy.deepcopy(T['cells'])
    used = set()
    for n in T['netnames'].values():
        used.update(b for b in n['bits'] if isinstance(b, int))
    nxt = [max(used) + 1]

    def alloc(w):
        bits = list(range(nxt[0], nxt[0] + w))
        nxt[0] += w
        return bits
    insts, n4, obligations = composition(mutant)
    nets = {}
    for name, o in insts.items():
        for p, spec in o['ports'].items():
            if spec['direction'] == 'output':
                net = spec['segments'][0][1]
                assert net not in T['netnames'] and net not in nets, net
                nets[net] = alloc(spec['width'])
    for ob in obligations:
        assert ob['net'] not in T['netnames'], ob['net']
        nets[ob['net']] = alloc(ob['width'])
        T['ports'][ob['net']] = dict(direction='input', bits=nets[ob['net']])
    assert T['cells']['u_mu_fused_n4_nw']['connections']['clk'] == T['netnames'][CLOCK]['bits']

    def bits_of(segments):
        out = []
        for seg in segments:
            if seg[0] == 'c':
                out += list(format(seg[2], f'0{seg[1]}b')[::-1])
            else:
                _, net, lo, hi = seg
                src = nets[net] if net in nets else T['netnames'][net]['bits']
                out += src[lo:hi + 1]
        return out
    readers = set()
    for name, o in insts.items():
        conns, dirs = {}, {}
        for p, spec in o['ports'].items():
            dirs[p] = spec['direction']
            conns[p] = nets[spec['segments'][0][1]] if spec['direction'] == 'output' else bits_of(spec['segments'])
            if spec['direction'] == 'input':
                readers.update(seg[1] for seg in spec['segments'] if seg[0] == 'n')
        T['cells'][name] = dict(hide_name=0, type=o['master'], parameters=params(o['params']), attributes={},
                                port_directions=dirs, connections=conns)
    for side in F.SIDES:
        readers.update(seg[1] for spec in n4[side].values() for seg in spec['segments'] if seg[0] == 'n')
    removed_ports, demoted = [], []
    for side in F.SIDES:
        c = T['cells'][f'u_mu_fused_n4_{side}']
        for p in ('ua', 'ub'):
            old = f'native_required__u_mu_fused_n4_{side}__{p}'
            assert c['connections'][p] == T['ports'][old]['bits']
            c['connections'][p] = bits_of(n4[side][p]['segments'])
            del T['ports'][old]
            removed_ports.append(old)
        for p in ('da', 'db'):
            net = f'u_mu_fused_n4_{side}__{p}'
            assert T['ports'][net]['direction'] == 'output' and net in readers
            del T['ports'][net]
            demoted.append(net)
    # removed port bits must have no remaining user anywhere in the top
    gone = {b for side in F.SIDES for p in ('ua', 'ub') for b in old_cells[f'u_mu_fused_n4_{side}']['connections'][p]}
    for n, c in T['cells'].items():
        for bs in c['connections'].values():
            assert not gone.intersection(b for b in bs if isinstance(b, int)), n
    for p in [p for p in removed_ports]:
        del T['netnames'][p]
    exposed = []
    for net, bits in nets.items():
        T['netnames'][net] = dict(hide_name=0, bits=bits, attributes={})
        if not net.startswith('native_required__') and net not in readers:
            T['ports'][net] = dict(direction='output', bits=bits)
            exposed.append(net)
    if 'ot_hnx_fused_lane' not in B['modules']:
        ports, nn, b = {}, {}, 2
        for p, (d, w) in LANE_PORTS.items():
            ports[p] = dict(direction=d, bits=list(range(b, b + w)))
            nn[p] = dict(hide_name=0, bits=ports[p]['bits'], attributes={})
            b += w
        B['modules']['ot_hnx_fused_lane'] = dict(attributes=dict(blackbox=b32(1)),
                                                 parameter_default_values={k: b32(v) for k, v in LANE_DEFAULTS.items()},
                                                 ports=ports, cells={}, netnames=nn)
    for name, c in T['cells'].items():
        if c['type'] == 'ot_hnx_fused_lane':
            assert {p: (d, len(c['connections'][p])) for p, d in c['port_directions'].items()} == LANE_PORTS, name
    after = {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for k, v in B['modules'].items()}
    changed = sorted(k for k in before if before[k] != after[k])
    assert changed == [TOP], changed
    same = [n for n in old_cells if n not in ('u_mu_fused_n4_nw', 'u_mu_fused_n4_ne')]
    assert all(T['cells'][n] == old_cells[n] for n in same)
    return dict(schema='hbm.bind6.fused_lower_tree_splice.v1', added_cells=len(insts),
                lanes=sum(o['master'] == 'ot_hnx_fused_lane' for o in insts.values()),
                tnodes=sum(o['master'] == 'ot_hnx_fused_tnode' for o in insts.values()),
                changed_cells=['u_mu_fused_n4_nw', 'u_mu_fused_n4_ne'], other_top_cells_identical=len(same),
                other_modules_identical=len(before) - 1, new_modules=[m for m in after if m not in before],
                removed_ports=removed_ports, demoted_outputs=demoted, new_input_ports=len(obligations),
                new_output_ports=len(exposed), obligations=obligations, mutant=mutant)


def graph(mod, link=lambda t: False):
    drv = {}
    for n, c in mod['cells'].items():
        for p, bs in c['connections'].items():
            if c['port_directions'][p] == 'output':
                for i, b in enumerate(bs):
                    if isinstance(b, int):
                        drv[b] = (n, p, i)
    for p, v in mod['ports'].items():
        if v['direction'] == 'input':
            for i, b in enumerate(v['bits']):
                drv[b] = ('<top>', p, i)

    def res(b, depth=0):
        if isinstance(b, str):
            return ('const', b)
        d = drv.get(b, ('undriven',))
        if d[0] in mod['cells'] and link(mod['cells'][d[0]]['type']):
            assert d[1] == 'q' and depth < 64
            return res(mod['cells'][d[0]]['connections']['d'][d[2]], depth + 1)
        return d
    return res


def ref_names():
    m = {}
    for gl in range(32):
        m[f'g_ln[{gl}].u_l'] = F.lane(F.SIDES[gl // 16], gl % 16)
    for q in range(4):
        side, h = F.SIDES[q // 2], q % 2
        for g in range(4):
            m[f'g_q[{q}].g_n1[{g}].u_n'] = f'u_mu_fused_n1_q{h}_{g}_{side}'
        for r, n in (('u_n2l', 'n2L'), ('u_n2r', 'n2R'), ('u_n3', 'n3')):
            m[f'g_q[{q}].{r}'] = f'u_mu_fused_{n}_q{h}_{side}'
    m['g_n4.u_n4a'], m['g_n4.u_n4b'], m['u_hub'] = 'u_mu_fused_n4_nw', 'u_mu_fused_n4_ne', 'u_mu_fused_root'
    return m


HUB_PORT = dict(uq0='up_nw', uq2='up_ne', dq0='down_nw', dq2='down_ne')
SKIP = {'clk', 'rst_n', 'pad_k', 'pad_b', 'rr_v', 'rr_d'}


def prove(R, S):
    rt = next(v for k, v in R['modules'].items() if k.endswith('ot_hnx_fused_tree_top'))
    st = S['modules'][TOP]
    rres = graph(rt, link=lambda t: t.endswith('ot_hnx_fused_link'))
    sres = graph(st)
    names = ref_names()
    checked, bad, excluded = 0, [], {}

    def mp(d):
        if d[0] in names:
            n = names[d[0]]
            return (n, HUB_PORT.get(d[1], d[1]) if n == 'u_mu_fused_root' else d[1], d[2])
        return d
    for rn, sn in names.items():
        rc, sc = rt['cells'][rn], st['cells'][sn]
        for p, rbs in rc['connections'].items():
            if rc['port_directions'][p] != 'input':
                continue
            sp = HUB_PORT.get(p, p) if sn == 'u_mu_fused_root' else p
            if rn == 'u_hub' and p not in HUB_PORT:
                excluded.setdefault('hub_' + p, 0)
                excluded['hub_' + p] += len(rbs)
                continue
            if p in SKIP:
                # composed side must be a top-level input (never tied) for these excluded pins
                clk0 = sres(st['cells']['u_mu_fused_root']['connections']['clk'][0])
                for b in sc['connections'][sp]:
                    d = sres(b)
                    if (p == 'clk' and d != clk0) or (p != 'clk' and d[0] != '<top>'):
                        bad.append((sn, sp, 'excluded pin: clk must be the root clock, others a top input', d))
                excluded[p] = excluded.get(p, 0) + len(rbs)
                continue
            sbs = sc['connections'][sp]
            if len(sbs) != len(rbs):
                bad.append((sn, sp, 'width', len(rbs), len(sbs)))
                continue
            for i, (rb, sb) in enumerate(zip(rbs, sbs)):
                checked += 1
                a, b = mp(rres(rb)), sres(sb)
                if a != b:
                    bad.append((sn, sp, i, a, b))
    return dict(schema='hbm.bind6.fused_lower_tree_proof.v1', instances=len(names), checked_bits=checked,
                mismatches=len(bad), examples=bad[:12], excluded_bits=excluded,
                verdict='PASS' if not bad and checked else 'FAIL')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    a1 = sp.add_parser('splice')
    for x in ('base', 'out', 'receipt'):
        a1.add_argument(x, type=Path)
    a2 = sp.add_parser('prove')
    for x in ('ref', 'spliced', 'report'):
        a2.add_argument(x, type=Path)
    a2.add_argument('--mutant')
    a = ap.parse_args()
    if a.cmd == 'splice':
        B = json.loads(a.base.read_text())
        rec = splice(B)
        rec.update(base=str(a.base), base_sha256=hashlib.sha256(a.base.read_bytes()).hexdigest())
        a.out.write_text(json.dumps(B))
        rec['out_sha256'] = hashlib.sha256(a.out.read_bytes()).hexdigest()
        a.receipt.write_text(json.dumps(rec, indent=1) + '\n')
        print(json.dumps({k: rec[k] for k in ('added_cells', 'lanes', 'tnodes', 'other_top_cells_identical', 'new_input_ports', 'new_output_ports')}))
    else:
        R, S = json.loads(a.ref.read_text()), json.loads(a.spliced.read_text())
        if a.mutant:
            # rebuild the composition with the mutant on a fresh copy of the spliced netlist's base cells
            T = S['modules'][TOP]
            insts, n4, _ = composition(a.mutant)
            good, _, _ = composition()
            # remap: mutant connections expressed in the spliced netlist's bits
            net_bits = {n: v['bits'] for n, v in T['netnames'].items()}

            def bits(segs):
                out = []
                for s in segs:
                    out += list(format(s[2], f'0{s[1]}b')[::-1]) if s[0] == 'c' else net_bits[s[1]][s[2]:s[3] + 1]
                return out
            for name, o in insts.items():
                for p, spec in o['ports'].items():
                    if spec['direction'] == 'input':
                        T['cells'][name]['connections'][p] = bits(spec['segments'])
        rep = prove(R, S)
        rep.update(ref=str(a.ref), spliced=str(a.spliced), mutant=a.mutant)
        a.report.write_text(json.dumps(rep, indent=1, default=str) + '\n')
        print(json.dumps({k: rep[k] for k in ('verdict', 'instances', 'checked_bits', 'mismatches', 'excluded_bits')}))
        sys.exit(0 if (rep['verdict'] == 'PASS') != bool(a.mutant) else 1)


if __name__ == '__main__':
    main()
