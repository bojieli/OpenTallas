"""Repair measured pin-to-pin overreach using die-placed registered channel relays.

Freeze the die tool's current master pin assignment before adding relays, so a
shared master's face cannot move in response to the new neighbouring relay.
Never route through a leaf; failed placement remains an explicit plan defect.
"""
import json
import math
import os
import re
from pathlib import Path

# KVR-DERIVE 10-19 (QW-KVATTN2 finding 5): a relay this pass (or kv_bundle_eq / kv_k_rt_eq) adds is clocked by the clock of
# the LAUNCHING pin's register, never by "the first clock trunk touching the source instance" (that put the K / V
# response relays krs / pvrs, slg o_pc and kvpc o_next on n_clk_hbm: unsynchronised core -> HBM -> core resampling).
# Launch domain per tile port = the elaborated-RTL measurement (kvs_port_domains.py, results/arch/qwen_kv_kits_b_1018/
# <kind>_ports.json); a die master without a record launches on the core clock (every non-tile KV die master is a core
# element; the main relay planner clocks every chain on clk_core_*).  ck -> the source's (else the sink's) clk_core_*
# trunk; hck (the kc command / fault chain kck_* / kcf_*: measured hck at both ends) -> its clk_hbm_* trunk; a bundle that
# carries both (slg o_pc / o_ctl, kvpc o_grp) has no single legal relay clock: core (as the main planner) + recorded
# MIXED (the bundle must be split by domain; open item, lanes/KVR-DERIVE.md).
PORT_DOMAINS = 'results/arch/qwen_kv_kits_b_1018'
# KV-DOMSPLIT 10-19 (OT_KV_DOMSPLIT=1): the split tiles' measured records (every group <-> PC / gather word single-domain)
if os.environ.get('OT_KV_DOMSPLIT', '0') == '1':
    PORT_DOMAINS = 'results/arch/qwen_kv_domsplit_1019/ports'
_PD = {}


def _port_record(master):
    kind = re.sub(r'^qkd_kvs_', '', master or '')
    if kind not in _PD:
        f = Path(__file__).resolve().parents[2] / PORT_DOMAINS / f'{kind}_ports.json'
        _PD[kind] = json.loads(f.read_text())['ports'] if master and master.startswith('qkd_kvs_') and f.exists() else None
    return _PD[kind]


def port_domain(master, port):
    """'core' | 'hbm' | 'mixed' | None (unknown / feed-through) for one die pin of a master"""
    rec = _port_record(master)
    if rec is None:
        return None
    v = rec.get(port.lstrip('*'))
    if not v:
        return None
    ds = {d for d in v.get('domains', []) if d not in ('none', '?const')}
    if not ds:
        return None
    if ds == {'ck'}:
        return 'core'
    if ds == {'hck'}:
        return 'hbm'
    return 'mixed'


def launch_domain(by, src, dst):
    """the launching pin's domain of a chain src -> dst (src record, else the sink's, else core)"""
    d = port_domain(getattr(by.get(src[0]), 'master', None), src[1])
    if d is None and dst is not None:
        d = port_domain(getattr(by.get(dst[0]), 'master', None), dst[1])
    return d or 'core'


def relay_trunk(buses, by, src, dst):
    """-> (bus index of the clock trunk for a relay on chain src -> dst, launch domain).  Never an HBM trunk for a core
    word, never a core trunk for an HBM word; mixed bundles take the core trunk (recorded by the callers)."""
    dom = launch_domain(by, src, dst)
    pre = 'clk_hbm_' if dom == 'hbm' else 'clk_core_'
    # K.RST 10-21: membership = the trunk's LOADS (b[3][1:]), never its driver.  The PLL drives every clk_core_* trunk,
    # so 'any endpoint' put the PLL lock pin relay (rly_pinfix_pll_lock_0__s0, at the PLL in region c) on the first core
    # trunk in bus order (clk_core_WS): kv_fwd_lanes then laned a c -> c hop as WS -> c and gated the PLL lock with a
    # die-reset en 28,959.8 um away (boot deadlock: the HOST releases die_rst_n only after pll_locked) and the opt-in
    # reset transport priced that wire at +89 release edges (HOLD 414 > h273b).  kv_die's main planner already skips eps[0].
    for inst in (src[0], dst[0] if dst else None):
        j = next((j for j, b in enumerate(buses) if b is not None and b[1] == 'clock_trunk' and b[0].startswith(pre)
                  and any(i == inst for i, _ in b[3][1:])), None)
        if j is not None:
            return j, dom
    if dom == 'hbm':
        raise ValueError(f'kv_pin_repair: HBM-domain chain {src} -> {dst} has no clk_hbm_* trunk at either end')
    return next(j for j, b in enumerate(buses) if b is not None and b[0] == 'clk_core_c'), dom


