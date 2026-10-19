#!/usr/bin/env python3
"""HBM-NEXT-DIE 10-19: die-case inputs for the P = 4 frame (stand-in integration), from the d4g GEN2 inputs (COPIED,
read-only) and a hbm_next plan (plan_p4.py output):

  grants_hnx_<tag>.json      grants_d4g.json with the die outline of the new plan and every die-level slot moved with
                             its plan block (slot -> plan_block / own name / the d4g block that contains its origin);
                             SM slots keep the CLOSED/as-built P = 1 outline (1939.68 x 6955.2, the stand-in) centred in x
                             in the P = 4 column slot and aligned to the column's INNER edge (the vmb-row / SM_X face);
                             child slots (parent != die) are parent-relative and unchanged.
  region_map_hnx_<tag>.json  the landed-regions clock plan of this frame: one region per SM column, per PC half, per
                             PHY, per IDX corner, per quadrant XQL store set, per SU group (bank pair + SU + SFU group +
                             HC client, <= 2.4 x 3.4 mm), per quadrant core (VM hub, SFU core, HC engine, SU core, DMA
                             back, IDX query), strip boxes <= 4 mm; neighbours = outlines within 600 um.  Every
                             region-to-region crossing is a LANDED crossing (4-slot ring, fixed latency, no backpressure).

    hnx_case_inputs.py --plan results/arch/hbm_next_1019/die/plan/f4c --tag f4c --out physical/hbm_next/die/f4c
"""
import argparse, collections, copy, json, math, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D4G = ROOT / 'results/arch/hbm_die_d4g'
FRAME = ROOT / 'physical/hbm_next/die/frame_d4g_copy'
IDXS_W, IDXS_H = 1508.976, 1509.84     # ot_hbm_idx_score_quarter_static stand-in view outline (GEN size rule)


def inside(r, x, y, tol=1.0):
    return r['x'] - tol <= x <= r['x'] + r['w'] + tol and r['y'] - tol <= y <= r['y'] + r['h'] + tol


def gap(a, b):
    dx = max(0.0, max(a['x'], b['x']) - min(a['x'] + a['w'], b['x'] + b['w']))
    dy = max(0.0, max(a['y'], b['y']) - min(a['y'] + a['h'], b['y'] + b['h']))
    return math.hypot(dx, dy)


def old_block_of(P0, x, y):
    hs = [n for n, r in P0.items() if inside(r, x, y)]
    if hs:
        return min(hs, key=lambda n: P0[n]['w'] * P0[n]['h'])
    return min(P0, key=lambda n: gap(P0[n], dict(x=x, y=y, w=0, h=0)))


def disp(P0, P, n):
    a, b = P0[n], P[n]
    if n.startswith('sm_'):
        dx = (b['x'] + b['w'] / 2) - (a['x'] + a['w'] / 2)
        if n.startswith('sm_SW'):             # S half: inner edge = top
            dy = (b['y'] + b['h']) - (a['y'] + a['h'])
        else:                                 # N half: inner edge = bottom
            dy = b['y'] - a['y']
        return dx, dy
    return b['x'] - a['x'], b['y'] - a['y']


ANCHOR = [  # GEN2 die slots that are not plan blocks: home next to their functional anchor (nearest free, 43.2 grid)
    (r'^coll(gi|gl|b|rs|ks)_(SW|SE|NW|NE)$', lambda m: f'coll_{m.group(2)}'),
    (r'^fr_(SW|SE|NW|NE)$', lambda m: f'coll_{m.group(1)}'),
    (r'^pgp_(SW|SE|NW|NE)$', lambda m: f'sucore_{m.group(1)}'),
    (r'^sfup_(SW|SE|NW|NE)$', lambda m: f'sfucore_{m.group(1)}'),
    (r'^calendar_(SW|SE|NW|NE)$', lambda m: f'vmh_{m.group(1)}'),
    (r'^vm_status4$', lambda m: 'vmh_SE'),
    (r'^hb_dbk_(SW|NW)$', lambda m: f'dbk_{m.group(1)}'),
    (r'^quant_NW_(xp|dec)$', lambda m: 'quant_NW0'),
    (r'^vmm_(NW)(\d)$', lambda m: f'vmb_{m.group(1)}{m.group(2)}'),
    (r'^fl_(SW|SE|NW|NE)(\d)$', lambda m: f'vmb_{m.group(1)}{2 * int(m.group(2)) + 1}'),
    (r'^fs_(SW|NW)$', lambda m: f'pc_{m.group(1)}0'),
    (r'^(refcfg|wbk)_(SW|NW)$', lambda m: f'pc_{m.group(2)}4'),
    (r'^hc_(eng|tbl)_tgt$', lambda m: 'hc_eng'),
    (r'^(host_N|host_ep|hb_argmax|hb_ckgen|su_pgr)$', lambda m: 'host_cp'),
]


