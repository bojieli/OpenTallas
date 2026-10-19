#!/usr/bin/env python3
"""TW5-GEN2E 10-19: GEN2e grant slots for the d4g 'generated homes' (blocks that had no grant slot / owner plan block).

GEN2/GEN2c post-landing GEN died 'no free area for hb_idx__s_SW (1509x1510)': die_case_v16's OWNER rule maps hb_idx* to
plan blocks idx_\\w+, which misses idxs_<q> / idxq_<q>; the 4 IDX quarter scorers (and ~45 other big blocks) got peer-centroid
homes at run time, the scorers in die corners 5.8-11.9 mm from their svg peers, and post-landing lane rows then took those
corners.  This tool gives every such block a REAL grant slot beside its data peers (good floorplan = timing + routing
closure; short regular links; no empty regions on link paths), on top of the HC ring grants (d4g_gen2d_grants_hcring.py)
and the COORD 0kb pretree p2 slot.

Edits (all idempotent):
 1. slot renames: the SE/NE x-load pair stores use the S/N SM pair gaps p2/p3: grant slots xq_SW_p2_* / xq_SW_p3_* /
    xq_NW_p2_* / xq_NW_p3_* had NO user (contract names xq_SE_p0_* / xq_SE_p1_* / xq_NE_p0_* / xq_NE_p1_*) -> renamed.
 2. hc_eng (ot_hbm_hc_root_static, std 0.144 mm2 + 2 x 1024x256 SRAM) sat in the old 5,223 x 1,953 HC engine slot at the
    SE die corner (12-18 mm from its 4 ring hubs, 913 b each) on top of plan idxs_SE: shrunk to an area-sized slot and
    re-homed at the free site nearest the 4 ring-hub centroid (die centre); its v15 plan pin windows dropped (top-down pins).
 3. IDX quarter scorers hb_idx__s_<q> (1509 x 1510 SYNTH): inside plan idxs_<q>, flush to the PHY W (SW/NW) or E (SE/NE)
    edge -- the nearest legal site to their 4 svg peers (4 x 1,099 b on the PC band); q_<q> + op_<q> (query core + VM
    operand reader) beside their scorer (GEN2c topology: the IDX latency budget results/arch/hbm_banklat_1019/idx_budget.json
    assumes it; the [HBM-BANKLAT-IDX] op-beside-VM-banks lever needs a re-budget and is NOT taken here).
 4. wbk_SW / wbk_NW (the old slot sat E of the PHY, beside nothing it talks to): moved into the bottom (top) of the SM pair
    gap 2/3 above the PC band, beside vmks_<q>0..3; wbk_SE / wbk_NE get the mirror slot in gap 4/5 (their GEN2a home).
 5. every other generated home >= MIN_UM2 (xl_<q>_ctl, x-load aq trees, epcal, qctl, dbk, cxij, host ingress, ...): a slot
    at its GEN2a home when that site is clear of every slot / plan block / placed block at CLR, else at the nearest clear
    site (occupancy scan, 10.8 um grid).
Checks: every new/moved slot clears every other used slot, plan block (own/released ones excepted) and GEN2a block by CLR.
    d4g_gen2e_grants_homes.py --contract PRE_RELAY.json[.gz] --manifest GEN2a_manifest.json [--grants G] [--plan P]
        [--report R] [--png PNG] [--check-only]"""
import argparse, gzip, json, math, re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'results/arch/hbm_die_d4g'
Q = ['SW', 'SE', 'NW', 'NE']
CLR = 21.6
G_UM = 10.8
MIN_UM2 = 9000.0
GRANT = 'd4g_gen2e_homes_1019'
RELAY = re.compile(r'(hbfd_|rf\d+_|sfr_|hidxr_|hcx_|rly\d+_|lh\d|land)')
RENAME = {f'xq_{h}_p{a}_{k}': f'xq_{h2}_p{b}_{k}'
          for h, h2 in (('SW', 'SE'), ('NW', 'NE')) for a, b in ((2, 0), (3, 1))
          for k in ['eg', 'bd'] + [f'bfq{i}' for i in range(4)]}
