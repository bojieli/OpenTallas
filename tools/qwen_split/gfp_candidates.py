#!/usr/bin/env python3
"""GLOBAL-FP-Q candidate generators for the Qwen compute die (all scored by gfp_core.score).

Levers (all keep every master, pin plan, row grid and track phase of the field):
  * remap      logical block -> physical 4x4 block slot + one of 8 in-block symmetries (ROM-image / compiler map;
               the ordered reduction AST, leaf A/B order and arithmetic are unchanged, bands keep their 16 blocks).
  * spine      field halves slide toward the centre (narrower spine; the die outline may shrink by 2*shift).
  * hub        hub groups (core VM/SU/ctlm/x-tap/seq/constants, three band port groups, up4 group, KV-link group)
               placed on legal slots inside the spine; IO band fixed on the S edge.
"""
import copy, itertools, math, random, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gfp_core as C  # noqa: E402

SPINE_X0, SPINE_X1 = 12536.184, 19856.88        # current W-field right edge (station) / E-field first tile
CH = 108.0                                       # relay/clock channel kept around every hub group (C7 CHE)
CORE = ['sp_vector_memory', 'sp_su64_sfu', 'tt_ctlm', 'xs_tap', 'seq_su'] + [f'cbuf_g_{i}' for i in range(8)] + \
       [f'crom_g_{i}' for i in range(8)]
CLK = ['clk_rx', 'rstseq_rom']
UP4 = [f'tt_up4_leaf{i}' for i in range(4)] + ['up4_sel_station', 'up4_sel_branch0', 'up4_sel_branch1']
TOP = ['ucie_kv', 'd2d_rom', 'ckb_rom', 'rs_bump', 'x3_mux']
BAND = {b: [f'sp_port_tiles_{b}', f'sp_port_tiles_{b}_f1', f'sp_res_ser_{b}', f'sp_band_lanes_{b}'] for b in range(3)}


# ------------------------------------------------------------------ geometry helpers
def bbox(model, names):
    xs = [model[n]['x'] for n in names]; ys = [model[n]['y'] for n in names]
    xe = [model[n]['x'] + model[n]['w'] for n in names]; ye = [model[n]['y'] + model[n]['h'] for n in names]
    return min(xs), min(ys), max(xe), max(ye)


def translate(model, names, dx, dy):
    for n in names:
        model[n]['x'] = round(model[n]['x'] + dx, 3); model[n]['y'] = round(model[n]['y'] + dy, 3)


def flip_group_x(model, names):
    """Mirror a group about its own horizontal centre line (MX image of the whole group)."""
    x0, y0, x1, y1 = bbox(model, names)
    for n in names:
        i = model[n]; i['y'] = round(y0 + y1 - i['y'] - i['h'], 3)
        i['o'] = {'R0': 'MX', 'MX': 'R0', 'MY': 'R180', 'R180': 'MY'}[i['o']]


def overlaps(model, names=None, pad=0.0):
    keys = list(model)
    arr = np.array([[model[k]['x'], model[k]['y'], model[k]['x'] + model[k]['w'], model[k]['y'] + model[k]['h']] for k in keys])
    idx = range(len(keys)) if names is None else [keys.index(n) for n in names]
    bad = []
    for a in idx:
        r = arr[a]
        hit = (arr[:, 0] < r[2] + pad - 1e-3) & (arr[:, 2] > r[0] - pad + 1e-3) & (arr[:, 1] < r[3] + pad - 1e-3) & (arr[:, 3] > r[1] - pad + 1e-3)
        hit[a] = False
        for b in np.nonzero(hit)[0]:
            if names is None and b < a: continue
            bad.append((keys[a], keys[b]))
    return bad


def outside(model, die):
    return [n for n, i in model.items() if i['x'] < -1e-3 or i['y'] < -1e-3 or i['x'] + i['w'] > die['w'] + 1e-3 or i['y'] + i['h'] > die['h'] + 1e-3]


