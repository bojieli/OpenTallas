#!/usr/bin/env python3
"""LAND-HBM-1 (METHODOLOGY 12.11, OWNER 10-27 ~19:0x): HBM regional clock domains joined by LANDED crossings.

    hbm_land_regions.py --plan DIR --form F [--k 3] --out DIR [--emit-plan]

Regions are FUNCTIONAL and coarse so the token-critical serial chains (hub-internal core-core legs, the HC bank sum
chain b000->...->b013, the SU row) stay inside one region; only hub<->row / hub<->SM / hub<->root / root<->PHY
crossings land.  A partition is never split across regions.  Forms (Q = NW / NE quadrant, mirrored):
  part   every partition its own region (all-seam fallback; upper reference)
  func   Q_hub | Q_bank (b0xx + io SerDes) | Q_nrow (su0x su1x b112 b113 spu0) | Q_srow (b10x b11x su2x su3x spu1)
         | Q_smN (sm0 spt* sm1) | Q_smS (sm2 spb* sm3) | ROOT (root + vsN*) | TOP (PHY_N + mca/mcb, HBM PHY hard)
  func4  func, but each SM its own region and spt*/spb* a service region (Q_sm0..3, Q_spt, Q_spb)
  core   Q_core = hub + bank + nrow + srow | Q_smN | Q_smS | ROOT | TOP
  quad   Q = every Q_ partition | ROOT | TOP
TOP = PHY_N + mca/mcb + vsN6 (soft PHY feed, so no landing sinks in the hard PHY macro); ROOT = root + vsN0..5.
Landed crossing = every plan port whose src and dst partition sit in different regions (ot_dp_clk_landing,
DEPTH4/OFFSET2/RDREG1, +K cycles, sink-side ring).  Two lane readings, as fallback_regions.py:
  face  ft stations run on the crossed partition's clock -> +K at every landed face of the lane
  fwd   ft stations of a lane run on its forwarded clock -> +K once per lane if any face is landed
--emit-plan writes DIR/<reading>/die_plan.json = the plan with lanes[*].fixed_cycles += added cycles (PRICING COPY
ONLY, never a plan event) + core_conns.json symlink, for the R13 price chain (b1_lane_traversal + cc_price + S2).
Ring area basis = FALLBACK-LAND 10-26 4.66 um2 per landed bit (5.4 FF/bit DEPTH4+RDREG1 + control), UNMAPPED.
"""
import argparse, collections, json, os, re
from pathlib import Path

RING_UM2_PER_BIT = 4.66
# the HBM PHY is a hard macro: a ring cannot sit in it, so its soft feed partition on the ROOT column (vsN6, the L9
# pass-through) joins TOP and every PHY-bound lane lands in a soft partition (checked: hard_sink_landings == 0)
TOP_FEED = 'vsN6'


def base(name):
    return re.sub(r'^(NW|NE)_', '', name)


def quad(name):
    m = re.match(r'^(NW|NE)_', name)
    return m.group(1) if m else None


