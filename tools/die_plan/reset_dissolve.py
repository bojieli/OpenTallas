#!/usr/bin/env python3
"""Expose planned reset-bearing hard cores without descending into their private RTL.

This is an explicit as-built manifest transform. The resulting bind must still pass
strict connectivity, core-reset identity/polarity and reset timing checks.
"""
import argparse
import copy
import json
import re
from pathlib import Path

import bind_elab as E
import reset_tree as RT
import schema


def ancestors(graph, targets, stop):
    """Structural ancestors of targets; never dissolve another physical hard core."""
    live = set(targets) & graph.keys()
    while True:
        nxt = live | {n for n, children in graph.items() if n not in stop and children & live}
        if nxt == live:
            return live - set(stop)
        live = nxt


def transform(raw, plan_path, manifest):
    p = schema.Plan(raw, Path(plan_path))
    stop = {c['module'] for t in p.types.values() for c in t.get('hard_cores', [])}
    targets = set()
    for tn, t in p.types.items():
        inst = {x['inst'] for x in RT.core_reset_targets(p, tn)}
        targets |= {c['module'] for c in t.get('hard_cores', []) if c['inst'] in inst}
    ab = copy.deepcopy(manifest)
    idx = E.module_index(ab.get('rtl_roots', []), ab.get('files', []), ab['base'])
    texts = {}
    def children(n):
        f, _ = E.pick(idx, n, ab.get('prefer', []))
        if f is None:
            return set()
        if f not in texts:
            texts[f] = E._strip(Path(f).read_text(errors='replace'))
        m = re.search(r'^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+' + re.escape(n)
                      + r'\b(.*?)\bendmodule\b', texts[f], re.M | re.S)
        return E.instantiated(m.group(1), idx) if m else set()
    graph = {}
    todo = list(ab.get('dissolve', []))
    for f in ab['netlist']:
        fp = Path(f) if Path(f).is_absolute() else Path(ab['base']) / f
        todo += E.instantiated(E._strip(fp.read_text()), idx)
    while todo:
        n = todo.pop()
        if n in graph:
            continue
        graph[n] = set() if n in stop else children(n)
        todo += graph[n]
    added = sorted(ancestors(graph, targets, stop) - set(ab.get('dissolve', [])))
    ab['dissolve'] = sorted(set(ab.get('dissolve', [])) | set(added))
    receipt = dict(added=added, reset_core_modules=sorted(targets),
                   missing_reset_core_modules=sorted(targets - graph.keys()),
                   graph_modules=len(graph), note='Manifest transform only; strict bind and verification required')
    return ab, receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('manifest', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    ab, rec = transform(json.loads(a.plan.read_text()), a.plan, json.loads(a.manifest.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(ab, indent=1) + '\n')
    a.out.with_suffix('.reset_dissolve.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