# ------------------------------------------------------------------ spine / hub
def field_shift(base, ws):
    """Slide both tile-field halves toward the centre so the spine is ws wide. Returns model, spine x0, x1, shift."""
    m = copy.deepcopy(base)
    s = round(((SPINE_X1 - SPINE_X0) - ws) / 2, 3)
    for i in m.values():
        if i['m'] in C.FIELD_MASTERS:
            if i['x'] < SPINE_X0: i['x'] = round(i['x'] + s, 3)
            elif i['x'] >= SPINE_X1 - 1: i['x'] = round(i['x'] - s, 3)
    return m, SPINE_X0 + s, SPINE_X1 - s, s


def hub_layout(base, ws, plan):
    """plan: dict with
         core_y      VM y (core cluster keeps its internal arrangement; VM centred in the spine)
         band        {b: (side 'L'|'R'|'C', y_bottom, orient 'R0'|'MX')}  port pair + res_ser + lanes as one rigid group
         up4         (x_rel, y) of the up4 leaf stack
         clk         (x_rel, y) of clk_rx (+ rstseq beside it)
    """
    m, x0, x1, s = field_shift(base, ws)
    cx = (x0 + x1) / 2
    vm = m['sp_vector_memory']
    translate(m, CORE, cx - vm['w'] / 2 + plan.get('core_dx', 0.0) - vm['x'], plan['core_y'] - vm['y'])
    # band groups: rigid, optional MX of the whole group
    for b, (side, yb, orient) in plan['band'].items():
        names = BAND[b]
        cur = 'MX' if m[f'sp_port_tiles_{b}']['o'] == 'MX' else 'R0'
        if orient != cur: flip_group_x(m, names)
        gx0, gy0, gx1, gy1 = bbox(m, names)
        if side == 'L': tx = x0 + CH
        elif side == 'R': tx = x1 - CH - (gx1 - gx0)
        else: tx = cx - (gx1 - gx0) / 2
        translate(m, names, tx - gx0, yb - gy0)
    ux, uy = plan['up4']
    gx0, gy0, _, _ = bbox(m, UP4); translate(m, UP4, x0 + ux - gx0, uy - gy0)
    kx, ky = plan['clk']
    translate(m, CLK, x0 + kx - m['clk_rx']['x'], ky - m['clk_rx']['y'])
    # KV link group stays on the N edge, centred on the same offset from the spine centre as today
    off = m['ucie_kv']['x'] - (SPINE_X0 + SPINE_X1) / 2
    translate(m, TOP, cx + off - m['ucie_kv']['x'], 0)
    return m, dict(spine_um=round(ws, 3), field_shift_um=s, spine_x=[round(x0, 3), round(x1, 3)], die_shrink_mm2=round(2 * s * 25937.28 / 1e6, 2))


def group_dims(base):
    out = {}
    for b in range(3):
        x0, y0, x1, y1 = bbox(base, BAND[b]); out[b] = (x1 - x0, y1 - y0)
    return out