def region_of(name, form):
    q, b = quad(name), base(name)
    if name == 'PHY_N' or b in ('mca', 'mcb') or name == TOP_FEED:
        return 'TOP'
    if name == 'root' or name.startswith('vsN'):
        return 'ROOT'
    if q is None:
        raise SystemExit(f'unclassified partition {name}')
    if form == 'part':
        return name
    if form == 'quad':
        return q
    grp = None
    if b == 'hub':
        grp = 'hub'
    elif re.match(r'^b0\d\d$', b) or b == 'io':
        grp = 'bank'
    elif b in ('su00', 'su01', 'su10', 'su11', 'b112', 'b113', 'spu0'):
        grp = 'nrow'
    elif re.match(r'^b1[01]\d$', b) or b in ('su20', 'su21', 'su30', 'su31', 'spu1'):
        grp = 'srow'
    elif b in ('sm0', 'sm1') or b.startswith('spt'):
        grp = 'smN' if form != 'func4' else (b if b.startswith('sm') else 'spt')
    elif b in ('sm2', 'sm3') or b.startswith('spb'):
        grp = 'smS' if form != 'func4' else (b if b.startswith('sm') else 'spb')
    if grp is None:
        raise SystemExit(f'unclassified partition {name}')
    if form == 'core' and grp in ('hub', 'bank', 'nrow', 'srow'):
        grp = 'core'
    return f'{q}_{grp}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--form', required=True, choices=['part', 'func', 'func4', 'core', 'quad'])
    ap.add_argument('--k', type=int, default=3)
    ap.add_argument('--out', required=True)
    ap.add_argument('--emit-plan', action='store_true')
    a = ap.parse_args()
    pd = Path(a.plan)
    P = json.loads((pd / 'die_plan.json').read_text())
    T = P['partition_types']
    reg = {p['name']: region_of(p['name'], a.form) for p in P['partitions']}
    rect = {}
    for p in P['partitions']:
        w, h = T[p['type']]['outline_um']; x, y = p['origin_um']
        rect[p['name']] = [x, y, x + w, y + h]
    ports = {p['id']: p for p in P['ports']}
    landed = []
    for p in P['ports']:
        s, d = p['src']['part'], p['dst']['part']
        if s in reg and d in reg and reg[s] != reg[d]:
            landed.append(dict(id=p['id'], src=s, dst=d, src_region=reg[s], dst_region=reg[d], width=p['width'],
                               face=p.get('face'), kind=p.get('kind')))
    hard_sink = [x for x in landed if T[next(p['type'] for p in P['partitions'] if p['name'] == x['dst'])].get('hard')]
    lid = {x['id'] for x in landed}
    lanes = {}
    for ln in P['lanes']:
        n = sum(1 for i in ln['ports'] if i in lid)
        if n:
            lanes[ln['id']] = dict(faces_landed=n, face=a.k * n, fwd=a.k, ports=ln['ports'])
    regions = collections.defaultdict(lambda: dict(parts=[], hard_cores=0))
    for p in P['partitions']:
        r = regions[reg[p['name']]]
        r['parts'].append(p['name']); r['hard_cores'] += len(T[p['type']].get('hard_cores') or [])
    for rn, r in regions.items():
        xs = [rect[n] for n in r['parts']]
        r['bbox_um'] = [min(v[0] for v in xs), min(v[1] for v in xs), max(v[2] for v in xs), max(v[3] for v in xs)]
        r['area_mm2'] = round(sum((v[2] - v[0]) * (v[3] - v[1]) for v in xs) / 1e6, 3)
        r['bbox_mm'] = [round((r['bbox_um'][2] - r['bbox_um'][0]) / 1e3, 2), round((r['bbox_um'][3] - r['bbox_um'][1]) / 1e3, 2)]
    bits = sum(x['width'] for x in landed)
    pair = collections.Counter()
    for x in landed:
        pair[tuple(sorted((x['src_region'], x['dst_region'])))] += x['width']
    summ = dict(form=a.form, k=a.k, plan=str(pd), regions=len(regions), landed_ports=len(landed), landed_bits=bits,
                ring_area_mm2_unmapped=round(bits * RING_UM2_PER_BIT / 1e6, 3),
                die_area_mm2=round(P['die']['outline_um'][0] * P['die']['outline_um'][1] / 1e6, 3),
                lanes_landed=len(lanes), hard_sink_landings=[x['id'] for x in hard_sink], lane_added_face=sum(v['face'] for v in lanes.values()),
                lane_added_fwd=sum(v['fwd'] for v in lanes.values()),
                region_pairs_bits={f'{k[0]}<->{k[1]}': v for k, v in sorted(pair.items(), key=lambda kv: -kv[1])},
                largest_region_bbox_mm=max((r['bbox_mm'] for r in regions.values()), key=lambda v: v[0] * v[1]))
    summ['ring_area_pct'] = round(100 * summ['ring_area_mm2_unmapped'] / summ['die_area_mm2'], 3)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / 'regions.json').write_text(json.dumps(dict(form=a.form, partition_region=reg, regions=regions), indent=1))
    (out / 'landed_crossings.json').write_text(json.dumps(landed, indent=1))
    (out / 'lane_added.json').write_text(json.dumps(lanes, indent=1))
    (out / 'summary.json').write_text(json.dumps(summ, indent=1))
    if a.emit_plan:
        for mode in ('face', 'fwd'):
            Q = json.loads(json.dumps(P))
            for ln in Q['lanes']:
                if ln['id'] in lanes:
                    ln['fixed_cycles'] = int(ln.get('fixed_cycles', 0)) + lanes[ln['id']][mode]
            o = out / mode; o.mkdir(exist_ok=True)
            (o / 'die_plan.json').write_text(json.dumps(Q))
            cc = o / 'core_conns.json'
            if not cc.exists():
                os.symlink((pd / 'core_conns.json').resolve(), cc)
    print(json.dumps({k: v for k, v in summ.items() if k != 'region_pairs_bits'}))


if __name__ == '__main__':
    main()
