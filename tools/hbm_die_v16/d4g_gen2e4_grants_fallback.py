#!/usr/bin/env python3
"""HBM-DIE6 10-20: GEN2e4 grant slots for every block the die case placed by GENERIC CENTROID FALLBACK.

The GEN2e4 diagnostic case_a (Codex identity3, artifacts/codex-gen2e4-diag-s3-1020/manifest_identity3.json) is NO GO with
placement_coverage FAIL: 82 instances (cxport dl/rc, cfg collars, obs/fault leaves, coll inj copies, host cfg leaves, xq
nodes, stree root, router ids, ...) had neither a grant slot nor an owner plan block, so die_case_v16 put each at the
bits^2 centroid of its placed peers ('-> outside plan blocks').  That is a run-time guess, not a floorplan decision.

This tool turns each of them into a REAL grant slot (same rule as d4g_gen2e_grants_homes.py step 6, no size floor):
target = bits^2-weighted centroid of its contract peers at their granted positions (slot centre when the peer has a used
slot, else its case_a site); nearest site clear of every used slot / plan block / placed block by CLR (21.6 um) and of the
centre N-S trunk channel; outline = the case_a SYNTH outline snapped up to 0.216 um; origin snapped to 0.216 um.
Biggest first.  Checks: no new slot within CLR of another used slot / new slot, none on a plan block, all inside the die.
Only coverage-fallback instances are touched; every existing slot is byte-identical.

    d4g_gen2e4_grants_fallback.py --contract PRE_RELAY.json[.gz] --manifest CASE_A_manifest.json --grants-in G.json
        --grants-out G2.json [--plan P] --report R.json [--png PNG]
"""
import argparse, json, math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_gen2e_grants_homes as GH  # noqa: E402  (Occ, snap, mkslot, rect, gap, load, CLR, RELEASE_PLAN)

