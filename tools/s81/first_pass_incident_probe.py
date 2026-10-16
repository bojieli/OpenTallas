#!/usr/bin/env python3
"""Read-only first-pass incident probe, never a usable routed/native die model.

Reuse the source-pinned preflight stop before hop repair. Export diagnostic
instance/bus/pin-name inputs, and exact original service polylines/masks so an
observed later-hop fallback can be traced to its initial source chain. No RTL,
LEF or route products are emitted; generated face centroids stay labelled.
"""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--root', type=Path, required=True)
    a.add_argument('--recipe', type=Path, required=True)
    a.add_argument('--out', type=Path, required=True)
    args = a.parse_args()
    src, out = args.root.resolve(), args.out.resolve()
    if out.exists():
        raise SystemExit('refusing to overwrite diagnostic directory')
    out.mkdir(parents=True)
    sys.path.insert(0, str(src / 'tools'))
    sys.path.insert(0, str(src / 'tools/s81'))
    import dsrom_s81_fulldie as G
    import hub_path_preflight as P
    models, chains = [], []
    original_collected, original_run = P.Collected, G.Chains.run

    class Captured(original_collected):
        def __init__(self, model):
            models.append(model)
            super().__init__(model)

    def chain(self, name, lanes, path, allowed, start, *more, **kw):
        if name in ('aSW', 'qSW'):
            chains.append(dict(name=name, lanes=list(lanes), path=[list(p) for p in path],
                               allowed=[list(r) for r in allowed], start=list(start),
                               force_horiz=kw.get('force_horiz', False)))
        return original_run(self, name, lanes, path, allowed, start, *more, **kw)

    P.Collected, G.Chains.run = Captured, chain
    try:
        rc = P.run(src, args.recipe.resolve(), out / 'hub_preflight.json')
    finally:
        P.Collected, G.Chains.run = original_collected, original_run
    if not models:
        raise SystemExit('no complete first-pass diagnostic model captured')
    m = models[-1]
    by = {i.name: i for i in m['insts']}
    source_sha = (src / 'SOURCE_SHA').read_text().strip()
    rp = G.real_ports()
    plan = dict(schema='opentallas.s81.first_pass_diagnostic.v1',
                scope='FIRST_PASS_PRE_HOP_PRE_FINAL_PINS_NOT_USABLE_FOR_QUALIFICATION',
                source_commit=source_sha, generator_sha256=hashlib.sha256((src / 'tools/dsrom_s81_fulldie.py').read_bytes()).hexdigest(),
                insts=[i.d() for i in m['insts']], buses=m['buses'],
                pins={master + '|' + port: names for master, ports in rp.items() for port, names in ports.items()},
                final_pin_placement=False, final_hop_placement=False,
                relay_progress_applied=False, final_clock_reset_netlist=False,
                warnings=['Stop is before relay-progress repair and final global clock/reset construction.',
                          'May contain partial failed diagnostic chains.',
                          'Port-name mapping is not a native-view/actual-final-pin proof.',
                          'Never substitute this record for final GEN, native composition or signoff.'])
    with gzip.open(out / 'first_pass_plan.json.gz', 'wt') as f:
        json.dump(plan, f, separators=(',', ':'), default=str)
    lpt = G._lint_pin_pt(m)
    incident = []
    wanted_names = set()
    for bid, cls, bits, eps in m['buses']:
        if bid.startswith(('aSW', 'qSW')):
            endpoints = []
            for inst, port, *_ in eps:
                it = by[inst]
                wanted_names.add(inst)
                physical = lpt(inst, port)
                bound = G._rfp_bv_local(it.master, G.pslice(port)[0])
                assigned = (G._assigned_record(it.master) or {}).get('ports', {}).get(G.pslice(port)[0])
                point = G._rfp_pin(m, it, port, {}, lpt)
                endpoints.append(dict(inst=inst, port=port, master=it.master, candidate_point_um=point,
                                      point_resolution='hard LEF centroid' if physical else 'bound LEF centroid' if bound else 'assigned centroid' if assigned else 'generated kind face/centre proxy',
                                      actual_final_pins=False))
            incident.append(dict(bus=bid, cls=cls, bits=bits, endpoints=endpoints))
    hard = [i for i in m['insts'] if i.kind not in ('stn', 'hstn', 'rly')]
    planned = (13512.5, 17830.8)
    blockers = [i.d() for i in hard if i.x < planned[0] < i.x + i.w and i.y < planned[1] < i.y + i.h]
    report = dict(scope=plan['scope'], source_commit=source_sha,
                  requested_fallback=dict(bus='aSW_d43', planned_um=planned, actual_fallback_um=[10349.9,17820.0], displacement_um=3173.4),
                  initial_chain_paths=chains, initial_chain_buses=incident,
                  initial_chain_instances=[by[n].d() for n in sorted(wanted_names)],
                  planned_point_macro_blockers=blockers,
                  preflight_rc=rc,
                  pending=['Actual later-hop aSW_d43 may refer to rebuilt station endpoints; compare final GEN.',
                           'Final per-bit pins, native source/clock phases, legal station sites and route cuts remain open.'])
    (out / 'incident.json').write_text(json.dumps(report, indent=1, default=str) + '\n')
    print('INCIDENT_PROBE_DONE', json.dumps(dict(source=source_sha, instances=len(by), buses=len(m['buses']), service_buses=len(incident), blockers=[i['name'] for i in blockers])))


if __name__ == '__main__':
    main()
