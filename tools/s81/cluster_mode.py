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
def cluster_layout(d, pitch, y_snap, frame_w, seam=8.64):
    """re-pitch the canonical columns (in place) and put every column's frames on the y_snap lattice; returns a receipt.
    x: west columns keep the die-W anchor and move toward the hub by k x delta, east columns mirror that.
    y: each column's stack shifts UNIFORMLY (streets keep their exact 259.2 / 388.8), by the smallest move that puts
    its first frame on the lattice -- so all frames have the same lattice phase and identical frame-relative offsets."""
    cols = sorted(d['columns'], key=lambda c: c['x_um'])
    xs = [c['x_um'] for c in cols]
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    split = max(range(len(gaps)), key=gaps.__getitem__) + 1
    old_pitch = min(gaps)
    delta = pitch - old_pitch
    assert delta >= -1e-6, ('cluster pitch below the canonical pitch', pitch, old_pitch)
    assert abs(delta / 0.432 - round(delta / 0.432)) < 1e-6, ('pitch delta off the 0.432 x lattice', delta)
    shift = {round(x, 4): (k * delta if k < split else -(len(xs) - k) * delta) for k, x in enumerate(xs)}
    dys = {}
    for c in cols:
        x_old = round(c['x_um'], 4)
        fs = sorted((f for f in d['placements'] if abs(f['origin_um'][0] - c['x_um']) < 1e-6), key=lambda f: f['origin_um'][1])
        assert fs, ('column without frames', c)
        y_first = fs[0]['origin_um'][1]
        dy = round(snap(y_first, y_snap) - y_first, 4)
        for f in fs:
            f['origin_um'] = [round(f['origin_um'][0] + shift[x_old], 4), round(f['origin_um'][1] + dy, 4)]
            assert abs(f['origin_um'][1] / y_snap - round(f['origin_um'][1] / y_snap)) < 1e-6, ('y off lattice', f['root'])
        top = fs[-1]['origin_um'][1] + fs[-1]['height_um']
        assert top <= d['die_outline_um'][1] - 10.0 and fs[0]['origin_um'][1] >= 200.0, ('column off the die', x_old, dy)
        c['x_um'] = round(c['x_um'] + shift[x_old], 4)
        c['y0_um'] = round(c['y0_um'] + dy, 4)
        c['y1_um'] = round(max(c['y1_um'], top + 4.32), 4)
        dys[x_old] = dy
    d['frames'] = {f['root']: f for f in d['placements']}
    channel = pitch - frame_w - seam
    assert channel > 30.0, ('no transit channel at this pitch', pitch, channel)
    return dict(pitch_um=pitch, old_pitch_um=round(old_pitch, 4), channel_um=round(channel, 4), seam_um=seam,
                y_snap_um=y_snap, west_columns=split,
                column_shift_um={str(x): [round(shift[x], 4), dys[x]] for x in sorted(shift)})


def cluster_box(G, f):
    """(x0, y0, x1, y1) of the column cluster of frame record f: frame width x (cfifo row bottom .. frame top)."""
    y0 = f['y'] - 4.32 - G.CF_WH[1] - 4.32
    if G.PQ_ROOTS:
        y0 -= G.PQ_ROOT_ROW
    return (f['x'], y0, f['x'] + G.COL_W8, f['y'] + f['h'])


def channel_x(G, f_or_x):
    """x range of the die-top transit channel east of a column whose frame starts at x."""
    x = f_or_x['x_um'] if isinstance(f_or_x, dict) else f_or_x
    cm = G.CLUSTER_MODE
    return (x + G.COL_W8 + 0.432, x + G.COL_W8 + cm['channel_um'] - 0.432)


def patch_corridors(G, m, cor):
    """cluster mode: rsclane{i} = the transit channel; cfstreet{r} = street band below the cluster; clusters reserved."""
    d = m['canonical_layout']
    for i, c in enumerate(d['columns']):
        x0, x1 = channel_x(G, c)
        cor[f'rsclane{i}'] = (x0, c['y0_um'] + .432, x1, c['y1_um'] - .432)
    for r, f in m['frames'].items():
        x, a, x1, b = f['street']
        bx0, by0, bx1, by1 = cluster_box(G, f)
        assert by0 - a >= 120.0, ('transit band below the cluster too thin', r, round(by0 - a, 2))
        cor[f'cfstreet{r}'] = (x + .432, a + .432, x1 - .432, by0 - .432)
        if (bx0, by0, bx1, by1, 'col_cluster') not in G.RSV_RECTS:
            G.RSV_RECTS.append((bx0, by0, bx1, by1, 'col_cluster'))
    m['cluster_boxes'] = {r: cluster_box(G, f) for r, f in m['frames'].items()}


def lane_x(G, m, col, return_lanes):
    """die-top vertical lane x of canonical column record col (its transit channel; return lanes on the E half)."""
    x0, x1 = channel_x(G, col)
    mid = (x0 + x1) / 2
    return mid + (12.0 if return_lanes else -12.0)


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
        for j, e in enumerate(eps):
            if e[0] in owner:
                r = owner[e[0]]
                assert e[0] == f'cf{r}', ('cluster boundary not on the column FIFO', bid, e)
                bnd[r].append((k, j))
    # port signature per root: {port: (dir, bits)}
    pdir = m['pdir']
    sig = {}
    for r in frames:
        ports = {}
        for k, j in bnd[r]:
            bid, cls, bits, eps = m['buses'][k]
            base = G.pslice(eps[j][1])[0]
            d_, w_ = pdir['dsfd_cfifo'][base]
            ports[PORT_RENAME.get(base, base)] = (d_, w_)
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
        for k, j in bnd[rep]:
            bid, cls, bits, eps = m['buses'][k]
            base = G.pslice(eps[j][1])[0]
            port = PORT_RENAME.get(base, base)
            d_ = pdir['dsfd_cfifo'][base][0]
            sb.append((port, 'top_out' if d_ == 'output' else 'top_in', pdir['dsfd_cfifo'][base][1], [eps[j]]))
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
    newb = []
    for k, (bid, cls, bits, eps) in enumerate(m['buses']):
        if k in drop:
            continue
        neps = []
        for e in eps:
            if e[0] in owner:
                r = owner[e[0]]
                base = G.pslice(e[1])[0]
                neps.append((f'col{r}', PORT_RENAME.get(base, base) + e[1][len(base):]))
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


def faces(G, Mx, ports):
    """cluster LEF pins: every port on the S (street) face, in cfifo order, starting above the cfifo."""
    order = ['xd', 'xf', 'xd2', 'xf2', 'rf', 'rd', 'ck_col', 'rst_col']
    rest = sorted(p for p in ports if p not in order)
    seq = [(p, ports[p][1]) for p in order + rest if p in ports]
    G._lay(Mx, 'S', seq, 'M5', start=G.CF_X + 4.32)