def trunk_domain(bid):
    return 'hbm' if bid.startswith('clk_hbm') else 'core' if bid.startswith('clk_core') else None


def _cands(K, target, grid, r):
    return [(K.up(target[0]+x*grid, K.GX), K.up(target[1]+y*grid, K.GY)) for x in range(-r, r+1) for y in range(-r, r+1)]


def _far(K, end, p, q):
    """KV-BIND11 (OT_KV_D2D_PINS): hop p -> end measured to the end's FARTHEST realized pin (d2d words), else p -> q."""
    f_ = getattr(K, 'ep_far', None)
    d_ = f_(end[0], end[1], p) if (f_ and end) else None
    return d_ if d_ is not None else abs(p[0]-q[0])+abs(p[1]-q[1])


class CollisionIndex:
    """Conservative rectangle lookup; preserve original obstacle order and comparisons."""
    def __init__(self, insts, cell=256.0):
        self.cell, self.items, self.bins = cell, [], {}
        for it in insts:
            self.add(it)

    def cells(self, x0, y0, x1, y1):
        for x in range(math.floor(x0/self.cell), math.floor(x1/self.cell)+1):
            for y in range(math.floor(y0/self.cell), math.floor(y1/self.cell)+1):
                yield x, y

    def add(self, it):
        index = len(self.items)
        self.items.append(it)
        for cell in self.cells(it.x, it.y, it.x+it.w, it.y+it.h):
            self.bins.setdefault(cell, []).append(index)

    def candidates(self, x0, y0, x1, y1):
        indices = set()
        for cell in self.cells(x0, y0, x1, y1):
            indices.update(self.bins.get(cell, ()))
        gone = getattr(self, 'gone', None)
        return [self.items[index] for index in sorted(indices) if not gone or self.items[index].name not in gone]


# KDIE4-PH 10-22 (OT_KV_PINFIX_ROUTE=1, default off = unchanged).
# Root cause of the residual hops: the relay planner's first pass places stations against the FRAME (no drawn pins yet;
# relm / ovm / ovf: 568-572 pin hops over reach after pass 1), the auto-pin pass then draws the word along the face (krs on
# a 1,188-um group face, pvw pr 873 um along its strip face), and the pin-hinted re-plan that would fix it is a greedy
# net-ordered pass that corners some other chain on every case (relm / ovm: slg_WS_0.o_pc0 stage 1 with the full hints,
# kvs_ctl.o_hroot_WS / px_tok__f23 with the narrow hints; ovf: kvs_ctl.o_hroot_WS) and is discarded.  The greedy repair
# then decides: its stage choice (a +-16 / 40 half-cell box around a point 350 um toward the far end, strict progress per
# stage) dead-ends in crowded channels although a legal relay chain exists (ks_pvp1 in the hub | strip channel filled by
# the emb px fork stations, krs_ES_7, kvpc o_grp), and where it succeeds it can spend an extra station (ovf krs_WS_6: 4
# for a 1,197-um hop -> K.rt_WS_6 81 > 80).  With the knob every over-reach hop is seated by an exhaustive search instead:
# breadth-first over every legal relay origin (10.8-um lattice, then 5.4 with a wider window; block halo 21.6 / relay gap
# 4.32 as the planner, then the repair's 4.32 everywhere), hops bounded by the repair's own cap measured conservatively
# centre-to-centre + frame width, so the FEWEST stations are found whenever any exist; every hop of the result is then
# re-measured exactly pin to pin (d2d / view ends: farthest pin).  The greedy stages remain the fallback; a hop still
# left over reach re-seats a window of its chain's own adjacent stations (never a fork tap, a tree hop, or a station
# another net uses).  Pins stay fixed (assigned_ports), no reach is raised, nothing is squeezed: only registered relay
# stations are added or moved; relay_stages / fork_stages carry the new counts, ages derive downstream as before.
PINFIX_ROUTE = os.environ.get('OT_KV_PINFIX_ROUTE', '0') == '1'
ROUTE_FIRST = os.environ.get('OT_KV_PINFIX_ROUTE_FIRST', '1') == '1'   # 0: greedy first, the search only where it fails
ROUTE_STEP = float(os.environ.get('OT_KV_PINFIX_ROUTE_STEP', '5.4'))
ROUTE_MAX_SPAN = int(os.environ.get('OT_KV_PINFIX_ROUTE_SPAN', '6'))
_HOPSFX = re.compile(r'__(r\d+|pinfix\d+|beq\d+)$')


