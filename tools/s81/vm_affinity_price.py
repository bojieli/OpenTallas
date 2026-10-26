#!/usr/bin/env python3
"""Price S81 VM relay edges PER VM JOB CLASS on the DS-ROM token path (client-affine VM banking, S-FUNC 2026-10-15).

The accepted VM.RELAY row adds one uniform edge count to every token-path node. With client-affine banking each
client's tensors live in the VM slice(s) beside its face, so relay edges differ per class.  Input: a JSON
{"basis": "...", "edges": {"su": n, "hc": n, "mix": n, "field": n, "coll": n, "svc": n, "sel": n}} (relay edges per
VM access of that class, from S-VM's reach screen).  Node -> class: token-path cls (field/su/coll/hbm/select), su
ops on the HC (".hc") -> hc, eng.* -> mix.  Hops, embed and head carry no VM access (0).  Output: AR and MTP loss
against the same base the ledger uses (tools/throughput/accepted_cost.solve, MTP wavefront term as rom_loss).

    python3 tools/s81/vm_affinity_price.py --edges E.json [--uniform 28] --out OUT.json
"""
import argparse, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/throughput'))
import accepted_cost as ac  # noqa: E402


def vm_class(n):
    cls, op = n['cls'], n['op']
    if cls == 'su':
        if '.hc' in op or op.startswith(('attn.hc', 'ffn.hc')):
            return 'hc'
        return 'mix' if op.startswith('eng.') else 'su'
    if cls == 'field':
        return 'mix' if op.startswith('eng.') else 'field'
    return dict(coll='coll', hbm='svc', select='sel').get(cls)


def node_edges(n, edges, op_edges=None):
    """relay edges of one token-path node: an op_edges regex override (per-access-set refinement, e.g. SU ops that
    write PQ inputs into the HC/PQ slice) wins over the class value."""
    for pat, val in (op_edges or {}).items():
        if vm_class(n) and re.search(pat, n['op']):
            return val
    return edges.get(vm_class(n), 0)


def price(doc, edges, op_edges=None):
    nodes, E = doc['nodes'], doc['edges']
    base, _ = ac.solve(nodes, E)
    delta = {n['id']: node_edges(n, edges, op_edges) for n in nodes if node_edges(n, edges, op_edges)}
    wave = [n['id'] for n in nodes if n.get('op') == 'wave.busy']
    if wave:                                   # same wavefront term as accepted_cost.rom_loss
        stages = [g for g in doc.get('groups', []) if g.get('kind') in ('stage', 'layer', 'embed')]
        worst = max(stages, key=lambda g: g['cycles'])['id']
        add = sum(delta.get(n['id'], 0) for n in nodes if n.get('group') == worst)
        for i in wave:
            delta[i] = delta.get(i, 0) + add
    new, _ = ac.solve(nodes, E, delta)
    per = {}
    for n in nodes:
        c = vm_class(n)
        if c:
            per[c] = per.get(c, 0) + 1
    return dict(base_cycles=round(base, 1), cycles=round(new, 1), added_cycles=round(new - base, 1),
                e2e_loss_pct=round(ac.loss_pct(base, new), 3), nodes_per_class=per)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--edges', type=Path, required=True)
    ap.add_argument('--uniform', type=int, default=None, help='also price this uniform edge count on VM-class nodes')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    spec = json.loads(a.edges.read_text())
    res = dict(schema='opentallas.s81.vm-affinity-price.v1', input=spec, grade='MODEL on the token path; edges from the '
               'S-VM reach screen (not a routed die)')
    for wl, f in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp')):
        doc = ac.load_path(f)
        res[wl] = price(doc, spec['edges'], spec.get('op_edges'))
        if a.uniform is not None:
            res[wl]['uniform_vm_class'] = price(doc, {k: a.uniform for k in ('su', 'hc', 'mix', 'field', 'coll', 'svc', 'sel')})
    txt = json.dumps(res, indent=2) + '\n'
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(txt)
    print(txt)


if __name__ == '__main__':
    main()
