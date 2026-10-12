"""Hierarchy-contract findings drawn on the layout (layout viewer 'Contract' overlay).

Uses the checks of tools/hier_contract/child_lint.py (check_pg, face_access, the strap-layer rule) on abstracts built
from the routed DB extraction, so each finding carries the exact layout shapes it is about:

  element  this element as a hard child of its parent: pins = block pins (bterms) + the PG nets' special-wire shapes
           (what write_abstract_lef emits as the PG pins); OBS = every other routed / placed shape (non-bloat abstract)
             (b) PG pins not full stripes   (c) signals / OBS on the parent strap layer   (f) covered edge (face) pins
  macro    every hard macro placed in this element, from its own master (pins + OBS), drawn at each placement, plus
             (grid) off-track macro pins: the DRT-0419 centre test of tools/check_macro_track_alignment.check_placement,
             against this DB's own track grids
Each finding: id, scope, check, sev (FAIL / WARN), title, reason, fix, inst, shapes [[layer, x0, y0, x1, y1, role]]
(DBU, role pin / obs / stripe / short), bbox, layers (whole layers worth lighting).
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent / 'hier_contract'):
    sys.path.insert(0, str(p))
import child_lint as CL  # noqa: E402

CAP = 400
FIX_B = ('give VDD and VSS each >= %d full-length stripes (>= 90%% of the span, spread >= 50%%) on ONE common top PG layer '
         '(pdn: add_pdn_stripe ... -extend_to_boundary on that layer); tools/hier_contract/schema.md PG rule' % CL.MIN_STRIPES)
FIX_C = ('stop child signals below the parent strap layer: route with MAX_ROUTING_LAYER = the PG layer (or own the layer '
         'below as full PG stripes and leave the strap layer free); preamble UPDATE 3, PDN-0233/0232')
FIX_GRID = ('move the macro origin onto the routing-track lattice (tools/check_macro_track_alignment.py snap_joint_nm / the '
            'placement hooks\' ot_snap_joint); tools/hier_contract/macro_grid_lint.py refuses such a placement')


def _um(v, dbu):
    return float(v) / dbu


def build_abstract(name, W, H, pins, obs, dbu):
    """child_lint macro dict (um, origin at the abstract's lower-left)"""
    return dict(name=name, W=W / dbu, H=H / dbu,
                pins={n: dict(use=p['use'], direction='', rects=[(L, _um(a, dbu), _um(b, dbu), _um(c, dbu), _um(d, dbu)) for L, a, b, c, d in p['rects']])
                      for n, p in pins.items()},
                obs=[(L, _um(a, dbu), _um(b, dbu), _um(c, dbu), _um(d, dbu)) for L, a, b, c, d in obs], bloat_comment=False)


def bbox_of(shapes):
    if not shapes: return None
    a = np.array([s[1:5] for s in shapes])
    return [int(a[:, 0].min()), int(a[:, 1].min()), int(a[:, 2].max()), int(a[:, 3].max())]


def finding(F, **kw):
    kw['id'] = len(F)
    sh = kw.get('shapes') or []
    kw['n_shapes'] = kw.pop('n_total', None) or len(sh)
    kw['shapes'] = sh[:CAP]
    kw.setdefault('bbox', bbox_of(sh))
    F.append(kw)


def metal_of(names, li):
    return CL.metal(names[li]) if 0 <= li < len(names) else None


def checks_on(F, scope, inst, m, pin_geo, obs_geo, all_obs, names, lname_to_idx):
    """run child_lint (b) (c) (f) on abstract m; pin_geo {pin: [(layer idx, x0, y0, x1, y1) abs DBU]}, obs_geo [(li, ...)]
    absolute DBU shapes for drawing (for the element: only the shapes over face pins); all_obs: numpy (n, 5) of every OBS
    shape for the strap-layer count (None: use obs_geo)"""
    frame = pin_geo['__frame__']
    pin_geo = {k: v for k, v in pin_geo.items() if k != '__frame__'}
    pg = CL.check_pg(m)
    pg_L = CL.metal(pg['top_layer'])
    strap_L = pg_L + 1 if pg_L else None
    where = ('macro %s (%s)' % (inst, m['name'])) if scope == 'macro' else 'this element as a hard child'
    pgpins = {n for n, p in m['pins'].items() if CL.is_pg(n, p)}
    if not pg['ok']:
        top = pg['top_layer']
        shapes = [[li, a, b, c, d, 'stripe'] for n in pgpins for (li, a, b, c, d) in pin_geo.get(n, []) if names[li] == top]
        nets = '; '.join('%s: %d full stripes on %s, %.0f%% spread, %.0f%% of top-layer PG metal' % (n, e['stripes'], e['top_layer'], 100 * e['spread'], 100 * e['coverage'])
                         for n, e in pg['nets'].items())
        finding(F, scope=scope, inst=inst, check='b', sev='FAIL', title='PG pins are not full stripes (%s)' % where,
                reason='child_lint (b): ' + '; '.join(pg['why']) + ('. ' + nets if nets else ''), fix=FIX_B,
                shapes=shapes, layers=[lname_to_idx[top]] if top in lname_to_idx else [])
    if strap_L:
        hi_sig = [[li, a, b, c, d, 'pin'] for n, p in pin_geo.items() if n not in pgpins for (li, a, b, c, d) in p if (metal_of(names, li) or 0) >= strap_L]
        if all_obs is not None:   # numpy (n, 5): count everything, draw a sample
            lm = np.array([metal_of(names, i) or 0 for i in range(len(names))])
            sel = all_obs[lm[all_obs[:, 0]] >= strap_L] if len(all_obs) else all_obs
            hi_obs = [[int(r[0]), int(r[1]), int(r[2]), int(r[3]), int(r[4]), 'obs'] for r in sel[:CAP]]
            n_hi_obs = len(sel); lays_obs = sorted(set(int(v) for v in np.unique(sel[:, 0]))) if len(sel) else []
        else:
            hi_obs = [[li, a, b, c, d, 'obs'] for (li, a, b, c, d) in obs_geo if (metal_of(names, li) or 0) >= strap_L]
            n_hi_obs = len(hi_obs); lays_obs = sorted({s[0] for s in hi_obs})
        hi_pg = sorted({names[li] for n in pgpins for (li, a, b, c, d) in pin_geo.get(n, []) if (metal_of(names, li) or 0) >= strap_L})
        if hi_sig or hi_obs or hi_pg:
            lays = sorted({s[0] for s in hi_sig} | set(lays_obs))
            finding(F, scope=scope, inst=inst, check='c', sev='FAIL', title='Signals on the parent strap layer M%d+ (%s)' % (strap_L, where),
                    reason='child_lint (c): strap layer M%d+ not clear: %d OBS shapes on %s, %d signal-pin shapes, PG on %s (PG layer M%d)'
                           % (strap_L, n_hi_obs, '/'.join(names[l] for l in lays) or '-', len(hi_sig), '/'.join(hi_pg) or '-', pg_L),
                    fix=FIX_C, shapes=hi_sig + hi_obs, layers=lays, n_total=len(hi_sig) + n_hi_obs)
    fa = CL.face_access(m)
    if fa['blocked_above']:
        # the blocked pins with the OBS above them, in placed coordinates
        shapes = []
        obs_by = {}
        for s in obs_geo: obs_by.setdefault(s[0], []).append(s)
        dbW = m['W']; dbH = m['H']
        for n, rs in pin_geo.items():
            if n in pgpins: continue
            for (li, a, b, c, d) in rs:
                L = metal_of(names, li)
                if L is None: continue
                up = lname_to_idx.get('M%d' % (L + 1))
                hits = [o for o in obs_by.get(up, []) if o[1] < c and o[3] > a and o[2] < d and o[4] > b]
                if hits and _on_face(a, b, c, d, frame):
                    shapes.append([li, a, b, c, d, 'pin'])
                    shapes += [[o[0], o[1], o[2], o[3], o[4], 'obs'] for o in hits[:4]]
        finding(F, scope=scope, inst=inst, check='f', sev='FAIL', title='Covered edge pins (%s)' % where,
                reason='child_lint (f): %d of %d face pins have OBS on the layer directly above the pin (no via access from the parent; '
                       'DRT-0073 class), e.g. %s' % (fa['blocked_above'], fa['face_pins'], ', '.join(fa['examples'][:3])),
                fix='fix in the child: ' + CL.FACE_FIX, shapes=shapes, layers=sorted({s[0] for s in shapes}))
    return pg


def _on_face(a, b, c, d, frame):
    x0, y0, x1, y1 = frame
    e = 2
    return b <= y0 + e or d >= y1 - e or a <= x0 + e or c >= x1 - e


def lint(meta, rects, vias, insts, inets, mrects):
    F = []
    dbu = meta['dbu']
    names = [l['name'] for l in meta['layers']]
    lname_to_idx = {n: i for i, n in enumerate(names)}
    sig = meta['net_sig']
    die = meta['die']
    ox, oy = die[0], die[1]
    # ---------------- element as hard child
    def use_of(net):
        s = sig[net - 1] if net > 0 else 'SIGNAL'
        return s if s in ('POWER', 'GROUND') else 'SIGNAL'
    netname = meta['nets']
    pins, pin_geo = {}, {}
    bt = rects[rects[:, 6] == 4]
    pgn = {i + 1 for i, s in enumerate(sig) if s in ('POWER', 'GROUND')}
    sp = rects[(rects[:, 6] >= 1) & (rects[:, 6] <= 3) & np.isin(rects[:, 5], list(pgn) or [-1])]
    for r in np.concatenate([bt, sp]):
        n = netname[r[5] - 1] if r[5] > 0 else '(unconnected)'
        L = names[r[0]]
        p = pins.setdefault(n, dict(use=use_of(int(r[5])), rects=[]))
        p['rects'].append((L, r[1] - ox, r[2] - oy, r[3] - ox, r[4] - oy))
        pin_geo.setdefault(n, []).append((int(r[0]), int(r[1]), int(r[2]), int(r[3]), int(r[4])))
    pin_geo['__frame__'] = tuple(die)
    # OBS: every other shape.  Only the ones that can matter are passed on: shapes on routing layers above any face pin
    # footprint (f), and every shape on a layer >= the strap layer (c) -- the strap layer is known after check_pg.
    other = rects[(rects[:, 6] == 0) | (rects[:, 6] >= 5) | ((rects[:, 6] >= 1) & (rects[:, 6] <= 3) & ~np.isin(rects[:, 5], list(pgn) or [-1]))]
    other = np.concatenate([other, mrects]) if len(mrects) else other
    m0 = build_abstract(meta['top'], die[2] - die[0], die[3] - die[1], {k: v for k, v in pins.items()}, [], dbu)
    pg0 = CL.check_pg(m0)
    pg_L = CL.metal(pg0['top_layer'])
    strap_L = pg_L + 1 if pg_L else None
    lay_metal = np.array([CL.metal(n) or 0 for n in names])
    # only face pins matter to (f): restrict the candidates to shapes in the boundary band the pins reach into
    band = 0
    for p in pins.values():
        for (L, a, b, c, d) in p['rects']:
            band = max(band, min(c, die[2] - die[0] - a), min(d, die[3] - die[1] - b))
    band = min(band, 5 * dbu) + 2
    inb = (other[:, 1] < die[0] + band) | (other[:, 3] > die[2] - band) | (other[:, 2] < die[1] + band) | (other[:, 4] > die[3] - band)
    cand_idx = np.nonzero(inb)[0]; cand = other[cand_idx]
    keep = np.zeros(len(other), dtype=bool)
    for n, p in pins.items():
        if p['use'] != 'SIGNAL': continue
        for (L, a, b, c, d) in p['rects']:
            Lm = CL.metal(L)
            if not Lm: continue
            up = lname_to_idx.get('M%d' % (Lm + 1))
            if up is None: continue
            A, B, C, D = a + ox, b + oy, c + ox, d + oy
            if not (B <= die[1] + 2 or D >= die[3] - 2 or A <= die[0] + 2 or C >= die[2] - 2): continue   # not a face pin
            hit = (cand[:, 0] == up) & (cand[:, 1] < C) & (cand[:, 3] > A) & (cand[:, 2] < D) & (cand[:, 4] > B)
            keep[cand_idx[hit]] = True
    ob = other[keep]
    obs_geo = [(int(r[0]), int(r[1]), int(r[2]), int(r[3]), int(r[4])) for r in ob]
    m = build_abstract(meta['top'], die[2] - die[0], die[3] - die[1], pins,
                       [(names[r[0]], r[1] - ox, r[2] - oy, r[3] - ox, r[4] - oy) for r in ob], dbu)
    pg = checks_on(F, 'element', None, m, pin_geo, obs_geo, other[:, :5], names, lname_to_idx)
    summary = dict(element=dict(pg_layer=pg['top_layer'], strap_layer=('M%d' % strap_L) if strap_L else None, pg=pg['nets'],
                                face=CL.face_access(m)))
    # ---------------- hard macros placed here
    masters = meta['masters']
    npins = np.array([len(mm['pins']) for mm in masters], dtype=np.int64)
    ioff = np.zeros(len(insts) + 1, dtype=np.int64); ioff[1:] = np.cumsum(npins[insts[:, 3]])
    from lv_tile import expand_master
    tracks = {}
    for li, l in enumerate(meta['layers']):
        if l['type'] == 'ROUTING' and l.get('tracks'):
            ax = 'y' if l.get('dir') == 'HORIZONTAL' else 'x'
            tracks[li] = (ax, [tuple(p) for p in l['tracks'][ax]])
    mres = []
    for i in np.nonzero(insts[:, 8] & 1)[0]:
        mm = masters[insts[i, 3]]
        if not mm['boxes']: continue
        b = np.array(mm['boxes'], dtype=np.int64)
        code, X, Y = int(insts[i, 2]), int(insts[i, 0]), int(insts[i, 1])
        pb = expand_master(b[:, 1:5], code, X, Y)
        bb = insts[i, 4:8]
        mp, mgeo, mobs, mobs_geo = {}, {}, [], []
        for k in range(len(b)):
            li, pi = int(b[k, 0]), int(b[k, 5])
            g = (li, int(pb[k, 0]), int(pb[k, 1]), int(pb[k, 2]), int(pb[k, 3]))
            loc = (names[li], g[1] - bb[0], g[2] - bb[1], g[3] - bb[0], g[4] - bb[1])
            if pi >= 0:
                pn = mm['pins'][pi]['name']
                u = mm['pins'][pi]['sig']
                p = mp.setdefault(pn, dict(use=u if u in ('POWER', 'GROUND') else 'SIGNAL', rects=[]))
                p['rects'].append(loc); mgeo.setdefault(pn, []).append(g)
            else:
                mobs.append(loc); mobs_geo.append(g)
        mgeo['__frame__'] = tuple(int(v) for v in bb)
        am = build_abstract(mm['name'], bb[2] - bb[0], bb[3] - bb[1], mp, mobs, dbu)
        name = meta['insts'][i]
        checks_on(F, 'macro', name, am, mgeo, mobs_geo, None, names, lname_to_idx)
        # off-track signal pins (DRT-0419 centre test)
        off = []
        worst = 0
        for pn, gs in mgeo.items():
            if pn == '__frame__' or mp[pn]['use'] != 'SIGNAL': continue
            for (li, a, bq, c, d) in gs:
                if li not in tracks: continue
                ax, pats = tracks[li]
                c2 = (bq + d) if ax == 'y' else (a + c)
                best = None
                for (o, cnt, st) in pats:
                    k = (c2 - 2 * o) / (2.0 * st)
                    for kk in (int(np.floor(k)), int(np.ceil(k))):
                        if 0 <= kk < cnt:
                            dd = abs(c2 - 2 * (o + kk * st)) / 2.0
                            best = dd if best is None else min(best, dd)
                if best is None or best > 0:
                    off.append([li, a, bq, c, d, 'pin']); worst = max(worst, best or 0)
        if off:
            lays = sorted({s[0] for s in off})
            finding(F, scope='macro', inst=name, check='grid', sev='FAIL', title='Off-grid macro: %d signal pins off their routing tracks (%s)' % (len(off), name),
                    reason='DRT-0419 centre test (tools/check_macro_track_alignment.check_placement) against this DB\'s track grids: %d pin shapes on %s '
                           'have their centre off every preferred-direction track (worst %.1f nm) with the macro at origin (%.3f, %.3f) um, %s'
                           % (len(off), '/'.join(names[l] for l in lays), worst, X / dbu, Y / dbu, meta['orients'][code]),
                    fix=FIX_GRID, shapes=off, layers=lays)
        mres.append(dict(inst=name, master=mm['name'], off_track=len(off)))
    summary['macros'] = mres
    return dict(schema='opentallas.layout_viewer.lint.v1', source='tools/hier_contract/child_lint.py (b, c, f) + DRT-0419 centre test',
                findings=F, summary=summary)
