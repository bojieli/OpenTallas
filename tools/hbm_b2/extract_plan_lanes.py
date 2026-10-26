#!/usr/bin/env python3
"""HBM-BIND2 (2026-10-25): extract the lane table of a B2 die plan for tools/hbm_b2/b2_delays.py --plan (read only).

    git show <plan sha>:physical/die_plan/hbm_arch/B2n/die_plan.json > plan.json
    python3 tools/hbm_b2/extract_plan_lanes.py plan.json --source 'physical/die_plan/hbm_arch/B2n/die_plan.json @ <branch> <sha>' \
        --sha <sha> --out results/arch/hbm_arch_1024/b2_delay_inputs/B2n_lanes.json

Keeps every lane, the first / last port of every lane and latency.lanes (cycles / stations / boundary) -- what
b2_delays.py reads.  A new plan (B2o ...) is one more extract; the bind regenerates its delays from it (regen_b2.sh).
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('plan')
    ap.add_argument('--source', required=True)
    ap.add_argument('--sha', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    p = json.loads(Path(a.plan).read_text())
    keep = set()
    for ln in p['lanes']:
        keep.update((ln['ports'][0], ln['ports'][-1]))
    ports = [x for x in p['ports'] if x['id'] in keep]
    lat = {k: {f: v[f] for f in ('cycles', 'stations', 'boundary') if f in v} for k, v in p['latency']['lanes'].items()}
    out = dict(schema='opentallas.hbm_b2.plan_lanes.v1',
               source=a.source + ' (read only; first/last port of every lane + latency.lanes) -- extract for '
                                 'tools/hbm_b2/b2_delays.py --plan (tools/hbm_b2/extract_plan_lanes.py)',
               plan_sha=a.sha, note=p.get('note', '')[:2000],
               lanes=[dict(id=ln['id'], note=ln.get('note', ''), ports=[ln['ports'][0], ln['ports'][-1]]) for ln in p['lanes']], ports=ports, latency=dict(lanes=lat))
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f'lanes {len(p["lanes"])} ports {len(ports)} -> {a.out}')


if __name__ == '__main__':
    main()