# ------------------------------------------------------------------ logical block remap
class Blocks:
    """48 logical blocks (16 tiles each, 4x4 in the current map) and their bus records."""

    def __init__(self, die):
        self.die = die
        self.tree = {k: [] for k in range(48)}
        for r in die.recs:
            if r['c'] == 'tree_block':
                self.tree[int(r['b'].split('_')[1])].append(r)
        self.bword = {int(r['b'].split('_')[1]): r for r in die.recs if r['b'].startswith('bword_') and r['b'].split('_')[1].isdigit()}
        self.tiles = {}
        for k, recs in self.tree.items():
            ts = sorted({n for r in recs for n, _ in r['ends']}, key=lambda t: (int(t.split('_')[1]), int(t.split('_')[2])))
            self.tiles[k] = ts
        # slot = (col group, row group) of the block's tiles in the current map
        self.slot = {}
        for k, ts in self.tiles.items():
            cs = sorted({int(t.split('_')[1]) for t in ts}); rs = sorted({int(t.split('_')[2]) for t in ts})
            self.slot[k] = (cs[0] // 4, rs[0] // 4)
        self.slot_of = {v: k for k, v in self.slot.items()}
        self.band = {k: self.bword[k]['ends'][1][0] for k in range(48)}   # destination port instance

    def mapping(self, k, slot, sym):
        """logical tile name -> physical tile name for logical block k placed at slot with symmetry sym (0..7)."""
        cg0, rg0 = self.slot[k]; cg, rg = slot
        out = {}
        for t in self.tiles[k]:
            c, r = int(t.split('_')[1]) - 4 * cg0, int(t.split('_')[2]) - 4 * rg0
            if sym & 4: c, r = r, c
            if sym & 1: c = 3 - c
            if sym & 2: r = 3 - r
            out[t] = f't_{4 * cg + c}_{4 * rg + r}'
        return out


def block_cost(die, model, B, k, slot, sym, downstream):
    """(max leaf->VM stages through this block, block bit-um) for logical block k at slot/sym."""
    P = B.mapping(k, slot, sym)
    out = {}; bitum = 0.0
    recs = sorted(B.tree[k], key=lambda r: int(r['b'].split('_')[2]))
    for r in recs:
        hp, L, _, ends = C.bus_geom(r, model, P)[:4]
        bitum += hp
        src, dst = ends[0][0], ends[-1][0]
        srcp = r['port'][0]
        t0 = out.get(src, 0) if srcp == 'n_y' else 0
        out[dst] = max(out.get(dst, 0), t0 + C.stages(L))
    bw = B.bword[k]
    hp, L, _, ends = C.bus_geom(bw, model, P)[:4]
    bitum += hp
    root = ends[0][0]
    return out[root] + C.stages(L) + downstream[bw['ends'][1][0]], bitum


def downstream_stages(die, model):
    """stages from each port instance to the VM (pfrag/slab_rq for f1, rq, rs)."""
    st = {}
    for r in die.recs:
        if r['b'].startswith(('pfrag_', 'slab_rq_', 'rq_', 'rs_')):
            st[r['b']] = C.stages(C.bus_geom(r, model)[1])
    d = {}
    for b in range(3):
        base_ = st[f'rq_{b}'] + st[f'rs_{b}']
        d[f'sp_port_tiles_{b}'] = base_
        d[f'sp_port_tiles_{b}_f1'] = max(st[f'pfrag_{b}_port_tiles_{b}_f1'], st[f'slab_rq_{b}']) + base_
    return d


def remap(die, model, B, power=4.0, syms=range(8)):
    """Assignment of logical blocks to physical slots (+ symmetry) minimising sum(path^power) (min-max proxy),
    ties by bit-um. Returns P (logical tile -> physical tile), per-block table."""
    from scipy.optimize import linear_sum_assignment
    ds = downstream_stages(die, model)
    slots = sorted(B.slot_of)
    cost = np.zeros((48, 48)); best = {}
    for k in range(48):
        for j, sl in enumerate(slots):
            bc = None
            for s in syms:
                path, bu = block_cost(die, model, B, k, sl, s, ds)
                key = (path, bu)
                if bc is None or key < bc[0]: bc = (key, s)
            best[(k, j)] = bc
            cost[k, j] = (bc[0][0] ** power) + bc[0][1] / 1e7
    rows, cols = linear_sum_assignment(cost)
    P = {}; table = []
    for k, j in zip(rows, cols):
        (path, bu), s = best[(k, j)]
        P.update(B.mapping(k, slots[j], s))
        table.append(dict(block=int(k), slot=list(slots[j]), sym=int(s), band_port=B.band[k], path_stages=int(path), bit_um=round(bu)))
    return P, table


# ------------------------------------------------------------------ named hub plans
def plan_cluster(base, ws):
    """Architect hub (H-tree root at the centroid): VM/SU seam on the head row, band1 directly under the VM
    (res_ser on top), band0 under band1, band2 directly over the SU (res_ser at the bottom), up4 stack W of the
    SU beside ctlm, clock receiver E under the VM; KV-link group on the N edge, IO band fixed."""
    gd = group_dims(base)
    vm = base['sp_vector_memory']
    vy = vm['y']                                  # 11962.08: VM top at the head-row seam (C12)
    b1y = vy - CH - gd[1][1]
    b0y = b1y - CH - gd[0][1]
    su_top = base['sp_su64_sfu']['y'] + base['sp_su64_sfu']['h']
    b2y = su_top + CH
    return dict(core_y=vy, band={1: ('L', b1y, 'R0'), 0: ('L', b0y, 'R0'), 2: ('L', b2y, 'MX')},
                up4=(CH + 20, base['tt_ctlm']['y'] + base['tt_ctlm']['h'] + 60), clk=(ws - CH - 520, vy - CH - 420))


def plan_bandside(base, ws):
    """Wide-enough spine for the band groups to sit BESIDE the VM/SU stack (E side of the spine)."""
    gd = group_dims(base)
    vm = base['sp_vector_memory']; vy = vm['y']
    return dict(core_y=vy, band={1: ('R', vy - 200 - gd[1][1] / 2 + 1200, 'R0'), 0: ('R', vy - 200 - gd[1][1] * 1.5 - 1300, 'R0'),
                                 2: ('R', vy + 2203.2 + 200, 'MX')},
                up4=(CH + 20, base['tt_ctlm']['y'] + base['tt_ctlm']['h'] + 60), clk=(CH, vy - CH - 420))


# ------------------------------------------------------------------ split head chain (structural, priced)
def split_head(die, model):
    """Feed each 24-column half at its middle: the root word forks to h_11 (xcol_w, chain west to h_0) and h_12
    (re-mastered xcol_e, chain east to h_23); mirror on the E half (h_36 xcol_e east to h_47, h_35 xcol_w west to
    h_24).  Same broadcast data, same xcol masters (_w/_e already exist), fork = plain fanout of the relayed root word.
    Returns (die view with rewired head buses, model with re-mastered inner-quarter head columns, cost note)."""
    import copy as _c
    m = _c.deepcopy(model)
    for c in range(12, 24): m[f'h_{c}']['m'] = 'qfd_xcol_e'
    for c in range(24, 36): m[f'h_{c}']['m'] = 'qfd_xcol_w'
    pins = die.g.pins
    view = _c.copy(die)
    recs = []
    for r in die.recs:
        if r['c'] == 'head_chain':
            continue                                   # 1567-b chain rewired below; 1-b xfault re-joined at the fork (not modelled)
        if any(m[n]['m'] != model[n]['m'] for n, _ in r['ends']):
            r = dict(r, ends=[(n, pins[m[n]['m']][p]) for (n, _), p in zip(r['ends'], r['port'])])
        recs.append(r)
    act = next(r for r in die.recs if r['b'] == 'head_0')
    def mk(name, ends):
        return dict(b=name, c='head_chain', n=1567, ends=[(n, pins[m[n]['m']][p]) for n, p in ends], port=[p for _, p in ends],
                    act=act['act'], crit=act['crit'], why=act['why'])
    recs.append(mk('head_root_w', [('xs_tap', 'hw_d'), ('h_11', 'e_d'), ('h_12', 'w_d')]))
    recs.append(mk('head_root_e', [('xs_tap', 'he_d'), ('h_35', 'e_d'), ('h_36', 'w_d')]))
    for c in range(11, 0, -1): recs.append(mk(f'head_w_{c}', [(f'h_{c}', 'w_d'), (f'h_{c-1}', 'e_d')]))
    for c in range(12, 23): recs.append(mk(f'head_wi_{c}', [(f'h_{c}', 'e_d'), (f'h_{c+1}', 'w_d')]))
    for c in range(35, 24, -1): recs.append(mk(f'head_ei_{c}', [(f'h_{c}', 'w_d'), (f'h_{c-1}', 'e_d')]))
    for c in range(36, 47): recs.append(mk(f'head_e_{c}', [(f'h_{c}', 'e_d'), (f'h_{c+1}', 'w_d')]))
    view.recs = recs
    view.byname = {r['b']: r for r in recs}
    return view, m, dict(note='h_12..h_23 -> qfd_xcol_e, h_24..h_35 -> qfd_xcol_w (existing masters); root word forks; '
                              'xfault chain must be re-joined at the fork (1-b OR, not modelled); xcol tids straps unchanged')


# ------------------------------------------------------------------ architect topology: three spines (one per band)
def _col(n):
    return int(n.split('_')[1])


def stack_band(m, b, x0, y0):
    """Re-arrange band b's group as a 1-port-wide column: res_ser, port_tiles, port_tiles_f1, band_lanes bottom-up
    (each centred on the column), channel CH between members. Returns column top y."""
    names = [f'sp_res_ser_{b}', f'sp_port_tiles_{b}', f'sp_port_tiles_{b}_f1', f'sp_band_lanes_{b}']
    wmax = max(m[n]['w'] for n in names)
    y = y0
    for n in names:
        i = m[n]; i['x'] = round(x0 + (wmax - i['w']) / 2, 3); i['y'] = round(y, 3); y += i['h'] + CH
    return y - CH, wmax


def tri_spine(die, base, ws=4924.8, band_y=None, stacked=True, cuts=(8, 40)):
    """Architect topology T3: every band's 16 blocks (4 block columns) surround ITS OWN port spine, instead of all
    48 block results crossing to one central spine.  W field opens a gap at tile column cuts[0] (band0 = block
    columns 0..3), E field at cuts[1] (band2 = block columns 8..11); band1 stays in the (narrowed) centre spine under
    the VM.  The die width changes by 2*gap - (7320.7 - ws).  Returns (die view with the new outline, model, info)."""
    import copy as _c
    gd = group_dims(base)
    if stacked:
        gw = max(base[n]['w'] for n in BAND[0]) + 2 * CH
    else:
        gw = gd[0][0] + 2 * CH
    m = _c.deepcopy(base)
    w0 = SPINE_X1 - SPINE_X0
    # W columns: c < cuts[0] stay, cuts[0] <= c < 24 shift +gw; centre spine ws; E columns shift by delta_E
    dE = gw - (w0 - ws)                       # E field shift before its own gap
    for n, i in m.items():
        if i['m'] not in C.FIELD_MASTERS: continue
        c = _col(n)
        if c < 24:
            if c >= cuts[0]: i['x'] = round(i['x'] + gw, 3)
        else:
            i['x'] = round(i['x'] + dE + (gw if c >= cuts[1] else 0), 3)
    x0 = SPINE_X0 + gw; x1 = x0 + ws; cx = (x0 + x1) / 2
    view = _c.copy(die)
    view.die = dict(die.die); view.die['w'] = round(die.die['w'] + 2 * gw - (w0 - ws), 3)
    view.die['mm2'] = round(view.die['w'] * view.die['h'] / 1e6, 3)
    # hub: same internal arrangement as arch_htree, centred in the new centre spine; band1 under the VM
    vm = m['sp_vector_memory']
    translate(m, CORE, cx - vm['w'] / 2 - vm['x'], 0)
    vy = vm['y']
    b1y = vy - CH - gd[1][1]
    gx0, gy0, gx1, gy1 = bbox(m, BAND[1]); translate(m, BAND[1], x0 + CH - gx0, b1y - gy0)
    ux0, uy0, _, _ = bbox(m, UP4); translate(m, UP4, x0 + CH + 20 - ux0, m['tt_ctlm']['y'] + m['tt_ctlm']['h'] + 60 - uy0)
    translate(m, CLK, x1 - CH - 520 - m['clk_rx']['x'], vy - CH - 420 - m['clk_rx']['y'])
    off = base['ucie_kv']['x'] - (SPINE_X0 + SPINE_X1) / 2
    translate(m, TOP, cx + off - m['ucie_kv']['x'], 0)
    # side spines: the gap opens where tile column cuts[k] stood before it moved right by gw
    xg0 = base[f't_{cuts[0]}_0']['x'] - 8.208
    xg2 = m[f't_{cuts[1]}_0']['x'] - gw - 8.208
    yb = band_y if band_y is not None else 4423.68
    for b, xg in ((0, xg0), (2, xg2)):
        if stacked:
            stack_band(m, b, xg + CH, yb)
        else:
            gx0, gy0, _, _ = bbox(m, BAND[b]); translate(m, BAND[b], xg + CH - gx0, yb - gy0)
    info = dict(spine_um=ws, side_spine_um=round(gw, 3), die_w_um=view.die['w'], die_mm2=view.die['mm2'],
                die_delta_mm2=round(view.die['mm2'] - die.die['mm2'], 2), band_y=yb, stacked=stacked, cuts=list(cuts),
                spine_x=[round(x0, 3), round(x1, 3)])
    return view, m, info
