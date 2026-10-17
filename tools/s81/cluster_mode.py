"""S81 hierarchical die top (H-C27 c27, --cluster-mode in tools/dsrom_s81_fulldie.py; owner 10-16: flat die GRT does not
finish, so the ROM-column field becomes replicated column clusters hardened once and the die top routes only the
inter-cluster forwarded-clock transport).

Geometry (opt-in, canonical layouts only):
  * column pitch widened to --cluster-pitch (default 1,210.464 um = frame 1,139.616 + top transit channel 62.208 + seam
    8.64; the S-DIE transit110 request pitch).  West columns keep the die-W anchor and move toward the hub, east columns
    keep the die-E anchor (the hub is a fixed body; transit110 measured 0 conflicts against its 113 fixed bodies);
  * frame origins snapped to an 8.64-um y lattice, so every frame-relative member offset is lattice-identical;
  * the frame keeps its own RSC strip (the column's return-tree relays stay INSIDE the cluster); the new channel east of
    each frame is die-top only: the canonical roadmap's per-column vertical lane moves from the RSC strip into it;
  * the street below each frame is split: the cfifo row (cluster) on top, the die-top transit band below it.  Every
    cluster rectangle is a reserved box for die-top station search (no top station may land inside a cluster).
Die top (after finalize_r8): each frame_<r> region + cf<r> collapses into ONE instance col<r> of its class master
dsfd_s81_col_<class> (class = height x pair count); its ports are the cfifo's boundary pins (xd/xf, xd2/xf2 forwarded
entries, rd/rf forwarded return, ck_col = clk_stream, rst_col = rst_stream), all on the S (street) face.
"""
from __future__ import annotations

import collections
import json
import math
import tempfile
from pathlib import Path

PORT_RENAME = {'ck': 'ck_col', 'rst': 'rst_col'}
CLASS_NAMES = {(2695.68, 15): 'h9', (2985.12, 15): 'h10a15', (2985.12, 16): 'h10a16', (3000.24, 16): 'h10b'}


def snap(v, g):
    return round(round(v / g) * g, 4)


# ------------------------------------------------------------------------------------------------ layout
SEAM_ROAD_UM = 60.48     # the die-top vertical road opened between W columns 0 and 1 (W columns 1.. move E by this)


def _align_column(fs, ref_bottoms, top_limit, first_street=259.2, street=388.8):
    """re-place one column's frames (any order) so every street bottom equals a street bottom of the neighbour column
    (ref_bottoms, ascending; the last frame may also stand on the neighbour's last street).  Returns {root: new y} or
    None.  Depth-first over frame orders by height class; streets keep >= 388.8 (first >= 259.2)."""
    hs = sorted({f['height_um'] for f in fs})
    by_h = {h: [f for f in fs if f['height_um'] == h] for h in hs}
    n = len(fs)

    def rec(k, prev_top, used, counts):
        if k == n:
            return []
        for si, sb in enumerate(ref_bottoms):
            if si in used or sb < prev_top - 1e-6:
                continue
            st = first_street if k == 0 and sb - prev_top < street else street
            for h in hs:
                if counts[h] == 0:
                    continue
                y = sb + st
                top = y + h
                nxt = [b for b in ref_bottoms[si + 1:]]
                if top > top_limit:
                    continue
                if k < n - 1 and not any(b >= top - 1e-6 for b in nxt):
                    continue
                counts[h] -= 1
                rest = rec(k + 1, top, used | {si}, counts)
                counts[h] += 1
                if rest is not None:
                    return [(h, y)] + rest
        return None
    plan = rec(0, -1e9, frozenset(), {h: len(v) for h, v in by_h.items()})
    if plan is None:
        return None
    out, pools = {}, {h: list(v) for h, v in by_h.items()}
    for h, y in plan:
        out[pools[h].pop(0)['root']] = y
    return out


