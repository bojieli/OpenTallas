#!/usr/bin/env python3
"""Audit every actual soft/hard cut of the proposed banked control component.

The fanout threshold selects a component; it never removes a physical port.
This is a source/ODB graph census, not a partition or timing qualification.
"""
import argparse
import collections
import gzip
import hashlib
import json
import subprocess
from pathlib import Path


def audit(rev, base, threshold):
    blobs = {n: subprocess.check_output(['git', 'show', f'{rev}:{base}/{n}.tsv.gz'])
             for n in ('instances', 'connections')}
    inst = {r[0]: r[1] for line in gzip.decompress(blobs['instances']).decode().splitlines()
            if (r := line.split('\t'))}
    def soft(i):
        return inst.get(i, '').endswith('_ASAP7_75t_R') and not inst[i].startswith(('TAPCELL', 'FILL'))
    nets = collections.defaultdict(list)
    for line in gzip.decompress(blobs['connections']).decode().splitlines():
        net, kind, i, model, pin, direction = line.split('\t')
        if kind == 'SIGNAL':
            nets[net].append((i, pin, direction))
    clocks = {n for n, ts in nets.items()
              if any(p == 'CLK' or p.startswith('ck') or p == 'clk' for _, p, _ in ts)}
    parent = {}
    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x
    for n, ts in nets.items():
        if n in clocks or len(ts) > threshold:
            continue
        cells = [i for i, _, _ in ts if soft(i)]
        for i in cells[1:]:
            parent[find(i)] = find(cells[0])
    components = collections.defaultdict(set)
    for i in inst:
        if soft(i):
            components[find(i)].add(i)
    core = max(components.values(), key=len)
    cuts = []
    for n, ts in nets.items():
        inside = [t for t in ts if t[0] in core]
        outside = [t for t in ts if t[0] not in core]
        if not inside or not outside:
            continue
        drivers = [t for t in inside if t[2] == 'OUTPUT']
        sinks = [t for t in inside if t[2] == 'INPUT']
        cuts.append(dict(net=n, clock=n in clocks, direction='output' if drivers else 'input',
                         existing_direct_ff_driver=bool(drivers) and all('DFF' in inst[t[0]] for t in drivers),
                         existing_direct_ff_sinks=bool(sinks) and all('DFF' in inst[t[0]] for t in sinks),
                         inside=inside, outside=outside,
                         external_soft=sum(soft(t[0]) for t in outside),
                         external_hard=sum(t[0] in inst and not inst[t[0]].endswith('_ASAP7_75t_R') for t in outside)))
    data = [r for r in cuts if not r['clock']]
    summary = dict(schema='opentallas.banked-control-complete-cut.v1', source_commit=rev,
                   input_sha256={n: hashlib.sha256(b).hexdigest() for n, b in blobs.items()},
                   selection_fanout_threshold=threshold, control_cells=len(core),
                   control_ff=sum('DFF' in inst[i] for i in core),
                   physical_nonclock_ports=len(data),
                   input_ports=sum(r['direction'] == 'input' for r in data),
                   output_ports=sum(r['direction'] == 'output' for r in data),
                   cuts_touching_other_soft_components=sum(r['external_soft'] > 0 for r in data),
                   existing_direct_ff_inputs=sum(r['direction'] == 'input' and r['existing_direct_ff_sinks'] for r in data),
                   existing_direct_ff_outputs=sum(r['direction'] == 'output' and r['existing_direct_ff_driver'] for r in data),
                   scope='All cut nets restored after graph selection, including high-fanout and soft-to-soft cuts. No source partition, leaf fit, pin registration, cycle cost or native qualification inferred.')
    return summary, dict(core_cells=sorted(core), cuts=cuts)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rev', default='9c2614c65')
    ap.add_argument('--base', default='results/rtl/qwen_compute_native_glue_1014/parent_pruned_1015/cut_census')
    ap.add_argument('--threshold', type=int, default=8)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    summary, detail = audit(a.rev, a.base, a.threshold)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    with gzip.open(a.out / 'complete_cut.json.gz', 'wt') as f:
        json.dump(detail, f, sort_keys=True)
    print(json.dumps(summary, indent=2))