RELEASE_PLAN = re.compile(r'(idxs|idxq)_(SW|SE|NW|NE)$|idx_(q|op)$')
HC_ENG_WH = (496.8, 540.0)          # 0.268 mm2 for 0.144 mm2 std / 0.60 + 2 x 1.3 x 0.0123 mm2 SRAM = 0.272 -> ~0.9 fill
WBK_WH = (475.2, 475.2)             # SYNTH area outline was 470 x 471


def load(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def rect(s):
    return (s['origin']['x'], s['origin']['y'], s['origin']['x'] + s['outline']['w'], s['origin']['y'] + s['outline']['h'])


def gap(a, b):
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def snap(v):
    return round(round(v / 0.216) * 0.216, 3)


class Occ:
    def __init__(s, W, H):
        s.W, s.H = W, H
        s.nx, s.ny = int(math.ceil(W / G_UM)), int(math.ceil(H / G_UM))
        s.m = np.zeros((s.ny, s.nx), dtype=np.int32)

    def add(s, r, clr=CLR):
        x0 = max(0, int(math.floor((r[0] - clr) / G_UM))); x1 = min(s.nx, int(math.ceil((r[2] + clr) / G_UM)))
        y0 = max(0, int(math.floor((r[1] - clr) / G_UM))); y1 = min(s.ny, int(math.ceil((r[3] + clr) / G_UM)))
        s.m[y0:y1, x0:x1] = 1

    def find(s, tx, ty, w, h, edge=21.6):
        """lower-left (x, y) of the free w x h site whose centre is nearest (Manhattan) to (tx, ty)"""
        bw, bh = int(math.ceil(w / G_UM)), int(math.ceil(h / G_UM))
        S = np.zeros((s.ny + 1, s.nx + 1), dtype=np.int64); S[1:, 1:] = s.m.cumsum(0).cumsum(1)
        tot = S[bh:, bw:] - S[:-bh, bw:] - S[bh:, :-bw] + S[:-bh, :-bw]      # [iy, ix] = occupied cells of the box at (ix, iy)
        e = int(math.ceil(edge / G_UM))
        ok = tot == 0
        ok[:e, :] = False; ok[:, :e] = False
        ok[max(0, ok.shape[0] - e):, :] = False; ok[:, max(0, ok.shape[1] - e):] = False
        iy, ix = np.nonzero(ok)
        if not len(ix):
            return None
        cx = ix * G_UM + w / 2; cy = iy * G_UM + h / 2
        k = int(np.argmin(np.abs(cx - tx) + np.abs(cy - ty)))
        return snap(ix[k] * G_UM), snap(iy[k] * G_UM)


def mkslot(name, cell, x, y, w, h, notes, extra=None):
    s = dict(name=name, cell=cell, kind='tile', parent='die', outline=dict(w=w, h=h), origin=dict(x=x, y=y, orient='R0'),
             pins=[], pin_status='FACES_ONLY', grant=GRANT, layer_cap='M5', signal_max_layer='M5', pg_layer='M5',
             strap_layer='M6', notes=notes)
    s.update(extra or {})
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contract', required=True); ap.add_argument('--manifest', required=True)
    ap.add_argument('--grants', default=str(D / 'grants_d4g.json'))
    ap.add_argument('--plan', default=str(D / 'plan/d4g_phy/compact.P.json'))
    ap.add_argument('--report', default=str(D / 'gen2e_homes/gen2e_homes_slots.json'))
    ap.add_argument('--png'); ap.add_argument('--check-only', action='store_true')
    a = ap.parse_args()
    g = load(a.grants); P = load(a.plan); C = load(a.contract); M = load(a.manifest)
    I = C['instances']; PL = M['placement']; HM = M.get('homes', {})
    die = next(s for s in g['slots'] if s['kind'] == 'die'); W, H = die['outline']['w'], die['outline']['h']
    rep = dict(tool='tools/hbm_die_v16/d4g_gen2e_grants_homes.py', lane='TW5-GEN2E 10-19', clearance_um=CLR, renamed={},
               moved={}, new={}, kept_gen2a=[], rescanned=[], violations=[])
    # 1. renames
    for s in g['slots']:
        if s['name'] in RENAME and RENAME[s['name']] in I:
            rep['renamed'][s['name']] = RENAME[s['name']]
            s['notes'] = (s.get('notes') or '') + f' | TW5-GEN2E 10-19: renamed {s["name"]} -> {RENAME[s["name"]]} (contract name; slot had no user)'
            s['name'] = RENAME[s['name']]
    slots = {s['name']: s for s in g['slots']}
    users = {}
    for n, v in I.items():
        if v.get('slot') in slots:
            users.setdefault(v['slot'], set()).add(n)
        if n in slots:
            users.setdefault(n, set()).add(n)
    used = lambda sn: bool(users.get(sn)) and slots[sn]['origin']['x'] + slots[sn]['origin']['y'] > 100
    # generated homes to grant (GEN2a rule not a slot / region / relay)
    gen = []
    for n, h in HM.items():
        r = h.get('rule', '')
        if n not in I or n not in PL or RELAY.match(n) or r.startswith(('planned relay', 'relay chain', 'region', 'grant slot', 'PC band', 'next to', 'owner plan block')):
            continue
        if n in slots and used(n):
            continue
        p = PL[n]
        if p['w'] * p['h'] < MIN_UM2:
            continue
        gen.append(n)
    manual = {f'hb_idx__{k}_{q}' for k in ('s', 'q', 'op') for q in Q} | {'hc_eng', 'wbk_SW', 'wbk_NW', 'wbk_SE', 'wbk_NE'}
    gen = [n for n in gen if n not in manual]
    # 2. occupancy: used slots (not the ones re-homed here) + plan blocks (not released) + GEN2a blocks without a slot
    occ = Occ(W, H)
    rehome = set(gen) | manual
    for sn, s in slots.items():
        if s['kind'] == 'die' or sn in rehome or not used(sn):
            continue
        occ.add(rect(s))
    for pn, b in P.items():
        if isinstance(b, dict) and 'x' in b and not RELEASE_PLAN.match(pn):
            occ.add((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
    for n, p in PL.items():
        if n in rehome or RELAY.match(n) or n not in I or (n in slots and used(n)):
            continue
        if p['w'] * p['h'] < 2000:
            continue
        occ.add((p['x'], p['y'], p['x'] + p['w'], p['y'] + p['h']))
    # centre lane channel (|x - W/2| < 200 um, N-S trunk lanes; the HC ring grants keep it clear too)
    occ.add((W / 2 - 200.0, 0.0, W / 2 + 200.0, H), clr=0.0)
    new = []

    def place(name, cell, x, y, w, h, notes, extra=None, why=''):
        r = (x, y, x + w, y + h)
        s = mkslot(name, cell, x, y, w, h, notes, extra)
        old = slots.get(name)
        if old is not None:
            rep['moved'][name] = dict(was=[old['origin']['x'], old['origin']['y'], old['outline']['w'], old['outline']['h']],
                                      now=[x, y, w, h], why=why)
            keep = {k: old[k] for k in ('clock_entry', 'io_budget', 'rtl_owner', 'version') if k in old}
            old.clear(); old.update(s); old.update(keep)
        else:
            g['slots'].append(s); slots[name] = s
            rep['new'][name] = dict(at=[x, y, w, h], why=why)
        occ.add(r); new.append(name)

    PHY = {h: rect(slots[f'phy_{h}']) for h in ('SW', 'NW')}
    # 3. hc_eng -> nearest free site to the 4 ring-hub centroid
    hubs = [rect(slots[f'hc_{q}']) for q in Q]
    tx = sum((r[0] + r[2]) / 2 for r in hubs) / 4; ty = sum((r[1] + r[3]) / 2 for r in hubs) / 4
    w, h = HC_ENG_WH; xy = occ.find(tx, ty, w, h)
    old = slots['hc_eng']
    place('hc_eng', I['hc_eng']['master'], xy[0], xy[1], w, h,
          f'TW5-GEN2E 10-19: HC root (ot_hbm_hc_root_static; std 0.144 mm2 + 2 SRAM) re-homed from the old 5,223 x 1,953 HC '
          f'engine slot at the SE die corner (on plan idxs_SE) to the free site nearest the 4 ring-hub centroid '
          f'({tx:.0f}, {ty:.0f}); area-sized outline; v15 pin windows dropped (die tools assign pins top-down)',
          dict(clock_entry=old.get('clock_entry'), io_budget=old.get('io_budget')), why='ring-hub centroid')
    # 4. IDX quarter scorers flush to the PHY inside idxs_<q>; query core + operand reader beside them
    for q in Q:
        n = f'hb_idx__s_{q}'; pw, ph_ = PL[n]['w'], PL[n]['h']
        w = h = snap(math.ceil(max(pw, ph_) / 21.6) * 21.6)
        north = q[0] == 'N'; west = q[1] == 'W'; pr = PHY['NW' if north else 'SW']; ib = P[f'idxs_{q}']
        x = snap(ib['x'] + ib['w'] - w) if west else snap(ib['x'])
        y = snap(ib['y']) if north else snap(ib['y'] + ib['h'] - h)
        place(n, I[n]['master'], x, y, w, h,
              f'TW5-GEN2E 10-19: IDX quarter scorer {q} in plan idxs_{q}, on its PHY-side edge (PHY / PC band at >= 60 um): '
              f'nearest legal site to its 4 svg peers (4 x 1,099 b on the PC band); was a peer-centroid home in a die corner',
              why='idxs plan block, PHY edge')
        sz = {k: (max(dw, snap(PL[f'hb_idx__{k}_{q}']['w'])), max(dh, snap(PL[f'hb_idx__{k}_{q}']['h'])))
              for k, (dw, dh) in (('q', (180.0, 180.0)), ('op', (216.0, 162.0)))}
        colw = max(v[0] for v in sz.values()); sp = CLR + 0.432
        sx = (x - sp - colw) if west else (x + w + sp)
        cy = (y + h) if not north else y          # column starts at the scorer edge away from the die edge
        for k in ('q', 'op'):
            m = f'hb_idx__{k}_{q}'; cw, ch = sz[k]
            yy = (cy - ch) if not north else cy
            cy = (yy - sp) if not north else (yy + ch + sp)
            place(m, I[m]['master'], snap(sx), snap(yy), cw, ch,
                  f'TW5-GEN2E 10-19: IDX {"query core" if k == "q" else "VM operand reader"} {q} beside its scorer '
                  f'hb_idx__s_{q} (GEN2c topology; the op-beside-VM-banks lever needs an IDX re-budget)', why='beside scorer')
    # 5. wbk: SM pair gap 2/3 (SW/NW) and 4/5 (SE/NE), on top of the PC band
    for q, (a_, b_) in (('SW', ('sm_SW2', 'sm_SW3')), ('NW', ('sm_NW2', 'sm_NW3')), ('SE', ('sm_SW4', 'sm_SW5')), ('NE', ('sm_NW4', 'sm_NW5'))):
        n = f'wbk_{q}'
        if n not in I:
            continue
        l, r = rect(slots[a_]), rect(slots[b_]); w, h = WBK_WH
        x = snap((l[2] + r[0]) / 2 - w / 2)
        pcy = max(P[f'pc_SW{k}']['y'] + P[f'pc_SW{k}']['h'] for k in range(8)) if q[0] == 'S' else \
            min(P[f'pc_NW{k}']['y'] for k in range(8))
        y = snap(pcy + CLR) if q[0] == 'S' else snap(pcy - CLR - h)
        place(n, I[n]['master'], x, y, w, h,
              f'TW5-GEN2E 10-19: write-back K port {q} in the SM pair gap {a_}/{b_} on the PC band edge, beside its vmks '
              f'consumers (4 x 1,156 b) on the way to hb_dbk_{q} (2,405 b); old slot sat E of the PHY beside nothing it talks to',
              why='SM pair gap above the PC band')
    # 6. generic generated homes, biggest first: target = bits^2-weighted centroid of the peers at their GEN2e positions
    #    (slot centre when the peer has a used / new slot, else its GEN2a site), as die_case_v16's generated-home rule,
    #    but against the GEN2e grants (renamed x-load slots, HC ring, moved hc_eng / IDX / wbk); nearest clear site
    adj = {}
    for e in C['edges']:
        s_, t_ = e['source'][0], e['sink'][0]
        if s_ != t_:
            adj.setdefault(s_, {}); adj[s_][t_] = adj[s_].get(t_, 0) + e['bits']
            adj.setdefault(t_, {}); adj[t_][s_] = adj[t_].get(s_, 0) + e['bits']

    def pos(m):
        for sn in (m, I.get(m, {}).get('slot')):
            if sn in slots and (sn in new or used(sn)) and sn != 'die':
                r = rect(slots[sn]); return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        if m in PL:
            q_ = PL[m]; return q_['x'] + q_['w'] / 2, q_['y'] + q_['h'] / 2
        return None
    for n in sorted(gen, key=lambda n: -PL[n]['w'] * PL[n]['h']):
        p = PL[n]; w = snap(math.ceil(p['w'] / 0.216) * 0.216); h = snap(math.ceil(p['h'] / 0.216) * 0.216)
        pts = [(pos(m), b) for m, b in adj.get(n, {}).items() if pos(m)]
        wt = sum(b * b for _, b in pts)
        if wt:
            tx = sum(xy_[0] * b * b for xy_, b in pts) / wt; ty = sum(xy_[1] * b * b for xy_, b in pts) / wt
        else:
            tx, ty = p['x'] + p['w'] / 2, p['y'] + p['h'] / 2
        xy = occ.find(tx, ty, w, h)
        if xy is None:
            rep['violations'].append([n, 'no free site']); continue
        d = abs(xy[0] + w / 2 - tx) + abs(xy[1] + h / 2 - ty)
        d2a = abs(xy[0] - p['x']) + abs(xy[1] - p['y'])
        (rep['kept_gen2a'] if d2a < 1.0 else rep['rescanned']).append([n, round(d, 1), round(d2a, 1)])
        place(n, I[n]['master'], xy[0], xy[1], w, h,
              f'TW5-GEN2E 10-19: grant slot for a GEN2a generated home ({HM[n]["rule"][:60]}): nearest clear site to the '
              f'bits^2 centroid of {len(pts)} peers at their GEN2e positions ({tx:.0f}, {ty:.0f}), {d:.0f} um off it; '
              f'{d2a:.0f} um from its GEN2a site', why=f'peer centroid, {d:.0f} um off')
    # 7. checks
    S = [(s['name'], rect(s)) for s in g['slots'] if s['kind'] != 'die' and used(s['name']) and s['name'] not in new] + \
        [(n, rect(slots[n])) for n in new]
    for i, (n1, r1) in enumerate(S):
        for n2, r2 in S[i + 1:]:
            if (n1 in new or n2 in new) and gap(r1, r2) < CLR - 1e-6 and slots[n1].get('ring_block') is None:
                rep['violations'].append([n1, n2, round(gap(r1, r2), 2)])
    for n in new:
        r1 = rect(slots[n])
        if not (0 <= r1[0] and r1[2] <= W and 0 <= r1[1] and r1[3] <= H):
            rep['violations'].append([n, 'die'])
        for pn, b in P.items():
            if isinstance(b, dict) and 'x' in b and not RELEASE_PLAN.match(pn):
                if gap(r1, (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])) < -1e-6:
                    rep['violations'].append([n, f'plan:{pn}', round(gap(r1, (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])), 2)])
    rep['summary'] = dict(renamed=len(rep['renamed']), moved=len(rep['moved']), new=len(rep['new']),
                          kept_gen2a=len(rep['kept_gen2a']), rescanned=len(rep['rescanned']), violations=len(rep['violations']))
    if not a.check_only:
        Path(a.grants).write_text(json.dumps(g, indent=1) + '\n')
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    if a.png:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        f, ax = plt.subplots(figsize=(10, 15.7))
        for pn, b in P.items():
            if isinstance(b, dict) and 'x' in b:
                ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], fill=False, ec='0.75', lw=0.4))
        for s in g['slots']:
            if s['kind'] == 'die' or not (used(s['name']) or s['name'] in new):
                continue
            r = rect(s); c = 'tab:red' if s['name'] in new else ('tab:green' if s.get('ring_block') else 'tab:blue')
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=c, alpha=0.35 if s['name'] in new else 0.2, ec=c, lw=0.5))
            if s['name'] in new and (r[2] - r[0]) * (r[3] - r[1]) > 30000:
                ax.text(r[0], r[3], s['name'], fontsize=4)
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
        ax.set_title(f'GEN2e grants: red = new/moved slots ({len(new)}), green = HC ring, blue = other used slots, grey = plan', fontsize=8)
        f.savefig(a.png, dpi=150, bbox_inches='tight')
    print(json.dumps(rep['summary']))
    for v in rep['violations'][:20]:
        print('  VIOL', v)
    raise SystemExit(1 if rep['violations'] else 0)


if __name__ == '__main__':
    main()
