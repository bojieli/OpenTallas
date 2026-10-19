#!/usr/bin/env python3
"""HBM-NEXT-DIE 10-19: landed-regions clocking plan of the P = 4 frame (standard 10-18).

From the hnx region map (hnx_case_inputs.py) and the plan pin model (v6_eval pins + lanes):
  * regions: count, largest box (every non-SM region <= 4 mm; each SM column region holds its own ck_n / ck_s landed
    regions inside the SM column parent, judged per linked child pair at the child flops, TT and FF <= 80 ps);
  * every plan-graph link whose ends sit in different regions is a LANDED crossing (4-slot ring, fixed latency, no
    backpressure) at the sink block input: count and bits per class;
  * forwarded half-cycle relay hops at the 405-um planning reach (repeaters inside registered hops): per link
    ceil(L / 405) - 1 on the pin-to-pin lane route (the v6_eval route rule), as count, bit-weighted mean and max per class.
No balanced / zero-skew tree spans more than one region.

    clock_plan_p4.py --plan results/arch/hbm_next_1019/die/plan/f4c --tag f4c --map physical/hbm_next/die/f4c/region_map_hnx_f4c.json --out ...
"""
import argparse, collections, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REACH = 405.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', required=True); ap.add_argument('--tag', required=True); ap.add_argument('--map', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    pd = ROOT / a.plan
    pins = json.loads((pd / 'pins' / f'{a.tag}.pins.json').read_text()); lanes = json.loads((pd / 'lanes.json').read_text())
    G = json.loads((pd / 'compact.graph.json').read_text())
    M = json.loads((ROOT / a.map).read_text())
    reg = {n: v['region'] for n, v in M['instances'].items()}
    ends = collections.defaultdict(list)
    for b, v in pins['blocks'].items():
        for f, fx in v['faces'].items():
            for p in fx['pins']:
                ends[p['link']].append(dict(p, block=b))
    cls = collections.defaultdict(lambda: dict(links=0, bits=0, landed_links=0, landed_bits=0, hops_bw=0.0, max_hops=0, longest_um=0.0, relay_flops=0))
    for l in G['links']:
        e = ends.get(l['id'], [])
        c = cls[l['cls']]
        c['links'] += 1; c['bits'] += l['bits']
        if reg.get(l['src']) != reg.get(l['dst']):
            c['landed_links'] += 1; c['landed_bits'] += l['bits']
        if len(e) == 2:
            p0, p1 = (e[0]['x'], e[0]['y']), (e[1]['x'], e[1]['y'])
            ln = lanes.get(l['id'], {})
            if 'v' in ln:
                L = abs(p0[0] - ln['v']) + abs(p1[1] - p0[1]) + abs(p1[0] - ln['v'])
            elif 'h' in ln:
                L = abs(p0[1] - ln['h']) + abs(p1[0] - p0[0]) + abs(p1[1] - ln['h'])
            else:
                L = abs(p0[0] - p1[0]) + abs(p0[1] - p1[1])
            hops = max(0, math.ceil(L / REACH) - 1)
            c['hops_bw'] += hops * l['bits']; c['max_hops'] = max(c['max_hops'], hops); c['longest_um'] = max(c['longest_um'], round(L))
            c['relay_flops'] += hops * l['bits']
    out = {}
    for k, c in sorted(cls.items(), key=lambda t: -t[1]['bits']):
        out[k] = dict(c, hops_bw=round(c['hops_bw'] / c['bits'], 2) if c['bits'] else 0.0)
    tot = dict(links=sum(c['links'] for c in cls.values()), landed_links=sum(c['landed_links'] for c in cls.values()),
               landed_bits=sum(c['landed_bits'] for c in cls.values()), relay_flops_405=sum(c['relay_flops'] for c in cls.values()),
               max_hops=max(c['max_hops'] for c in cls.values()))
    boxes = {r: v.get('box_um', [0.0, 0.0]) for r, v in M['regions'].items()}
    res = dict(schema='opentallas.hbm_next.clock_plan.v1', tag=a.tag, standard='landed regions 10-18; reach 405 um planning hop; '
               'pin-flop spread <= 80 ps TT+FF per region, neighbour-matched boundary through landings',
               regions=len(M['regions']), neighbour_pairs=len(M['neighbours']),
               largest_non_sm_region_um=max((max(b), r) for r, b in boxes.items() if not r.startswith(('sm_', 'phy_'))),
               sm_column_regions=dict(n=sum(1 for r in boxes if r.startswith('sm_')), inside='ck_n / ck_s landed regions per rp4 tile '
                                      '(PL-SMT form), 16 tiles x 2 regions; the column parent lands every tile-to-tile and tile-to-front crossing'),
               totals=tot, per_class=out)
    o = ROOT / a.out; o.parent.mkdir(parents=True, exist_ok=True)
    o.write_text(json.dumps(res, indent=1))
    print(json.dumps(dict(regions=res['regions'], largest=res['largest_non_sm_region_um'], totals=tot)))
    for k, c in out.items():
        print(f"  {k:10s} bits {c['bits']:6d} landed {c['landed_links']:3d}/{c['links']:3d} hops_bw {c['hops_bw']:5.2f} max {c['max_hops']:3d} longest {c['longest_um']}")


if __name__ == '__main__':
    main()