def legalize(G, P, P0, W, H, moved, G0):
    """GEN2 corner engines as GEN2 places them (IDX scorer idx_s0 / idx_s1 in the W PHY corners, the single HC engine
    hc_eng in the S-E PHY corner); every other non-plan slot (and any slot that overlaps) goes to the nearest free 43.2-um
    site around its functional anchor.  Plan blocks without a GEN2 slot (the plan-graph abstractions hce_*, idxs_*, vmb_*)
    are free space here."""
    slots = [s for s in G['slots'] if s['parent'] == 'die' and s['kind'] != 'die']
    rect = lambda s: dict(x=s['origin']['x'], y=s['origin']['y'], w=s['outline']['w'], h=s['outline']['h'])
    ph_s, ph_n = P['phy_SW'], P['phy_NW']
    pcr = max(P[f'pc_SW{i}']['x'] + P[f'pc_SW{i}']['w'] for i in range(8))
    fixed = {}
    for s in slots:
        w, h = s['outline']['w'], s['outline']['h']
        if s['name'] == 'idx_s0':
            fixed[s['name']] = (ph_s['x'] - 60.0 - w, 32.4)
        elif s['name'] == 'idx_s1':
            fixed[s['name']] = (ph_n['x'] - 60.0 - w, H - 32.4 - h)
        elif s['name'] == 'hc_eng':
            fixed[s['name']] = (max(ph_s['x'] + ph_s['w'], pcr) + 60.0, 32.4)
    orig = {t['name']: t['origin'] for t in G0['slots'] if t.get('origin')}
    for s in slots:                     # PHY-row leaves keep their d4g offset to their PHY; HC targets to the HC engine
        m = re.match(r'^(wbk|refcfg|fs)_(SW|NW)$', s['name'])
        o = orig.get(s['name'])
        if m and o:
            st = m.group(2)
            fixed[s['name']] = (o['x'] + P[f'phy_{st}']['x'] - P0[f'phy_{st}']['x'], o['y'] + P[f'phy_{st}']['y'] - P0[f'phy_{st}']['y'])
    wk = next(t for t in slots if t['name'] == 'wbk_SW')     # hc_eng E of the PHY-row K-port (as GEN2)
    if 'wbk_SW' in fixed:
        fixed['hc_eng'] = (max(fixed['hc_eng'][0], fixed['wbk_SW'][0] + wk['outline']['w'] + 16.0), fixed['hc_eng'][1])
    he_x = fixed['hc_eng'][0] + next(t for t in slots if t['name'] == 'hc_eng')['outline']['w']
    for s in slots:                     # step 5: the S-E score quarter's plan corner holds the single stand-in HC engine
        if s['name'] == 'idxs_SE' and s['origin']['x'] < he_x and s['origin']['x'] + s['outline']['w'] > fixed['hc_eng'][0]:
            fixed['idxs_SE'] = (he_x + 60.0, s['origin']['y'])     # -> the free S-E corner E of hc_eng (as the relay-free GEN found)
    for s in slots:
        o = orig.get(s['name'])
        if s['name'] in ('hc_eng_tgt', 'hc_tbl_tgt') and o:
            he = orig['hc_eng']
            fixed[s['name']] = (o['x'] + fixed['hc_eng'][0] - he['x'], o['y'] + fixed['hc_eng'][1] - he['y'])
    log = {}
    placed = []
    todo = []
    for s in slots:
        if s['name'] in fixed:
            s['origin']['x'], s['origin']['y'] = [round(v, 3) for v in fixed[s['name']]]
            placed.append(rect(s)); log[s['name']] = 'gen2_corner'
        else:
            todo.append(s)
    def clash(r, sp=10.0):
        if r['x'] < 21.6 or r['y'] < 21.6 or r['x'] + r['w'] > W - 21.6 or r['y'] + r['h'] > H - 21.6:
            return True
        return any(r['x'] < q['x'] + q['w'] + sp and q['x'] < r['x'] + r['w'] + sp and r['y'] < q['y'] + q['h'] + sp and q['y'] < r['y'] + r['h'] + sp for q in placed)
    planned = lambda s: bool(s.get('hnx_moved_with')) and (s['name'] == s['hnx_moved_with'] or s.get('plan_block') == s['hnx_moved_with'])
    # plan-mapped slots first (biggest first), at their moved position when free; the rest after, all nearest-free
    todo.sort(key=lambda s: (not planned(s), -s['outline']['w'] * s['outline']['h']))
    for s in todo:
        if planned(s) and not clash(rect(s)):
            placed.append(rect(s)); continue
        anc = s['hnx_moved_with'] if planned(s) else None
        for pat, fn in ([] if anc else ANCHOR):
            m = re.match(pat, s['name'])
            if m:
                anc = fn(m); break
        w, h = s['outline']['w'], s['outline']['h']
        if anc == 'hc_eng':
            a = next(rect(t) for t in slots if t['name'] == 'hc_eng')
        elif anc in P:
            a = P[anc]
        else:
            a = dict(x=s['origin']['x'], y=s['origin']['y'], w=w, h=h); anc = 'own'
        cx, cy = a['x'] + a['w'] / 2, a['y'] + a['h'] / 2
        best = None
        step = 43.2
        for ring in range(0, 400):
            cands = []
            for i in range(-ring, ring + 1):
                for j in (-ring, ring) if abs(i) != ring else range(-ring, ring + 1):
                    cands.append((cx - w / 2 + i * step, cy - h / 2 + j * step))
            # stay in the anchor's quadrant: same side of the centre line and of the strip mid-line
            ok = [c for c in cands if ((c[0] + w / 2 - W / 2) * (cx - W / 2) >= 0 or abs(cx - W / 2) < 1.0)
                  and ((c[1] + h / 2 - H / 2) * (cy - H / 2) >= 0 or abs(cy - H / 2) < 1000.0)
                  and not clash(dict(x=c[0], y=c[1], w=w, h=h))]
            if ok:
                best = min(ok, key=lambda c: abs(c[0] + w / 2 - cx) + abs(c[1] + h / 2 - cy)); break
        if best is None:
            log[s['name']] = 'UNPLACED'; continue
        s['origin']['x'], s['origin']['y'] = round(best[0], 3), round(best[1], 3)
        placed.append(rect(s))
        log[s['name']] = f'near {anc} ({abs(best[0] + w / 2 - cx) + abs(best[1] + h / 2 - cy):.0f} um)'
        moved['legalized'] += 1
    return log


