#!/usr/bin/env python3
"""Static tree arrival audit; no RTL simulation or timing qualification."""
import argparse, collections, functools, hashlib, json
from pathlib import Path
from extract import parse

def audit(path, node_latency=3, applied_pads=None):
    applied_pads = applied_pads or {}
    inst, bus = parse(path)
    slots = {n: dict(master=m, pins=p) for n, (m, p) in inst.items()
             if not m.startswith(('qfd_rly', 'qkd_rly'))}
    ports = collections.defaultdict(list)
    for b, d in bus.items():
        if d['cls'] == 'corridor':
            for e in d['src'] + d['dst']:
                ports[e.split('.')[0]].append(b)
    roots = [b for b, d in bus.items() if d['cls'] == 'corridor'
             and any(e.startswith('sp_vector_memory.') for e in d['src'])]
    seen, todo = set(roots), [e.split('.')[0] for b in roots for e in bus[b]['dst']]
    while todo:
        n = todo.pop()
        for b in ports[n]:
            if b in seen:
                continue
            seen.add(b)
            d = bus[b]
            eps = d['src'] + d['dst']
            if d['K'] == 0:
                d['src'] = [e for e in eps if e.split('.')[0] == n]
                d['dst'] = [e for e in eps if e.split('.')[0] != n]
            todo += [e.split('.')[0] for e in d['dst']
                     if slots[e.split('.')[0]]['master'] != 'qfd_tile_nk']
    incoming = {e: b for b, d in bus.items() if d['cls'] != 'clock' for e in d['dst']}
    @functools.lru_cache(None)
    def arrival(endpoint):
        n, p = endpoint.split('.')
        if n == 'sp_vector_memory':
            return 0  # common VM output reference; absolute latency cancels
        if slots[n]['master'] == 'qfd_tile_nk':
            if p == 't_out':
                return input_arrival(n + '.tap') + 1
            if p == 'n_y':
                return max(input_arrival(n + '.n_a'), input_arrival(n + '.n_b')) + node_latency
            raise ValueError(endpoint)
        inputs = [e for e in incoming if e.startswith(n + '.')]
        assert len(inputs) == 1, (n, inputs)
        return input_arrival(inputs[0]) + 1
    def input_arrival(endpoint):
        d = bus[incoming[endpoint]]
        assert len(d['src']) == 1, (endpoint, d['src'])
        return arrival(d['src'][0]) + d['K'] + applied_pads.get(incoming[endpoint], 0)
    nodes = [n for n, s in slots.items() if s['master'] == 'qfd_tile_nk' and 'n_a' in s['pins']]
    skews = {n: input_arrival(n + '.n_a') - input_arrival(n + '.n_b') for n in nodes}
    pads = {}
    @functools.lru_cache(None)
    def balanced_arrival(endpoint):
        n, p = endpoint.split('.')
        if n == 'sp_vector_memory':
            return 0
        if slots[n]['master'] == 'qfd_tile_nk':
            if p == 't_out':
                return balanced_input(n + '.tap') + 1
            a, b = balanced_input(n + '.n_a'), balanced_input(n + '.n_b')
            if a != b:
                early = n + ('.n_a' if a < b else '.n_b')
                bn = incoming[early]
                pads[bn] = dict(extra_cycles=abs(a-b), destination=early, width_bits=bus[bn]['w'],
                                source=bus[bn]['src'][0])
            return max(a, b) + node_latency
        inputs = [e for e in incoming if e.startswith(n + '.')]
        assert len(inputs) == 1, (n, inputs)
        return balanced_input(inputs[0]) + 1
    def balanced_input(endpoint):
        d = bus[incoming[endpoint]]
        assert len(d['src']) == 1
        return balanced_arrival(d['src'][0]) + d['K']
    for n in nodes:
        balanced_arrival(n + '.n_y')
    return dict(nodes=len(nodes), misaligned=sum(v != 0 for v in skews.values()),
                skew_histogram=dict(sorted(collections.Counter(skews.values()).items())),
                examples=[dict(node=n, skew_cycles=v) for n, v in skews.items() if v][:12],
                corridor_roots=roots, relay_count=sum(d['K'] for d in bus.values()),
                proposed_pad_relays=sum(p['extra_cycles'] for p in pads.values()),
                proposed_storage_bits=sum(p['extra_cycles']*p['width_bits'] for p in pads.values()),
                proposed_pads=pads,
                node_latency_cycles=node_latency, limitation='Static bus arrival model only; does not prove bit exactness, relay clock presence, STA, or die closure.')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--source', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    result = audit(a.die_v)
    result.update(source=a.source, die_sha256=hashlib.sha256(Path(a.die_v).read_bytes()).hexdigest())
    Path(a.out).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