GRANT = 'd4g_gen2e4_fallback_1020'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--contract', required=True); ap.add_argument('--manifest', required=True)
    ap.add_argument('--grants-in', required=True); ap.add_argument('--grants-out', required=True)
    ap.add_argument('--plan', default=str(GH.D / 'plan/d4g_phy/compact.P.json'))
    ap.add_argument('--report', required=True); ap.add_argument('--png')
    a = ap.parse_args()
    g = GH.load(a.grants_in); P = GH.load(a.plan); C = GH.load(a.contract); M = GH.load(a.manifest)
    I = C['instances']; PL = M['placement']
    rows = [r for r in M['placement_coverage']['rows'] if r['reason'] == 'generic_centroid_fallback']
    fb = {r['instance'] for r in rows}
    die = next(s for s in g['slots'] if s['kind'] == 'die'); W, H = die['outline']['w'], die['outline']['h']
    slots = {s['name']: s for s in g['slots']}
    clash = sorted(n for n in fb if n in slots)
    users = {}
    for n, v in I.items():
        if v.get('slot') in slots:
            users.setdefault(v['slot'], set()).add(n)
        if n in slots:
            users.setdefault(n, set()).add(n)
    used = lambda sn: bool(users.get(sn)) and slots[sn]['kind'] != 'die'
    occ = GH.Occ(W, H)
    for sn, s in slots.items():
        if used(sn) and sn not in fb:
            occ.add(GH.rect(s))
    for pn, b in P.items():
        if isinstance(b, dict) and 'x' in b and not GH.RELEASE_PLAN.match(pn):
            occ.add((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
    for n, p in PL.items():
        if n in fb or n not in I or GH.RELAY.match(n):
            continue
        occ.add((p['x'], p['y'], p['x'] + p['w'], p['y'] + p['h']))
    occ.add((W / 2 - 200.0, 0.0, W / 2 + 200.0, H), clr=0.0)
    adj = {}
    for e in C['edges']:
        s_, t_ = e['source'][0], e['sink'][0]
        if s_ != t_:
            adj.setdefault(s_, {}); adj[s_][t_] = adj[s_].get(t_, 0) + e['bits']
            adj.setdefault(t_, {}); adj[t_][s_] = adj[t_].get(s_, 0) + e['bits']
    new = {}

    def pos(m):
        if m in new:
            r = GH.rect(new[m]); return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        for sn in (m, I.get(m, {}).get('slot')):
            if sn in slots and used(sn) and sn not in fb:
                r = GH.rect(slots[sn]); return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        if m in PL and m not in fb:
            q = PL[m]; return q['x'] + q['w'] / 2, q['y'] + q['h'] / 2
        return None
    rep = dict(tool='tools/hbm_die_v16/d4g_gen2e4_grants_fallback.py', lane='HBM-DIE6 10-20', clearance_um=GH.CLR,
               grants_in=a.grants_in, manifest=a.manifest, fallback_instances=len(fb), name_clash=clash, new={}, violations=[])
    for n in sorted(fb, key=lambda n: -PL[n]['w'] * PL[n]['h']):
        if n not in I or n in slots:
            rep['violations'].append([n, 'not in contract' if n not in I else 'slot name already used']); continue
        p = PL[n]; w = GH.snap(math.ceil(p['w'] / 0.216) * 0.216); h = GH.snap(math.ceil(p['h'] / 0.216) * 0.216)
        pts = [(pos(m), b) for m, b in adj.get(n, {}).items() if pos(m)]
        wt = sum(b * b for _, b in pts)
        tx, ty = ((sum(q[0] * b * b for q, b in pts) / wt, sum(q[1] * b * b for q, b in pts) / wt) if wt
                  else (p['x'] + p['w'] / 2, p['y'] + p['h'] / 2))
        xy = occ.find(tx, ty, w, h)
        if xy is None:
            rep['violations'].append([n, 'no free site']); continue
        d = abs(xy[0] + w / 2 - tx) + abs(xy[1] + h / 2 - ty)
        dca = abs(xy[0] - p['x']) + abs(xy[1] - p['y'])
        s = GH.mkslot(n, I[n]['master'], xy[0], xy[1], w, h,
                      f'HBM-DIE6 10-20: grant slot for a GEN2e4 case_a generic-centroid-fallback home: nearest clear site '
                      f'(CLR {GH.CLR}) to the bits^2 centroid of {len(pts)} peers ({tx:.0f}, {ty:.0f}), {d:.0f} um off it; '
                      f'{dca:.0f} um from its case_a fallback site')
        s['grant'] = GRANT
        new[n] = s; occ.add(GH.rect(s))
        rep['new'][n] = dict(master=I[n]['master'], at=[xy[0], xy[1], w, h], centroid=[round(tx, 1), round(ty, 1)],
                             off_centroid_um=round(d, 1), from_case_a_um=round(dca, 1), peers=len(pts))
    S = [(sn, GH.rect(s)) for sn, s in slots.items() if used(sn) and sn not in fb] + [(n, GH.rect(s)) for n, s in new.items()]
    for n, s in new.items():
        r1 = GH.rect(s)
        for n2, r2 in S:
            if n2 != n and GH.gap(r1, r2) < GH.CLR - 1e-6 and slots.get(n2, {}).get('ring_block') is None:
                rep['violations'].append([n, n2, round(GH.gap(r1, r2), 2)])
        if not (0 <= r1[0] and r1[2] <= W and 0 <= r1[1] and r1[3] <= H):
            rep['violations'].append([n, 'die'])
        for pn, b in P.items():
            if isinstance(b, dict) and 'x' in b and not GH.RELEASE_PLAN.match(pn):
                if GH.gap(r1, (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])) < -1e-6:
                    rep['violations'].append([n, f'plan:{pn}'])
    g['slots'].extend(new[n] for n in sorted(new))
    offs = sorted(v['off_centroid_um'] for v in rep['new'].values())
    rep['summary'] = dict(fallback=len(fb), new=len(new), violations=len(rep['violations']),
                          off_centroid_um_max=offs[-1] if offs else None,
                          off_centroid_um_median=offs[len(offs) // 2] if offs else None)
    Path(a.grants_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.grants_out).write_text(json.dumps(g, indent=1) + '\n')
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    if a.png:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        f, ax = plt.subplots(figsize=(10, 15.7))
        for sn, s in slots.items():
            if used(sn):
                r = GH.rect(s); ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc='tab:blue', alpha=0.15, ec='tab:blue', lw=0.3))
        for n, s in new.items():
            r = GH.rect(s); ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc='tab:red', alpha=0.8, ec='tab:red', lw=0.8))
            c = rep['new'][n]['centroid']; ax.plot([c[0], (r[0] + r[2]) / 2], [c[1], (r[1] + r[3]) / 2], 'r-', lw=0.4)
            ax.text(r[2], r[3], n, fontsize=3)
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
        ax.set_title(f'GEN2e4 fallback grants: red = {len(new)} new slots (line to peer centroid), blue = used slots', fontsize=8)
        f.savefig(a.png, dpi=150, bbox_inches='tight')
    print(json.dumps(rep['summary']))
    for v in rep['violations'][:20]:
        print('  VIOL', v)
    raise SystemExit(1 if rep['violations'] else 0)


if __name__ == '__main__':
    main()