def cluster_layout(d, y_snap, west_seam=True, align_hub_column=False):
    """--cluster-mode geometry on the canonical record (in place); returns a receipt.
    * y lattice: every column's stack shifts UNIFORMLY onto the y_snap lattice (all frames one lattice phase -> one
      physical signature per class; W columns 2-6 started at 3,061.256, the others at 20);
    * west_seam: W columns 1.. move E by SEAM_ROAD_UM, opening a vertical die-top road between W columns 0 and 1 (the
      W field is irregular: column 1's streets do not all meet a neighbour street);
    * align_hub_column: the W hub-side column (large free height) is re-placed so each of its streets sits on a street
      of its W neighbour (exact band overlap; frames may change order inside the column, roots keep their ids)."""
    cols = sorted(d['columns'], key=lambda c: c['x_um'])
    xs = [c['x_um'] for c in cols]
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    nw = max(range(len(gaps)), key=gaps.__getitem__) + 1
    members = {}
    for c in cols:
        members[round(c['x_um'], 4)] = sorted((f for f in d['placements'] if abs(f['origin_um'][0] - c['x_um']) < 1e-6),
                                              key=lambda f: f['origin_um'][1])
    rec = dict(y_snap_um=y_snap, transport='street_only', west_columns=nw)
    if align_hub_column:
        ref = members[round(xs[nw - 2], 4)]
        ref_b = sorted([ref[0]['origin_um'][1] - 259.2] + [f['origin_um'][1] - 388.8 for f in ref[1:]])
        fs = members[round(xs[nw - 1], 4)]
        # its top free band must still meet the neighbour's last street (the W top row joins through it)
        newy = _align_column(fs, ref_b, min(d['die_outline_um'][1] - 30.0, ref_b[-1] + 150.0))
        assert newy is not None, '--cluster-mode: the W hub-side column cannot align to its neighbour streets'
        rec['hub_column_realigned'] = {str(r): [round(next(f['origin_um'][1] for f in fs if f['root'] == r), 3), round(y, 3)]
                                       for r, y in newy.items()}
        for f in fs:
            f['origin_um'] = [f['origin_um'][0], round(newy[f['root']], 4)]
        fs.sort(key=lambda f: f['origin_um'][1])
        c = cols[nw - 1]
        c['y0_um'] = round(fs[0]['origin_um'][1] - 388.8, 4)
    # W columns between die-W column 0 and the hub-side column: slide each stack UP inside its free top margin to the
    # offset (2.16 steps) that maximises street-band overlaps >= 60 um with its neighbours
    def bands_of(x_):
        fs_ = members[round(x_, 4)]
        out_, prev_ = [], None
        for f in fs_:
            lo_ = f['origin_um'][1] - (388.8 if prev_ is not None else f['origin_um'][1] - cols_y0[round(x_, 4)])
            out_.append((lo_, f['origin_um'][1] - 108.4))
            prev_ = f
        return out_
    cols_y0 = {round(c['x_um'], 4): c['y0_um'] for c in cols}

    def score(k_):
        n_ = 0
        for j_ in (k_ - 1, k_ + 1):
            if 0 <= j_ < nw:
                for a0, a1 in bands_of(xs[k_]):
                    n_ += sum(1 for b0, b1 in bands_of(xs[j_]) if min(a1, b1) - max(a0, b0) >= 60.0)
        return n_
    slides = {}
    for k in range(1, nw - 1):
        fs = members[round(xs[k], 4)]
        slack = d['die_outline_um'][1] - 30.0 - (fs[-1]['origin_um'][1] + fs[-1]['height_um'])
        best = (score(k), 0.0)
        base = [f['origin_um'][1] for f in fs]
        y0b = cols_y0[round(xs[k], 4)]
        steps = int(max(0.0, slack) // 2.16)
        for t in range(1, steps + 1):
            dy_ = t * 2.16
            for f, y_ in zip(fs, base):
                f['origin_um'][1] = y_ + dy_
            cols_y0[round(xs[k], 4)] = y0b + dy_
            sc = score(k)
            if sc > best[0]:
                best = (sc, dy_)
        for f, y_ in zip(fs, base):
            f['origin_um'][1] = round(y_ + best[1], 4)
        cols_y0[round(xs[k], 4)] = y0b + best[1]
        cols[k]['y0_um'] = round(y0b + best[1], 4)
        if best[1]:
            slides[str(round(xs[k], 3))] = round(best[1], 3)
    rec['w_column_slides_um'] = slides
    dys = {}
    for c in cols:
        fs = members[round(c['x_um'], 4)]
        y_first = fs[0]['origin_um'][1]
        dy = round(snap(y_first, y_snap) - y_first, 4)
        for f in fs:
            f['origin_um'] = [f['origin_um'][0], round(f['origin_um'][1] + dy, 4)]
            assert abs(f['origin_um'][1] / y_snap - round(f['origin_um'][1] / y_snap)) < 1e-6, ('y off lattice', f['root'])
        for a, b in zip(fs, fs[1:]):
            assert b['origin_um'][1] - a['origin_um'][1] - a['height_um'] >= 388.8 - 1e-6, ('street closed', a['root'], b['root'])
        top = fs[-1]['origin_um'][1] + fs[-1]['height_um']
        assert top <= d['die_outline_um'][1] - 10.0 and fs[0]['origin_um'][1] >= 200.0, ('column off the die', c['x_um'], dy)
        c['y0_um'] = round(c['y0_um'] + dy, 4)
        c['y1_um'] = round(max(c['y1_um'], top + 4.32), 4)
        dys[round(c['x_um'], 3)] = dy
    if west_seam:
        # two W seam roads: between W columns 0|1 and between the last two W columns (nw-2 | nw-1)
        for k, c in enumerate(cols[1:nw], start=1):
            sh = SEAM_ROAD_UM * (2 if k == nw - 1 else 1)
            for f in members[round(c['x_um'], 4)]:
                f['origin_um'] = [round(f['origin_um'][0] + sh, 4), f['origin_um'][1]]
            c['x_um'] = round(c['x_um'] + sh, 4)
        rec['west_seams'] = [[0, 1], [nw - 2, nw - 1]]
        rec['west_seam_um'] = SEAM_ROAD_UM
    d['frames'] = {f['root']: f for f in d['placements']}
    rec['column_dy_um'] = {str(k): v for k, v in dys.items()}
    return rec


def cluster_box(G, f):
    """(x0, y0, x1, y1) of the column cluster of frame record f: frame width x (cfifo row bottom .. frame top)."""
    y0 = f['y'] - 4.32 - G.CF_WH[1] - 4.32
    if G.PQ_ROOTS:
        y0 -= G.PQ_ROOT_ROW
    return (f['x'], y0, f['x'] + G.COL_W8, f['y'] + f['h'])


ROW_X, ROW_R = 64.8 + 15, 8.64 + 20      # the canonical street rows (broadcast / return) above the street bottom


def street_bands(G, m):
    """column index -> [(key, lo, hi)]: the die-top transit band of every street (below the cluster box) and the free
    band above the column's top frame (key ('top', i)); lo = street bottom, hi = cluster box bottom / die top margin."""
    d = m['canonical_layout']
    cols = sorted(d['columns'], key=lambda c: c['x_um'])
    out = {i: [] for i in range(len(cols))}
    for r, f in m['frames'].items():
        x, a, x1, b = f['street']
        out[f['column_index']].append((r, a, cluster_box(G, f)[1]))
    for i, c in enumerate(cols):
        top = max(f['y'] + f['h'] for f in m['frames'].values() if f['column_index'] == i)
        hi = G.DIE[1] - 20.432
        if hi - top >= 120.0:
            out[i].append((('top', i), top + 4.32, hi))
    for i in out:
        out[i].sort(key=lambda t: t[1])
    return cols, out


def patch_corridors(G, m, cor):
    """street-only: no die-top station in a column (rsclane gone, cfstreet = band below the cluster, clusters reserved);
    the free band above each column top and the die-W edge corridor are transit space."""
    for k in [k for k in cor if k.startswith('rsclane')]:
        del cor[k]
    cols, bands = street_bands(G, m)
    for i, rows in bands.items():
        x = cols[i]['x_um']
        for key, lo, hi in rows:
            assert hi - lo >= 120.0, ('transit band too thin', key, round(hi - lo, 2))
            name = f'cfstreet{key}' if not isinstance(key, tuple) else f'cfstreet_top{i}'
            cor[name] = (x + .432, lo + .432, x + G.COL_W8 - .432, hi - .432)
    # die-W edge road: from the die edge margin (link column included: its occupied link stations stay obstacles) to
    # the outer W column, full height
    x1 = cols[0]['x_um'] - 4.32
    assert x1 - 20.432 >= 60.0, ('no die-W edge road', x1)
    cor['cfstreet_edgeW'] = (20.432, 20.432, x1, G.DIE[1] - 20.432)
    for i in range(len(cols) - 1):
        gap = cols[i + 1]['x_um'] - (cols[i]['x_um'] + G.COL_W8)
        if 50.0 <= gap < 1000.0:
            cor[f'cfstreet_seam{i}'] = (cols[i]['x_um'] + G.COL_W8 + .432, 20.432, cols[i + 1]['x_um'] - .432, G.DIE[1] - 20.432)
    for r, f in m['frames'].items():
        bx = cluster_box(G, f)
        if (*bx, f'col_cluster:{r}') not in G.RSV_RECTS:
            G.RSV_RECTS.append((*bx, f'col_cluster:{r}'))
    m['cluster_boxes'] = {r: cluster_box(G, f) for r, f in m['frames'].items()}


def street_roadmap(road, G, m, cols, nw, return_lanes):
    """canonical Roadmap, street-only: rows only inside street transit bands; columns joined where their bands overlap
    (>= 30 um after 10-um margins) by a horizontal crossing at the overlap middle; S14 entries on the hub-side columns;
    the die-W edge corridor joins the outer W column's bands.  No vertical edge inside a column cluster."""
    _, bands = street_bands(G, m)
    off = 15.12 if return_lanes else G.RSC_W / 2
    road.sx = {i: c['x_um'] + G.COL_W8 - off for i, c in enumerate(cols)}
    rows_of = {}
    for i, rows in bands.items():
        for key, lo, hi in rows:
            pts = []
            for kind, o in (('x', ROW_X), ('r', ROW_R)):
                y = lo + o
                assert y < hi - 20.0, ('street row above the band', key, kind, round(y, 2), round(hi, 2))
                node = (road.sx[i], y)
                pts.append(node)
                if not isinstance(key, tuple):
                    road.rootnode[(key, kind)] = node
            road.add(pts[0], pts[1])
            rows_of[(i, key)] = pts
    # crossings between neighbouring columns of one half
    for i in range(len(cols) - 1):
        j = i + 1
        if i == nw - 1:
            continue
        for ki, lo_i, hi_i in bands[i]:
            for kj, lo_j, hi_j in bands[j]:
                lo, hi = max(lo_i, lo_j) + 10.0, min(hi_i, hi_j) - 10.0
                if hi - lo < 30.0:
                    continue
                yc = round((lo + hi) / 2, 3)
                A, B = (road.sx[i], yc), (road.sx[j], yc)
                road.add(A, B)
                for p in rows_of[(i, ki)]:
                    if p != A:
                        road.add(A, p)
                for p in rows_of[(j, kj)]:
                    if p != B:
                        road.add(B, p)
    # S14 entries
    for i in (nw - 1, nw):
        side = 'W' if i == nw - 1 else 'E'
        sx = G.s14_x(m, side, 'xdn')
        if side == 'W':
            sx = max(sx, cols[i]['x_um'] + G.COL_W8 + G.stn_dims([1026], False)[0] / 2 + .864)
        for key, lo, hi in bands[i]:
            for p in rows_of[(i, key)]:
                e = (sx, p[1])
                road.add(e, p)
                road.entry.setdefault(side, []).append(e)
    # die-W edge corridor: a vertical road joining the outer W column's bands
    ew = road.cor.get('cfstreet_edgeW')
    if ew:
        ex = round((ew[0] + ew[2]) / 2, 3)
        nodes = []
        for key, lo, hi in bands[0]:
            for p in rows_of[(0, key)]:
                e = (ex, p[1])
                road.add(e, p)
                nodes.append(e)
        nodes.sort(key=lambda n: n[1])
        for a, b in zip(nodes, nodes[1:]):
            road.add(a, b)
    # seam roads: a vertical die-top road in every gap >= 50 um between neighbouring columns of one half
    for i in range(len(cols) - 1):
        if i == nw - 1:
            continue
        gap = cols[i + 1]['x_um'] - (cols[i]['x_um'] + G.COL_W8)
        if gap < 50.0:
            continue
        sxm = round(cols[i]['x_um'] + G.COL_W8 + gap / 2, 3)
        nodes = []
        for ci in (i, i + 1):
            for key, lo, hi in bands[ci]:
                for p in rows_of[(ci, key)]:
                    e = (sxm, p[1])
                    road.add(e, p)
                    nodes.append(e)
        nodes = sorted(set(nodes), key=lambda n: n[1])
        for a_, b_ in zip(nodes, nodes[1:]):
            road.add(a_, b_)
    # every root row must reach its half's S14 entries through streets only
    for side in 'WE':
        seen, todo = set(road.entry.get(side, [])), list(road.entry.get(side, []))
        for a_, b_ in zip(sorted(road.entry.get(side, []), key=lambda n: n[1]), sorted(road.entry.get(side, []), key=lambda n: n[1])[1:]):
            road.add(a_, b_)
        while todo:
            n = todo.pop()
            for q in road.graph.get(n, ()):
                if q not in seen:
                    seen.add(q)
                    todo.append(q)
        half = {r for r, f in m['frames'].items() if f['half'] == side}
        lost = sorted(r for (r, k), n in road.rootnode.items() if r in half and n not in seen)
        if lost:
            raise ValueError(f'--cluster-mode street roadmap: {side} roots unreachable through streets: {lost}')


# ------------------------------------------------------------------------------------------------ collapse
def class_of(f):
    key = (round(f['h'], 2), len(f['elems']))
    return CLASS_NAMES.get(key, f"h{key[0]:.0f}p{key[1]}")


def collapse(G, m):
    """replace every frame region by one cluster instance; returns a report.  Must run after finalize_r8."""
    frames = m['frames']
    members = collections.defaultdict(list)
    for it in m['insts']:
        if it.region.startswith('frame_'):
            members[int(it.region[6:])].append(it)
    assert sorted(members) == sorted(frames), 'cluster mode: frame census'
    owner = {it.name: r for r, L in members.items() for it in L}
    by_ = {it.name: it for it in m['insts']}
    classes = collections.defaultdict(list)
    for r in sorted(frames):
        classes[class_of(frames[r])].append(r)
    reps = {c: rs[0] for c, rs in classes.items()}
    # boundary analysis on the flat model
    bnd = collections.defaultdict(list)       # root -> [(bus index, endpoint index)]
    internal = collections.defaultdict(list)  # root -> [bus index]
    for k, (bid, cls, bits, eps) in enumerate(m['buses']):
        rs = {owner[e[0]] for e in eps if e[0] in owner}
        if not rs:
            continue
        if len(rs) == 1 and all(e[0] in owner for e in eps):
            internal[rs.pop()].append(k)
            continue
        per = collections.defaultdict(list)
        for j, e in enumerate(eps):
            if e[0] in owner:
                per[owner[e[0]]].append(j)
        for r, J in per.items():
            cfn = f'cf{r}'
            if all(eps[j][0] == cfn for j in J):
                for j in J:                       # a column FIFO pin: one cluster port per pin
                    base = G.pslice(eps[j][1])[0]
                    d_, w_ = m['pdir'][by_[cfn].master][base]
                    bnd[r].append((k, [j], PORT_RENAME.get(base, base), d_, w_))
            else:
                # --cfifo-crsplit: the column clock (driven by the x lane's forwarded station) enters ONE port ck_col
                assert cls == 'col_clock' and eps[0][0] not in owner, ('cluster boundary not on the column FIFO', bid, cls)
                bnd[r].append((k, J, 'ck_col', 'input', 1))
    # port signature per root: {port: (dir, bits)}
    pdir = m['pdir']
    sig = {}
    for r in frames:
        ports = {}
        for k, J, port, d_, w_ in bnd[r]:
            assert port not in ports, ('two boundary nets on one cluster port', r, port)
            ports[port] = (d_, w_)
        sig[r] = ports
    for c, rs in classes.items():
        for r in rs:
            assert sig[r] == sig[reps[c]], ('cluster port signature differs inside class', c, r, reps[c])
    # cluster module text per class from the representative (the generator's own netlist writer)
    modules, mod_rec = [], {}
    for c, rep in sorted(reps.items()):
        name = f'dsfd_s81_col_{c}'
        sub = dict(m)
        sub['insts'] = list(members[rep])
        sb = [m['buses'][k] for k in internal[rep]]
        for k, J, port, d_, w_ in bnd[rep]:
            eps = m['buses'][k][3]
            sb.append((port, 'top_out' if d_ == 'output' else 'top_in', w_, [eps[j] for j in J]))
        sub['buses'] = sb
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'c.v'
            G.write_netlist(sub, 1, p, top=name)
            txt = p.read_text()
            pads = p.with_name(p.name + '.pads.json')
            pad_rec = json.loads(pads.read_text()) if pads.exists() else None
            prm = p.with_name(p.name + '.params.json')
            params_rec = json.loads(prm.read_text()).get('masters') if prm.exists() else None
        modules.append(txt)
        f = frames[rep]
        bx = cluster_box(G, f)
        mod_rec[name] = dict(cls=c, representative=rep, roots=classes[c], outline_um=[round(bx[2] - bx[0], 4), round(bx[3] - bx[1], 4)],
                             children=len(members[rep]), internal_buses=len(internal[rep]), ports=sig[rep],
                             port_bits=sum(w for _, w in sig[rep].values()), pads=pad_rec, child_params=params_rec,
                             children_by_master=dict(collections.Counter(it.master for it in members[rep])),
                             placement=[[it.name, it.master, round(it.x - bx[0], 4), round(it.y - bx[1], 4), round(it.w, 4),
                                         round(it.h, 4), it.orient] for it in members[rep]])
    # per-root deltas vs the representative (relay inventory + frame stage records the compiler reads)
    deltas = {}
    for c, rs in classes.items():
        rep = reps[c]
        inv0 = collections.Counter(it.master for it in members[rep])
        for r in rs:
            inv = collections.Counter(it.master for it in members[r])
            dm = {k: inv0.get(k, 0) - inv.get(k, 0) for k in set(inv0) | set(inv) if inv0.get(k, 0) != inv.get(k, 0)}
            st = {k: (frames[rep].get(k), frames[r].get(k)) for k in ('ret_stages', 'relay_ret', 'relay_x', 'bank_stages')
                  if frames[rep].get(k) != frames[r].get(k)}
            if dm or st:
                deltas[r] = dict(cls=c, rep=rep, master_count_delta=dm, frame_stage_rep_vs_root=st)
    # geometry check: every member inside its cluster box
    for r, L in members.items():
        bx = cluster_box(G, frames[r])
        for it in L:
            assert it.x >= bx[0] - 1e-3 and it.y >= bx[1] - 1e-3 and it.x + it.w <= bx[2] + 1e-3 and it.y + it.h <= bx[3] + 1e-3, \
                ('member outside its cluster box', r, it.name, (it.x, it.y, it.w, it.h), bx)
    # rewrite the top: remove members + their internal buses, re-point boundary endpoints
    drop = {k for ks in internal.values() for k in ks}
    portof = {(k, j): port for r in frames for k, J, port, d_, w_ in bnd[r] for j in J}
    newb = []
    for k, (bid, cls, bits, eps) in enumerate(m['buses']):
        if k in drop:
            continue
        neps = []
        for j, e in enumerate(eps):
            if e[0] in owner:
                r = owner[e[0]]
                base = G.pslice(e[1])[0]
                port = portof[(k, j)]
                ne = (f'col{r}', port + (e[1][len(base):] if port == PORT_RENAME.get(base, base) else ''))
                if ne not in neps:
                    neps.append(ne)
            else:
                neps.append(e)
        newb.append((bid, cls, bits, neps))
    m['buses'][:] = newb
    keep = [it for it in m['insts'] if it.name not in owner]
    for r in sorted(frames):
        bx = cluster_box(G, frames[r])
        c = class_of(frames[r])
        keep.append(G.Inst(f'col{r}', f'dsfd_s81_col_{c}', bx[0], bx[1], bx[2] - bx[0], bx[3] - bx[1], 'R0',
                           kind='col_cluster', region='cluster'))
    m['insts'][:] = keep
    for name, rec in mod_rec.items():
        pdir[name] = dict(rec['ports'])
    for k_ in ('_by', '_nets_of', '_nets_of_o', '_laid_all'):
        m.pop(k_, None)
    m['cluster_modules'] = '\n'.join(modules)
    rep_ = dict(schema='opentallas.s81.cluster_mode.v1', masters=mod_rec, top_instances=len(m['insts']),
                top_buses=len(m['buses']), removed_internal_buses=len(drop), member_instances=len(owner),
                deltas_vs_representative=deltas, layout=m['variant'].get('cluster_mode'))
    m['cluster_report'] = rep_
    return rep_


NSPREAD = 'physical/s81_die_pins/cfifo_crs/dsfd_cfifo_crs_nspread.tcl'


def faces(G, Mx, ports):
    """cluster LEF pins, all on the S (street) face.  --cfifo-crsplit: xd / xd2 / rd at the dsfd_cfifo_crs r5f nspread S
    pin x (cfifo x + pin x: each cluster pin straight below its cfifo pin), ck_col / rst_col just W of the cfifo span;
    otherwise sequential from the cfifo x."""
    import re as _re
    if getattr(G, 'CFIFO_CRSPLIT', False):
        txt = (G.ROOT / NSPREAD).read_text()
        pos = {}
        for mm in _re.finditer(r'-pin_name \{([^}]+)\} -layer (\S+) -location \{([-\d.]+) ([-\d.]+)\}', txt):
            if float(mm.group(4)) < 1.0:
                pos[mm.group(1)] = (mm.group(2), float(mm.group(3)))
        x0 = G.CF_X
        for p, (d_, bits) in ports.items():
            if p in ('ck_col', 'rst_col'):
                continue
            vals = []
            for i in range(bits):
                nm = f'{p}[{i}]' if f'{p}[{i}]' in pos else p
                assert nm in pos, ('cluster port has no cfifo S pin', p, i)
                layer, x = pos[nm]
                vals.append((f'{p}[{i}]', layer, (round(x0 + x - 0.012, 4), 0.0, round(x0 + x + 0.012, 4), 0.4)))
            Mx.ports[p] = ('rects', vals)
            Mx.order.append(p)
        for p, dx in (('ck_col', -6.0), ('rst_col', -12.0)):
            if p in ports:
                Mx.ports[p] = ('rects', [(f'{p}[0]', 'M5', (round(x0 + dx - 0.012, 4), 0.0, round(x0 + dx + 0.012, 4), 0.4))])
                Mx.order.append(p)
        return
    order = ['xd', 'xf', 'xd2', 'xf2', 'rf', 'rd', 'ck_col', 'rst_col']
    rest = sorted(p for p in ports if p not in order)
    seq = [(p, ports[p][1]) for p in order + rest if p in ports]
    G._lay(Mx, 'S', seq, 'M5', start=G.CF_X + 4.32)
