#!/usr/bin/env python3
"""S81 VM A2 full-programme cost of the +2 fixed write edges (token-path model, immutable prices untouched).

A2 moves the registered drain capture from P+4+lane to P+6+lane (observed in the full shared53/full32/512-bit gate,
a2_controlled_pinplain_proof.json), so raw SRAM write P+10+n -> P+12+n and returned commit P+12+n -> P+14+n
(profile s81_vm_r4_c2_w1 -> A2).  Reads are unchanged.  Every job's completion fence is its returned commit, so a job
whose result lands in VM finishes 2 stream edges (2 x 833 ps = 2 token-path cycles at 1.2 GHz) later.

Charged with tools/throughput/accepted_cost.py rom_loss (--node-delta 2) on the committed token-path DAGs:
  upper   +2 on EVERY node (every node treated as a VM-landing job, fused SU sub-steps included)
  landing +2 on every node of a VM-landing class (field/su/coll/select/hbm), hop/embed/head excluded
  jobs    +2 on non-fused jobs only (a fused_fast chain writes VM once, at its end)
The share is modelled (no per-layer die run with A2 exists); the +2 is measured.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/throughput'))
import accepted_cost as ac  # noqa: E402

VM_CLASSES = {'su', 'field', 'coll', 'select', 'hbm'}


def run(doc, sel):
    nodes = doc['nodes']
    ids = [n['id'] for n in nodes if sel(n) and n.get('op') != 'wave.busy']
    rx = '^(' + '|'.join(map(__import__('re').escape, ids)) + ')$'
    return ac.rom_loss(doc, rx, 0, 0, node_delta=2.0)


def main():
    out = dict(schema='opentallas.s81.vm-a2-programme-cost.v1', added_write_edges=2, edge_ps=833.333,
               evidence_edge='results/arch/s81_vm_area_1417/a2_controlled_pinplain_proof.json (P+6+lane vs old P+4+lane)',
               model='tools/throughput/accepted_cost.py rom_loss node_delta=2 on results/arch/token_path_20261009',
               share_basis='modelled', workloads={})
    for wl, f in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp')):
        doc = json.load(open(ROOT / f'results/arch/token_path_20261009/{f}.json'))
        out['workloads'][wl] = dict(
            upper=run(doc, lambda n: True),
            landing=run(doc, lambda n: n['cls'] in VM_CLASSES),
            jobs=run(doc, lambda n: n['cls'] in VM_CLASSES and n['kind'] != 'fused_fast'))
    out['charge_pct'] = max(v['upper']['e2e_loss_pct'] for v in out['workloads'].values())
    out['verdict'] = ('worst-workload upper bound %.3f %% tok/s (<= 5 %% unit limit); S81 accepted total is already '
                      '17.485 %% under an owner exception, so adoption needs that decision recorded' % out['charge_pct'])
    p = ROOT / 'results/arch/s81_vm_area_1417/a2_programme_cost.json'
    p.write_text(json.dumps(out, indent=1) + '\n')
    for wl, v in out['workloads'].items():
        print(wl, {k: (r['added_cycles'], r['e2e_loss_pct']) for k, r in v.items()})
    print(out['verdict'])


if __name__ == '__main__':
    main()
