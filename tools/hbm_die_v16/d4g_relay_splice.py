#!/usr/bin/env python3
"""H-D4G3b 10-18: apply a relay layer (relay_layer_d4f.py output: instances / clocks / edges / relay_splice_v2) to a FINAL
contract (after the d4g GEN1 post-layers d4g_layers/l*.py), at contract level -- the same bit-level splice
full_die_v16 uses for soft-parent buses (soft_relay_splice): every listed load bit must be driven by its listed driver
bit in this contract (else a problem: the station list is stale), is re-driven by its last station, and the station /
forwarded-clock edges are bound.  Relay ports come from the RTL (full_die_v16.Rtl, the strict bind's parser); relay
clock/reset inputs not driven by a forwarded-clock edge bind to the domain root (hb_ckgen pll_<d> / por_<d>), as
full_die_v16 does.  Rows the layer could not splice are listed; the run fails on any problem.
    d4g_relay_splice.py IN_contract.json[.gz] LAYER.json.gz OUT_contract.json --report R.json
"""
import argparse, collections, gzip, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'hbm_die_v15'))
import full_die_v16 as F  # noqa: E402


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def detach_reset_inputs(c, layer, problems):
    """Replace only declared reset forest inputs; reject partial-bit or stale replacements."""
    targets = {tuple(p) for p in layer.get('reset_forest_ports', [])}
    if not targets and not layer.get('drop_edges'):
        return
    replacement = collections.defaultdict(set)
    ports = {n: v['ports'] for n, v in c['instances'].items()}
    for e in layer['edges']:
        di, dp, lo, hi = F.rng(e['dst'], ports)
        if (di, dp) in targets:
            overlap = replacement[(di, dp)].intersection(range(lo, hi))
            if overlap:
                problems.append(f'reset forest duplicate drive {di}.{dp}: bits {sorted(overlap)[:8]}')
            replacement[(di, dp)].update(range(lo, hi))
    old = {(x['instance'], x['port']): x for x in c['clock_resets'] if x['kind'] == 'reset'}
    for n, p in sorted(targets):
        v = old.get((n, p))
        if v is None or v['source'][0] != 'hb_ckgen':
            problems.append(f'reset forest stale target {n}.{p}: no hb_ckgen reset binding')
            continue
        expected = set(range(ports[n][p]['bits']))
        if replacement[(n, p)] != expected:
            problems.append(f'reset forest incomplete target {n}.{p}: expected {len(expected)} bits, '
                            f'got {len(replacement[(n, p)])}')
    c['clock_resets'] = [x for x in c['clock_resets'] if (x['instance'], x['port']) not in targets]
    drop = {tuple(d) for d in layer.get('drop_edges', [])}
    removed = set()
    edges = []
    for e in c['edges']:
        key = (e['source'][0], e['source'][1], e['sink'][0])
        if key in drop:
            if e['source'][1] != 'bridge_rst_n':
                problems.append(f'reset forest refuses non-reset drop {key}')
                edges.append(e)
            else:
                removed.add(key)
        else:
            edges.append(e)
    problems.extend(f'reset forest stale drop {key}' for key in sorted(drop - removed))
    c['edges'] = edges


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('contract'); ap.add_argument('layer'); ap.add_argument('out')
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = load(a.contract); L = load(a.layer); problems = []
    I = c['instances']; rtl = F.Rtl()
    for x in L['instances']:
        n = x['name']
        if n in I:
            problems.append(f'relay instance {n} already in the contract'); continue
        d = {k: x.get(k) for k in ('master', 'source', 'params', 'slot', 'owner', 'note', 'rtl_deps')}
        d['params'] = d['params'] or {}; d['rtl_deps'] = d['rtl_deps'] or []; d['region'] = L['region']
        d['ports'] = rtl.ports(x['master'], x['source'], d['params'])
        I[n] = d
        c['masters'][x['master']] = c['masters'].get(x['master'], 0) + 1
    detach_reset_inputs(c, L, problems)
    ports = {n: v['ports'] for n, v in I.items()}
    drv = {}
    for e in c['edges']:
        si, sp, slo, shi = e['source']; di, dp, dlo, dhi = e['sink']
        for k in range(shi - slo):
            drv[(di, dp, dlo + k)] = (si, sp, slo + k)
    n_edges0 = len(c['edges'])
    E = list(c['edges'])
    F.soft_relay_splice(L.get('relay_splice_v2', []), ports, drv, E, problems)
    # forwarded-clock chains (src/dst, whole port when no range)
    for e in L['edges']:
        si, sp, slo, shi = F.rng(e['src'], ports); di, dp, dlo, dhi = F.rng(e['dst'], ports)
        for k in range(shi - slo):
            if (di, dp, dlo + k) in drv:
                problems.append(f'clock chain {di}.{dp}[{dlo + k}] already driven'); break
            drv[(di, dp, dlo + k)] = (si, sp, slo + k)
        E.append(dict(name=e.get('name') or f'{si}__{sp}__{di}__{dp}', bits=shi - slo, source=[si, sp, slo, shi],
                      sink=[di, dp, dlo, dhi], clock=e.get('clock'), ready_or_credit=False, allowed_exception=None,
                      basis=e.get('basis', ''), region=L['region']))
    c['edges'] = E
    ck = 'hb_ckgen'
    for x in L['clocks']:
        i, p, dm, kind = x['inst'], x['port'], x['domain'], x['kind']
        if (i, p, 0) in drv:
            continue
        src = F.DOM[dm][0 if kind == 'clock' else 1]
        bits = ports[i][p]['bits']
        for b in range(bits):
            drv[(i, p, b)] = (ck, src, 0)
        c['clock_resets'].append(dict(instance=i, port=p, bits=bits, domain=dm, kind=kind, source=[ck, src],
                                      note='relay layer ' + L['region']))
    for s in L.get('straps', []):
        c['straps'].append(s)
        for b in range(s.get('lo', 0), s.get('hi', ports[s['inst']][s['port']]['bits'])):
            drv[(s['inst'], s['port'], b)] = ('STRAP', s['value'], b)
    # HBM-LANDING: landing fault outputs -> die status pins (relay_layer_d4f.py --land --land-fault pins)
    for x in L.get('die_pins', []):
        c.setdefault('die_pins', []).append(x)
    c['gaps'] = list(c.get('gaps') or []) + list(L.get('gaps') or [])
    # every relay input bit driven
    und = []
    for x in L['instances']:
        n = x['name']
        for p, d in ports[n].items():
            if d['direction'] == 'input' and any((n, p, b) not in drv for b in range(d['bits'])):
                und.append(f'{n}.{p}')
    if und:
        problems.append(f'{len(und)} relay input ports not fully driven, e.g. {und[:5]}')
    c.setdefault('notes', [])
    note = (f"d4g relay splice (d4g_relay_splice.py): layer {L['region']} ({L.get('basis_commit', '')}): "
            f"{len(L['instances'])} relay tiles, {len(L.get('relay_splice_v2', []))} buses, edges {n_edges0} -> {len(E)}")
    if isinstance(c['notes'], list):
        c['notes'].append(note)
    else:
        c['notes'] = str(c['notes']) + ' | ' + note
    c['summary']['instances'] = len(I)
    rep = dict(layer=a.layer, relay_instances=len(L['instances']), buses=len(L.get('relay_splice_v2', [])),
               edges_before=n_edges0, edges_after=len(E), masters=dict(collections.Counter(x['master'] for x in L['instances'])),
               problems=problems)
    json.dump(rep, open(a.report, 'w'), indent=1)
    if problems:
        print('RELAY_SPLICE FAIL', len(problems)); [print(' ', p[:300]) for p in problems[:20]]; sys.exit(1)
    op = gzip.open(a.out, 'wt') if a.out.endswith('.gz') else open(a.out, 'w')
    json.dump(c, op)
    op.close()
    print('RELAY_SPLICE PASS tiles', len(L['instances']), 'buses', len(L.get('relay_splice_v2', [])), 'edges', n_edges0, '->', len(E))


if __name__ == '__main__':
    main()