def _frame(K, bid, bits):
    """the repair's relay frame (width, height incl. SHAVE) for a word of bits"""
    width, height = 52.68, 30.24 if bits <= 512 else K.up(bits * .048 + 4, K.GY)
    if os.environ.get('OT_KV_RLY_STD', '0') == '1':
        import kv_rly_std as RS
        width, height, _ = RS.layout(bits, RS.frame_rev(bid))
        width, height = width + K.SHAVE, max(height + K.SHAVE, bits * .048 + 4 if bits > 512 else 0.0)
        height = K.up(height, K.GY) if height > RS.STD[528][1] + K.SHAVE else height
    return width, height


def _io(K, x, y, width, height, orient):
    """(in pin a, out pin b) of a relay frame at (x, y) as _choice draws it"""
    inp_x, out_x = (x + width - K.SHAVE, x) if orient == 'MY' else (x, x + width - K.SHAVE)
    return (inp_x, y + height / 2), (out_x, y + height / 2)


def _bfs_run(K, m, oidx, removed, src, src_end, dst, dst_end, width, height, cap, bgap, s=None, mg=None):
    """fewest relay stations (origins, src -> dst order) for one run, or None.  Every hop <= cap (exact re-check after)."""
    import numpy as np
    s = s or ROUTE_STEP
    Wd, Hd = m['die']['w'], m['die']['h']
    mg = mg or max(2 * cap, 600.0)
    x0 = max(0.0, min(src[0], dst[0]) - mg)
    x1 = min(Wd, max(src[0], dst[0]) + mg)
    y0 = max(0.0, min(src[1], dst[1]) - mg)
    y1 = min(Hd, max(src[1], dst[1]) + mg)
    i0, j0 = int(x0 // s), int(y0 // s)
    xs = np.array([K.up(k * s, K.GX) for k in range(i0, int(x1 // s) + 1)])
    ys = np.array([K.up(k * s, K.GY) for k in range(j0, int(y1 // s) + 1)])
    nx, ny = len(xs), len(ys)
    if not nx or not ny:
        return None
    free = np.ones((nx, ny), bool)
    free[(xs < 4.32) | (xs + width + 4.32 > Wd), :] = False
    free[:, (ys < 4.32) | (ys + height + 4.32 > Hd)] = False
    obs = [(o.x, o.y, o.w, o.h, o.name.startswith('rly_') or str(getattr(o, 'master', '')).startswith('qkd_rly'))
           for o in oidx.candidates(x0 - width - bgap, y0 - height - bgap, x1 + bgap, y1 + bgap) if o.name not in removed]
    obs += [(kx, ky, kw, kh, False) for _n, kx, ky, kw, kh in m.get('keepouts', [])]
    for ox, oy, ow, oh, rl in obs:
        g = 4.32 if rl else bgap
        # overlap  <=>  x - g < ox + ow  and  x + w + g > ox  (as _choice, with the block halo g)
        ia = np.searchsorted(xs, ox - width - g + .001, 'left')
        ib = np.searchsorted(xs, ox + ow + g - .001, 'left')
        ja = np.searchsorted(ys, oy - height - g + .001, 'left')
        jb = np.searchsorted(ys, oy + oh + g - .001, 'left')
        if ia < ib and ja < jb:
            free[ia:ib, ja:jb] = False
    idx = np.argwhere(free)
    if not len(idx):
        return None
    cx, cy = xs[idx[:, 0]] + width / 2, ys[idx[:, 1]] + height / 2
    start = np.zeros_like(free)
    goal = np.zeros_like(free)
    near_s = np.abs(cx - src[0]) + np.abs(cy - src[1]) <= cap + width
    near_g = np.abs(cx - dst[0]) + np.abs(cy - dst[1]) <= cap + width
    for q in np.nonzero(near_s | near_g)[0]:
        (i, j), ns_, ng_ = idx[q], near_s[q], near_g[q]
        for o in ('R0', 'MY'):
            a_, b_ = _io(K, xs[i], ys[j], width, height, o)
            if ns_ and max(abs(a_[0] - src[0]) + abs(a_[1] - src[1]), _far(K, src_end, a_, src)) <= cap:
                start[i, j] = True
            if ng_ and max(abs(b_[0] - dst[0]) + abs(b_[1] - dst[1]), _far(K, dst_end, b_, dst)) <= cap:
                goal[i, j] = True
    R = int((cap - width) // s)
    if R < 1 or not start.any() or not goal.any():
        return None

    def dil(mk):
        d = mk.copy()
        for _ in range(R):
            e = d.copy()
            e[1:] |= d[:-1]
            e[:-1] |= d[1:]
            e[:, 1:] |= d[:, :-1]
            e[:, :-1] |= d[:, 1:]
            d = e
        return d
    layer, seen, layers = start, start.copy(), [start]
    while not (layer & goal).any():
        nxt = dil(layer) & free & ~seen
        if not nxt.any() or len(layers) > 200:
            return None
        seen |= nxt
        layer = nxt
        layers.append(layer)

    def key(t, c):
        return (abs(int(t[0]) - c[0]) + abs(int(t[1]) - c[1]) + (abs(xs[t[0]] - src[0]) + abs(ys[t[1]] - src[1])) / s,
                int(t[0]), int(t[1]))
    g_ = [tuple(t) for t in np.argwhere(layer & goal)]
    path = [min(g_, key=lambda t: (abs(xs[t[0]] - dst[0]) + abs(ys[t[1]] - dst[1]), t))]
    for L in range(len(layers) - 2, -1, -1):
        c = path[-1]
        cand = [tuple(t) for t in np.argwhere(layers[L]) if abs(int(t[0]) - c[0]) + abs(int(t[1]) - c[1]) <= R]
        path.append(min(cand, key=lambda t: key(t, c)))
    path.reverse()
    return [(float(xs[i]), float(ys[j])) for i, j in path]


def _orient_check(K, spots, src, src_end, dst, dst_end, width, height, cap):
    """orient every station (start / goal: an orientation meeting its end hop; else toward the run) and re-measure every
    hop exactly; -> [(x, y, orient)] or None"""
    n = len(spots)
    orients = []
    for k, (x, y) in enumerate(spots):
        prev_c = src if k == 0 else (spots[k - 1][0] + width / 2, spots[k - 1][1] + height / 2)
        next_c = dst if k == n - 1 else (spots[k + 1][0] + width / 2, spots[k + 1][1] + height / 2)
        pref = 'MY' if next_c[0] < prev_c[0] else 'R0'
        opts = [pref, 'R0' if pref == 'MY' else 'MY']
        ok = None
        for o in opts:
            a_, b_ = _io(K, x, y, width, height, o)
            if k == 0 and max(abs(a_[0] - src[0]) + abs(a_[1] - src[1]), _far(K, src_end, a_, src)) > cap:
                continue
            if k == n - 1 and max(abs(b_[0] - dst[0]) + abs(b_[1] - dst[1]), _far(K, dst_end, b_, dst)) > cap:
                continue
            ok = o
            break
        if ok is None:
            return None
        orients.append(ok)
    prev = src
    for k, (x, y) in enumerate(spots):
        a_, b_ = _io(K, x, y, width, height, orients[k])
        d_ = abs(a_[0] - prev[0]) + abs(a_[1] - prev[1])
        if k == 0:
            d_ = max(d_, _far(K, src_end, a_, src))
        if d_ > cap:
            return None
        prev = b_
    if max(abs(prev[0] - dst[0]) + abs(prev[1] - dst[1]), _far(K, dst_end, prev, dst)) > cap:
        return None
    return [(x, y, o) for (x, y), o in zip(spots, orients)]


def _route_insert(K, m, oidx, bid, cls, bits, a_end, ap, b_end, bp, width, height, cap0):
    """OT_KV_PINFIX_ROUTE in the repair loop: the fewest registered stations between the two fixed pins of one hop
    (named / chained exactly as the greedy stages), or None -> (staged, chain, previous, last out pin)"""
    for cap in (cap0,):          # the greedy pass's own cap (no new reach rule); fewest stations at it
        for bgap in (21.6, 4.32):
            for s_, mg_ in ((2 * ROUTE_STEP, cap), (ROUTE_STEP, max(2 * cap, 600.0))):
                sp_ = _bfs_run(K, m, oidx, set(), ap, a_end, bp, b_end, width, height, cap, bgap, s_, mg_)
                st_ = sp_ and _orient_check(K, sp_, ap, a_end, bp, b_end, width, height, cap)
                if not st_:
                    continue
                staged, chain, previous = [], [], a_end
                for k, (x, y, o) in enumerate(st_):
                    name = 'rly_pinfix_' + bid.replace('__', '_') + '_' + str(k)
                    staged.append(K.F.Inst(name, f'qkd_rly_{bits}', x, y, width - K.SHAVE, height - K.SHAVE, o,
                                           kind='relay', region='relay'))
                    chain.append((bid if not k else bid + '__pinfix' + str(k), cls, bits, [previous, (name, 'a')]))
                    previous = (name, 'b')
                x, y, o = st_[-1]
                m.setdefault('pin_route_insert', []).append(dict(bus=bid, stations=len(st_), cap=cap, block_gap=bgap,
                                                                  step=s_))
                return staged, chain, previous, _io(K, x, y, width, height, o)[1]
    return None


def _reseat_unresolved(K, m, buses, by, oidx, unresolved, additions):
    """OT_KV_PINFIX_ROUTE: BFS re-seat of every hop the greedy repair left over reach (see PINFIX_ROUTE)"""
    import sys
    M = K.masters(m, 1)
    oidx.gone = set()
    cap0 = K.HOP_REACH if getattr(K, 'HOP', False) else K.PIN_REACH
    refs = {}
    for bid, cls, bits, eps in buses:
        if cls == 'clock_trunk':
            continue
        for inst, _p in eps:
            refs[inst] = refs.get(inst, 0) + 1
    taps = {t_.get('tap') for t_ in (m.get('fork_taps') or {}).values()}
    names = {b_[0] for b_ in buses}
    left, done = [], []

    def pin(inst, port):
        it_ = by[inst]
        return K._leaf_pin(it_, port) or K.pin_xy(it_, M[it_.master], port.lstrip('*'))

    def removable(inst):
        it_ = by.get(inst)
        return (it_ is not None and inst.startswith('rly_') and it_.master.startswith('qkd_rly') and
                it_.master != 'qkd_rly_t1' and refs.get(inst, 0) == 2 and inst not in taps)
    for row in unresolved:
        bid0 = row['bus']
        k0 = next((k for k, b_ in enumerate(buses) if b_[0] == bid0), None)
        if k0 is None:
            left.append(row)
            continue
        _, cls, bits, eps = buses[k0]
        if any(by[e_[0]].master in ('qkd_rly_t1', 'qkd_rst_region') for e_ in eps):
            left.append(row)          # a reset / boot tree hop: its depth is a calendar constant, never re-seated here
            continue
        # the chain around the hop: hops[i] = bus index of hop i, nodes[i] -> nodes[i + 1]
        hops, nodes = [k0], [tuple(eps[0]), tuple(eps[1])]
        while True:        # upstream: the node before is a relay whose input net is a point-to-point hop
            a_ = nodes[0]
            if a_[1] != 'b' or not removable(a_[0]):
                break
            kp = next((k for k, b_ in enumerate(buses) if len(b_[3]) == 2 and tuple(b_[3][1]) == (a_[0], 'a')
                       and b_[1] not in ('clock_trunk', 'reset', 'constant')), None)
            if kp is None:
                break
            hops.insert(0, kp)
            nodes.insert(0, tuple(buses[kp][3][0]))
        while True:        # downstream
            b_ = nodes[-1]
            if b_[1] != 'a' or not removable(b_[0]):
                break
            kn = next((k for k, x_ in enumerate(buses) if len(x_[3]) == 2 and tuple(x_[3][0]) == (b_[0], 'b')
                       and x_[1] not in ('clock_trunk', 'reset', 'constant')), None)
            if kn is None:
                break
            hops.append(kn)
            nodes.append(tuple(buses[kn][3][1]))
        v = hops.index(k0)
        width, height = _frame(K, bid0, bits)
        caps = (cap0,)               # the greedy pass's own cap
        found = None
        windows = sorted(((i, j) for i in range(0, v + 1) for j in range(v + 1, len(nodes))
                          if j - i <= ROUTE_MAX_SPAN), key=lambda t: (t[1] - t[0], -t[0]))
        for cap, bgap in [(c_, g_) for c_ in caps for g_ in (21.6, 4.32)]:
            for i, j in windows:
                rem = {nodes[q][0] for q in range(i + 1, j)}
                src, dst = pin(*nodes[i]), pin(*nodes[j])
                src_end = None if by[nodes[i][0]].master.startswith('qkd_rly') else nodes[i]
                dst_end = None if by[nodes[j][0]].master.startswith('qkd_rly') else nodes[j]
                sp_ = _bfs_run(K, m, oidx, rem, src, src_end, dst, dst_end, width, height, cap, bgap)
                if sp_ is None:
                    continue
                st_ = _orient_check(K, sp_, src, src_end, dst, dst_end, width, height, cap)
                if st_ is not None:
                    found = (i, j, rem, st_, bgap, cap)
                    break
            if found:
                break
        if found is None:
            left.append(row)
            print(f'kv_pin_repair ROUTE: {bid0} ({bits} b, {row["um"]:.0f} um) no legal relay run', file=sys.stderr)
            continue
        i, j, rem, st_, bgap, cap = found
        hop_bids = [buses[hops[q]][0] for q in range(i, j)]
        new_eps, new_insts = [], []
        prev = nodes[i]
        stem = hop_bids[0]
        for t, (x, y, o) in enumerate(st_):
            nm = f"rly_pinfix_{stem.replace('__', '_')}_q{t}"
            while nm in by:
                nm += 'x'
            it = K.F.Inst(nm, f'qkd_rly_{bits}', x, y, width - K.SHAVE, height - K.SHAVE, o, kind='relay', region='relay')
            new_insts.append(it)
            new_eps.append([prev, (nm, 'a')])
            prev = (nm, 'b')
        new_eps.append([prev, nodes[j]])
        hb = []
        for t, e_ in enumerate(new_eps):
            nb_ = stem if t == 0 else f'{stem}__pinfix{t}'
            while t and nb_ in names:
                nb_ += '0'
            names.add(nb_)
            hb.append((nb_, cls, bits, e_))
        # splice: drop the window's hops, insert the new run where its first hop was; drop the ripped stations
        kill = {hops[q] for q in range(i, j)}
        first = min(kill)
        rebuilt = []
        for k, b_ in enumerate(buses):
            if k == first:
                rebuilt.extend(hb)
            if k in kill:
                continue
            if b_[1] == 'clock_trunk' and any(e_[0] in rem for e_ in b_[3]):
                b_ = (b_[0], b_[1], b_[2], [e_ for e_ in b_[3] if e_[0] not in rem])
            rebuilt.append(b_)
        buses[:] = rebuilt
        m['insts'][:] = [it_ for it_ in m['insts'] if it_.name not in rem] + new_insts
        for r_ in rem:
            by.pop(r_, None)
        oidx.gone |= rem
        for it_ in new_insts:
            by[it_.name] = it_
            oidx.add(it_)
        additions[:] = [a_ for a_ in additions if a_['relay'] not in rem]
        if m.get('group_launch_orientations'):
            m['group_launch_orientations'] = [g_ for g_ in m['group_launch_orientations'] if g_.get('relay') not in rem]
        base = bid0
        while _HOPSFX.search(base):
            base = _HOPSFX.sub('', base)
        delta = len(new_insts) - len(rem)
        m['relay_stages'][base] = m['relay_stages'].get(base, 0) + delta
        if base in (m.get('fork_stages') or {}):
            m['fork_stages'][base] += delta
        root, sink = nodes[0], nodes[-1]
        for it_ in new_insts:
            additions.append(dict(bus=stem, relay=it_.name, clock_source=root[0], launch=root, sink=sink, stages_added=1,
                                  before_um=round(row['um'], 3), route='bfs'))
        done.append(dict(bus=bid0, window=hop_bids, removed=sorted(rem), added=[it_.name for it_ in new_insts],
                         stages_delta=delta, block_gap=bgap, cap=cap))
        print(f'kv_pin_repair ROUTE: {bid0} ({bits} b, {row["um"]:.0f} um): window {hop_bids} -> {len(new_insts)} '
              f'stations (ripped {len(rem)}, block gap {bgap}, cap {cap})', file=sys.stderr)
    m['pin_route'] = done
    return left


def _choice(K, m, staged, x, y, width, height, ap, bp, cap, distance, detour=0.0, a_end=None, b_end=None,
            obstacle_index=None):
    if x < 4.32 or y < 4.32 or x+width+4.32 > m['die']['w'] or y+height+4.32 > m['die']['h']:
        return None
    orient = 'MY' if bp[0] < ap[0] else 'R0'
    inp_x, out_x = (x+width-K.SHAVE,x) if orient=='MY' else (x,x+width-K.SHAVE)
    left = _far(K, a_end, (inp_x, y+height/2), ap)
    remaining = _far(K, b_end, (out_x, y+height/2), bp)
    if left > cap or remaining >= distance-1+detour:
        return None
    obstacles = (obstacle_index.candidates(x-4.32, y-4.32, x+width+4.32, y+height+4.32)
                 if obstacle_index is not None else m['insts'])
    if any(min(x+width+4.32,i.x+i.w)-max(x-4.32,i.x) > .001 and
           min(y+height+4.32,i.y+i.h)-max(y-4.32,i.y) > .001 for i in obstacles+staged):
        return None
    return (remaining,x,y,left,out_x,orient)


def repair(K, m):
    M = K.masters(m, 1)
    m['assigned_ports'] = {n: {p: list(v) for p, v in mm.ports.items()}
                           for n, mm in M.items() if not n.startswith('qkd_rly')}
    by = {i.name: i for i in m['insts']}
    obstacle_index = CollisionIndex(m['insts'])
    additions, buses, unresolved, widened = [], [], [], {}
    for bid, cls, bits, eps in m['buses']:
        if len(eps) != 2 or cls in K.ABUT or cls in ('clock_trunk', 'reset', 'constant'):
            buses.append((bid, cls, bits, eps)); continue
        (a, pa), (b, pb) = eps
        ap, bp = K.pin_xy(by[a], M[by[a].master], pa.lstrip('*')), K.pin_xy(by[b], M[by[b].master], pb.lstrip('*'))
        # KV-BIND11 (OT_KV_D2D_PINS): a d2d end is measured to its farthest realized view pin
        if hasattr(K, '_d2d_pin'):
            K._d2d_pin(by[a], pa); K._d2d_pin(by[b], pb)
        hop_ = lambda p_, q_, first_: max(abs(p_[0]-q_[0])+abs(p_[1]-q_[1]), _far(K, (b, pb), p_, q_),  # noqa: E731
                                          _far(K, (a, pa), q_, p_) if first_ else 0.0)
        if hop_(ap, bp, True) <= (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH):
            buses.append((bid, cls, bits, eps)); continue
        width, height = 52.68, 30.24 if bits <= 512 else K.up(bits * .048 + 4, K.GY)
        if __import__('os').environ.get('OT_KV_RLY_STD', '0') == '1':
            import kv_rly_std as RS          # Q-KVSYS-RLY: the relay-standard row (default off: unchanged)
            width, height, _ = RS.layout(bits, RS.frame_rev(bid))
            width, height = width + K.SHAVE, max(height + K.SHAVE, bits * .048 + 4 if bits > 512 else 0.0)
            height = K.up(height, K.GY) if height > RS.STD[528][1] + K.SHAVE else height
        initial_ap = ap
        ap0 = ap
        routed = None
        if PINFIX_ROUTE and ROUTE_FIRST:
            # OT_KV_PINFIX_ROUTE: the fewest stations of an exhaustive search first; the greedy stages only if it finds none
            routed = _route_insert(K, m, obstacle_index, bid, cls, bits, (a, pa), ap, (b, pb), bp, width, height,
                                   300 if a.startswith('wctl_') and bid.startswith('wencoded_') else
                                   (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH))
        if routed is not None:
            staged, chain, previous, ap = routed
        for attempt in ((0, 1) if routed is None else ()):
          # KV-PLAN3 10-18: attempt 1 (only after attempt 0 left the hop over reach) searches the 40-half-cell ring
          # with a bounded detour at EVERY stage (crowded group / PC control channels: 2-7 residual hops per plan)
          ap = ap0
          chain, staged, previous = [], [], (a,pa)
          # Several registered stages are necessary for a long fault-chain return.
          # Each stage is chosen in free channel space; a trapped chain is rolled back.
          for stage in range(math.ceil((abs(ap[0]-bp[0])+abs(ap[1]-bp[1]))/200)+12):
              cap = 300 if previous[0].startswith('wctl_') and bid.startswith('wencoded_') else (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH)
              if hop_(ap, bp, not staged) <= cap:
                  break
              ae_ = None if staged else (a, pa)
              distance = max(abs(ap[0]-bp[0])+abs(ap[1]-bp[1]), _far(K, (b, pb), ap, bp))
              fraction = min(.5, 350/distance)
              target = (ap[0]+fraction*(bp[0]-ap[0])-width/2,
                        ap[1]+fraction*(bp[1]-ap[1])-height/2)
              grid = K.GRID/2
              choices = []
              for x,y in _cands(K, target, grid, 16):
                  c_ = _choice(K, m, staged, x, y, width, height, ap, bp, cap, distance, a_end=ae_, b_end=(b, pb),
                               obstacle_index=obstacle_index)
                  if c_:
                      choices.append(c_)
              if not choices and (attempt == 1 or not widened.get(bid)):
                  # Q-KVSYS-HOP 2026-10-16: a pin boxed in by blocks (d2d_kv fwd_* 1-bit pins, ~1,200 um to the first
                  # relay) finds no spot within 16 half-cells; look again up to 40 (only where repair failed before)
                  widened[bid] = True
                  ring = [(x, y) for x, y in _cands(K, target, grid, 40)]
                  for x, y in ring:
                      # a boxed-in pin may step AROUND its blocker first (bounded detour; later stages must progress)
                      c_ = _choice(K, m, staged, x, y, width, height, ap, bp, cap, distance, detour=cap, a_end=ae_, b_end=(b, pb),
                                   obstacle_index=obstacle_index)
                      if c_:
                          choices.append(c_)
              if not choices:
                  break
              remaining,x,y,left,out_x,orient=min(choices)
              name='rly_pinfix_'+bid.replace('__','_')+'_'+str(stage)
              it=K.F.Inst(name,f'qkd_rly_{bits}',x,y,width-K.SHAVE,height-K.SHAVE,orient,kind='relay',region='relay')
              staged.append(it)
              sbid=bid if not chain else bid+'__pinfix'+str(stage)
              chain.append((sbid,cls,bits,[previous,(name,'a')]))
              previous=(name,'b');ap=(out_x,y+height/2)
          if hop_(ap, bp, not staged) <= (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH):
            break
        if hop_(ap, bp, not staged) > (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH):
            unresolved.append(dict(bus=bid,um=abs(initial_ap[0]-bp[0])+abs(initial_ap[1]-bp[1])));
            buses.append((bid,cls,bits,eps)); continue
        if not staged:
            buses.append((bid,cls,bits,eps));continue
        m['insts'].extend(staged)
        for it in staged:
            obstacle_index.add(it)
        by.update({i.name:i for i in staged})
        buses.extend(chain+[(bid+'__pinfix'+str(len(staged)),cls,bits,[previous,(b,pb)])])
        base=bid.split('__r')[0]
        m['relay_stages'][base]=m['relay_stages'].get(base,0)+len(staged)
        for index,it in enumerate(staged):
            additions.append(dict(bus=bid,relay=it.name,clock_source=a,launch=(a,pa),sink=(b,pb),stages_added=1,
                                  before_um=round(abs(initial_ap[0]-bp[0])+abs(initial_ap[1]-bp[1]),3)))
    if PINFIX_ROUTE and unresolved:
        unresolved = _reseat_unresolved(K, m, buses, by, obstacle_index, unresolved, additions)
    mixed = set()
    for row in additions:      # KVR-DERIVE: the launching pin's clock (relay_trunk), not the source's first trunk
        n=row['relay']
        clock, dom = relay_trunk(buses, by, row['launch'], row['sink'])
        row['domain'] = dom
        row['clock'] = buses[clock][0]
        if dom == 'mixed':
            mixed.add(row['bus'])
        bid,cl,bits,eps=buses[clock];buses[clock]=(bid,cl,bits,list(eps)+[(n,'ck')])
    bad = [r_ for r_ in additions if trunk_domain(r_['clock']) != ('core' if r_['domain'] == 'mixed' else r_['domain'])]
    if bad:
        raise ValueError(f'kv_pin_repair: relay clock domain != launching pin domain: {bad[:4]}')
    m['buses']=buses
    m['pin_repair']=dict(added=additions, unresolved=unresolved, mixed_domain_buses=sorted(mixed),
                         method='fixed master pins; registered channel relay; no leaf traversal; relay clock = the '
                                'launching pin domain (kv_pin_repair.relay_trunk)')
    return m