def region_of(n):
    m = re.match(r'^sm_(SW|NW)(\d)$', n)
    if m:
        return n
    m = re.match(r'^pc_(SW|NW)(\d)$', n)
    if m:
        st, i = m.group(1), int(m.group(2))
        return f'pc_{st}_{i // 2}'                 # 2 PCs a region (2.2 mm)
    if n.startswith('phy_'):
        return n
    m = re.match(r'^idxs_(SW|SE|NW|NE)$', n)
    if m:
        return 'idx_' + m.group(1)
    m = re.match(r'^xq_(SW|NW)_p(\d)_', n)
    if m:
        return f'xq_{m.group(1)}_p{m.group(2)}'      # one region per XQL pair store set
    m = re.match(r'^pleaf_(SW|SE|NW|NE)$', n)
    if m:
        return 'leaf_' + m.group(1)
    m = re.match(r'^(vmb)_(SW|SE|NW|NE)(\d)$', n)
    if m:
        return f'grp_{m.group(2)}{int(m.group(3)) // 2}'
    m = re.match(r'^fus_(SW|SE|NW|NE)(\d)$', n)        # UNITS-FUSED lane: one per VM bank, in its bank pair's SU group
    if m:
        return f'grp_{m.group(1)}{int(m.group(2)) // 2}'
    m = re.match(r'^(su|sfu|hc|quant)_(SW|SE|NW|NE)(\d)$', n)
    if m:
        return f'grp_{m.group(2)}{m.group(3)}'
    m = re.match(r'^(vmh|sfucore|hce)_(SW|SE|NW|NE)$', n)
    if m:
        return 'core_' + m.group(2)
    m = re.match(r'^(sucore|sucx|dbk|hc|cij|idxq)_(SW|SE|NW|NE)$', n)
    if m:
        return 'corec_' + m.group(2)
    return None                                # strip blocks: by 4-mm box


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', required=True); ap.add_argument('--tag', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    pd = ROOT / a.plan
    P = json.loads((pd / 'compact.P.json').read_text())
    W, H = json.loads((pd / 'compact.metrics.json').read_text())['die_um']
    P0 = json.loads((FRAME / 'd4g_phy.compact.P.json').read_text())
    G0 = json.loads((FRAME / 'grants_d4g_3ca4d2b98.json').read_text())   # GEN2 grants incl. the hardened hb_ckgen pins (3ca4d2b98)
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    # ---------------------------------------------------------------- grants
    G = copy.deepcopy(G0)
    G['die'] = 'hnx_hbm_p4'; G['version'] = f'hnx.{a.tag}.1'; G['owner'] = 'HBM-NEXT-DIE'; G['updated'] = '2026-10-19'
    G['floorplan'] = dict(file=str((pd / 'compact.P.json').relative_to(ROOT)), candidate=a.tag, die_um=[W, H],
                          derived_from='results/arch/hbm_die_d4g/grants_d4g.json @ claude/hd4g-gen2-1018 3ca4d2b98 (copied to physical/hbm_next/die/frame_d4g_copy/grants_d4g_3ca4d2b98.json; slots moved with their plan block)',
                          stand_in='SM slots keep the P = 1 outline 1939.68 x 6955.2 inside the P = 4 column slot (SM4 view pending)')
    moved = collections.Counter()
    loc = {}
    for s in G['slots']:
        if s['parent'] is None or s['kind'] == 'die':
            s['outline'] = {'w': W, 'h': H}
            continue
        if s['parent'] != 'die':
            continue
        o = s['origin']
        cand = [s.get('plan_block'), s['name']]
        b = next((c for c in cand if c and c in P0 and c in P), None)
        rule = 'plan_block' if b and b == s.get('plan_block') else 'name'
        if b is None:
            b = old_block_of(P0, o['x'] + s['outline']['w'] / 2, o['y'] + s['outline']['h'] / 2); rule = 'contained'
        if b not in P:
            moved['unmapped'] += 1
            continue
        dx, dy = disp(P0, P, b)
        if b.startswith('sm_') and s['name'] == b:
            o['x'] = round(P[b]['x'] + (P[b]['w'] - s['outline']['w']) / 2, 3)
            o['y'] = round(P[b]['y'] + (P[b]['h'] - s['outline']['h'] if b.startswith('sm_SW') else 0.0), 3)
        else:
            o['x'] = round(o['x'] + dx, 3); o['y'] = round(o['y'] + dy, 3)
        s['hnx_moved_with'] = b
        loc[s['name']] = (o['x'] + s['outline']['w'] / 2, o['y'] + s['outline']['h'] / 2, b)
        moved[rule] += 1
    # step 5 (10-19): the IDX score quarters get one die slot per quadrant at the plan's IDX corner (idxs_<q>), with the
    # stand-in view outline, instead of the GEN2 W-corner pair slots idx_s0/idx_s1 (contract slots idx_s<k>_h<j> match no
    # grant, so GEN placed the 1.5-mm quarters LAST in free area -- after 40,936 relay lane rows had taken it: DIE-P4-1
    # S7 'no free area for hb_idx__s_SW').  The case scripts slot-map hb_idx__s_<q> -> idxs_<q> (placed before lane rows).
    tmpl = next(s for s in G['slots'] if s['name'] == 'idx_s0')
    G['slots'] = [s for s in G['slots'] if s['name'] not in ('idx_s0', 'idx_s1')]
    for q in ('SW', 'SE', 'NW', 'NE'):
        b = P.get(f'idxs_{q}')
        if b is None:
            continue
        s = copy.deepcopy(tmpl)
        s['name'] = f'idxs_{q}'; s['cell'] = 'ot_hbm_idx_score_quarter_static'
        s['outline'] = dict(w=IDXS_W, h=IDXS_H)
        s['origin'] = dict(x=round(b['x'] + (b['w'] - IDXS_W) / 2, 3), y=round(b['y'] + (b['h'] - IDXS_H) / 2, 3), orient='R0')
        s['hnx_moved_with'] = f'idxs_{q}'
        s['notes'] = f'HBM-NEXT-DIE step 5: score quarter hb_idx__s_{q} (stand-in view outline), plan block idxs_{q}'
        G['slots'].append(s)
    legal = legalize(G, P, P0, W, H, moved, G0)
    G['hnx_moved'] = dict(moved)
    G['hnx_legalized'] = legal
    (out / f'grants_hnx_{a.tag}.json').write_text(json.dumps(G, indent=1))
    # ---------------------------------------------------------------- region map
    M0 = json.loads((D4G / 'd4g_region_map.json').read_text())
    final = {s['name']: (s['origin']['x'] + s['outline']['w'] / 2, s['origin']['y'] + s['outline']['h'] / 2)
             for s in G['slots'] if s['parent'] == 'die' and s['kind'] != 'die'}
    blocks_region = {}
    for n, r in P.items():
        rg = region_of(n)
        if rg is None:                         # strip: 4-mm boxes from the W edge
            rg = f'strip_{int((r["x"] + r["w"] / 2) // 2500)}'
        blocks_region[n] = rg
    members = collections.defaultdict(list)
    for n, rg in blocks_region.items():
        members[rg].append(n)
    regions = {}
    for rg, ms in sorted(members.items()):
        x0 = min(P[m]['x'] for m in ms); y0 = min(P[m]['y'] for m in ms)
        x1 = max(P[m]['x'] + P[m]['w'] for m in ms); y1 = max(P[m]['y'] + P[m]['h'] for m in ms)
        regions[rg] = dict(site=[round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)], members=sorted(ms), box_um=[round(x1 - x0, 1), round(y1 - y0, 1)])
    for s_ in G['slots']:
        m_ = re.match(r'^idxs_(SW|SE|NW|NE)$', s_['name'])
        if m_ and 'idx_' + m_.group(1) in regions:
            regions['idx_' + m_.group(1)]['site'] = [round(final[s_['name']][0], 1), round(final[s_['name']][1], 1)]
    inst = {}
    for n in M0['instances']:
        if n in P:
            b = n
        elif n in final:
            fx, fy = final[n]
            b = min(P, key=lambda k: gap(P[k], dict(x=fx, y=fy, w=0, h=0)))
        else:
            old = M0['instances'][n]['site']
            b = old_block_of(P0, *old)
        if b not in blocks_region:
            b = min(P, key=lambda k: gap(P[k], P0.get(b, P[k])))
        rg = blocks_region[b]
        inst[n] = dict(region=rg, site=regions[rg]['site'])
    for n in P:
        inst.setdefault(n, dict(region=blocks_region[n], site=regions[blocks_region[n]]['site']))
    nb = set()
    rl = sorted(regions)
    for i, ra in enumerate(rl):
        for rb in rl[i + 1:]:
            if any(gap(P[x], P[y]) <= 600.0 for x in members[ra] for y in members[rb]):
                nb.add((ra, rb))
    big = {rg: v['box_um'] for rg, v in regions.items() if max(v['box_um']) > 4000 and not rg.startswith(('sm_', 'phy_'))}
    M = dict(schema=M0['schema'], plan=str((pd / 'compact.P.json').relative_to(ROOT)),
             rule=('HBM-NEXT-DIE P=4 (landed-regions standard 10-18): one region per SM column (its own ck_n/ck_s landed regions '
                   'inside), per PC half, per PHY, per IDX corner, per quadrant XQL store set, per SU group (bank pair + SU slot + '
                   'SFU group + HC client), per quadrant core (VM hub, SFU core, HC engine, SU core, DMA back, IDX query, config '
                   'leaf), strip boxes of 4 mm; every crossing between regions LANDED (4-slot ring, fixed latency, no '
                   'backpressure); neighbours = outlines within 600 um'),
             instances=inst, regions=regions, neighbours=sorted([list(p) for p in nb]), over_4mm_non_sm=big)
    (out / f'region_map_hnx_{a.tag}.json').write_text(json.dumps(M, indent=1))
    print('grants moved', dict(moved), '| regions', len(regions), 'neighbour pairs', len(nb), 'instances', len(inst), '| >4mm', big)


if __name__ == '__main__':
    main()
