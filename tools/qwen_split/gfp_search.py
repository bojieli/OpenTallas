#!/usr/bin/env python3
"""GLOBAL-FP-Q own placer: simulated annealing over legal hub slots + spine width, with the logical reduction map
(block -> slot assignment, in-block symmetry, then tile-level swaps) re-solved inside the loop.

Objective (same terms as gfp_core.score, fast centroid model inside the loop, exact scorer on the result):
    J = exposed stage-cycles/token (217 x ME loop + 73 x collective loop + 36 x KV loop)
        + LAMBDA x traffic-weighted bit-um + MU x relay flops  (+ overlap / outside penalties)
Explicit reach/relay penalty: every bus costs ceil(L/490) stages on its loop and (stages-1) x bits relay flops.
"""
import copy, math, random, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gfp_core as C  # noqa: E402
import gfp_candidates as G  # noqa: E402

LAMBDA = 1.0 / 2.0e7      # 1 exposed cycle ~ 2e7 traffic bit-um (keeps both terms O(1e4))
MU = 1.0 / 100.0          # 1 exposed cycle ~ 100 relay flops


class FastReduction:
    """Centroid model of the 48 block trees + block words; exact per-bus centroid->longest offsets from baseline."""

    def __init__(self, die, B):
        self.die, self.B = die, B
        tp = die.g.pins['qfd_tile_nk']
        self.pc = {p: tp[p].mean(0) for p in ('t_out', 'n_a', 'n_b', 'n_y')}   # R0 local pin centroids
        self.blocks = {}
        for k in range(48):
            recs = sorted(B.tree[k], key=lambda r: int(r['b'].split('_')[2]))
            cg0, rg0 = B.slot[k]
            edges = []
            for r in recs:
                (sn, _), (dn, _) = r['ends'][0], r['ends'][-1]
                sp, dp = r['port'][0], r['port'][-1]
                sc = (int(sn.split('_')[1]) - 4 * cg0, int(sn.split('_')[2]) - 4 * rg0)
                dc = (int(dn.split('_')[1]) - 4 * cg0, int(dn.split('_')[2]) - 4 * rg0)
                edges.append((sn, sp, sc, dn, dp, dc))
            bw = B.bword[k]
            root = bw['ends'][0][0]
            rc = (int(root.split('_')[1]) - 4 * cg0, int(root.split('_')[2]) - 4 * rg0)
            self.blocks[k] = dict(edges=edges, root=root, rc=rc, port=bw['ends'][1][0], port_loc=bw['ends'][1][1])

    def tile_xy(self, model):
        """physical tile (c, r) -> origin, orientation flag arrays."""
        X = np.zeros((48, 16)); Y = np.zeros((48, 16)); MYf = np.zeros((48, 16), bool)
        for c in range(48):
            for r in range(16):
                i = model[f't_{c}_{r}']; X[c, r] = i['x']; Y[c, r] = i['y']; MYf[c, r] = i['o'] in ('MY', 'R180')
        return X, Y, MYf

    def pin(self, X, Y, MYf, c, r, p):
        lx, ly = self.pc[p]
        return X[c, r] + np.where(MYf[c, r], 449.28 - lx, lx), Y[c, r] + ly

    def costs(self, model, ds):
        """cost[k, slot, sym] = (path stages, bit-um) for every logical block, slot and symmetry (vectorised)."""
        X, Y, MYf = self.tile_xy(model)
        slots = sorted(self.B.slot_of)
        S = len(slots)
        cg = np.array([s[0] for s in slots])[:, None].repeat(8, 1); rg = np.array([s[1] for s in slots])[:, None].repeat(8, 1)
        sym = np.arange(8)[None, :].repeat(S, 0)

        def phys(lc):
            c, r = lc
            c = np.full(sym.shape, c); r = np.full(sym.shape, r)
            sw = (sym & 4) > 0
            c2 = np.where(sw, r, c); r2 = np.where(sw, c, r)
            c2 = np.where(sym & 1, 3 - c2, c2); r2 = np.where(sym & 2, 3 - r2, r2)
            return 4 * cg + c2, 4 * rg + r2
        path = np.zeros((48, S, 8)); bitum = np.zeros((48, S, 8))
        for k, blk in self.blocks.items():
            out = {}
            for sn, sp, sc, dn, dp, dc in blk['edges']:
                a = phys(sc); b = phys(dc)
                ax, ay = self.pin(X, Y, MYf, a[0], a[1], sp); bx, by = self.pin(X, Y, MYf, b[0], b[1], dp)
                L = np.abs(ax - bx) + np.abs(ay - by)
                st = np.maximum(1, np.ceil((L + 49.0) / C.REACH))          # +49 um: 514-bit word spread on the face
                t0 = out.get(sn, 0) if sp == 'n_y' else 0
                out[dn] = np.maximum(out.get(dn, 0), t0 + st)
                bitum[k] += L * 514
            a = phys(blk['rc'])
            ax, ay = self.pin(X, Y, MYf, a[0], a[1], 'n_y')
            pi = model[blk['port']]; loc = blk['port_loc']
            lx, ly = loc[:, 0].mean(), loc[:, 1].mean()
            if pi['o'] in ('MY', 'R180'): lx = pi['w'] - lx
            if pi['o'] in ('MX', 'R180'): ly = pi['h'] - ly
            L = np.abs(ax - (pi['x'] + lx)) + np.abs(ay - (pi['y'] + ly))
            path[k] = out[blk['root']] + np.maximum(1, np.ceil((L + 49.0) / C.REACH)) + ds[blk['port']]
            bitum[k] += L * 514
        return path, bitum, slots

    def assign(self, model, ds, power=4.0):
        from scipy.optimize import linear_sum_assignment
        path, bitum, slots = self.costs(model, ds)
        tot = path ** power + bitum / 1e7
        sbest = tot.argmin(2)
        cm = np.take_along_axis(tot, sbest[..., None], 2)[..., 0]
        rows, cols = linear_sum_assignment(cm)
        P = {}; worst = 0; bu = 0.0
        for k, j in zip(rows, cols):
            s = int(sbest[k, j]); P.update(self.B.mapping(k, slots[j], s))
            worst = max(worst, path[k, j, s]); bu += bitum[k, j, s]
        return P, int(worst), bu, [(int(k), slots[j], int(sbest[k, j])) for k, j in zip(rows, cols)]


def fast_eval(die, model, FR):
    ev = [C.bus_geom(r, model) for r in die.recs]
    ds = G.downstream_stages(die, model)
    P, red_fast, _, _ = FR.assign(model, ds)
    me = C.me_loop(die, model, [C.bus_geom(r, model, P) if (r['c'] == 'tree_block' or r['b'].startswith('bword_')) else ev[k]
                                for k, r in enumerate(die.recs)], P)
    ll = C.layer_loops(die, ev)
    exposed = C.ME_OPS * me['me_loop'] + C.ARS * ll['coll_loop'] + C.LAYERS * ll['kv_loop']
    tb = sum(e[0] * r['act'] for e, r in zip(ev, die.recs)); rf = sum((C.stages(e[1]) - 1) * r['n'] for e, r in zip(ev, die.recs))
    return exposed + LAMBDA * tb + MU * rf, dict(exposed=exposed, me=me['me_loop'], bd=me['bd'], red=me['red'], coll=ll['coll_loop'], kv=ll['kv_loop'], P=P)


# ------------------------------------------------------------------ hub annealer
def legal(model, die, x0, x1):
    """Hub instances inside the spine, inside the die, no instance overlap, >= CHPAD between distinct hub groups."""
    groups = [G.CORE + G.CLK, G.UP4, G.TOP] + list(G.BAND.values())
    for grp in groups:
        for n in grp:
            i = model[n]
            if grp is not G.TOP and (i['x'] < x0 + 20 or i['x'] + i['w'] > x1 - 20): return False
    if G.outside(model, die.die): return False
    hub = sum(groups, [])
    if G.overlaps(model, hub, pad=0.0): return False
    bbs = [G.bbox(model, g_) for g_ in groups[1:]] + [G.bbox(model, G.CORE)]
    for a in range(len(bbs)):
        for b in range(a + 1, len(bbs)):
            A, Bq = bbs[a], bbs[b]
            if A[0] < Bq[2] + CHPAD and Bq[0] < A[2] + CHPAD and A[1] < Bq[3] + CHPAD and Bq[1] < A[3] + CHPAD:
                # the up4 stack legitimately nests beside ctlm inside the core bbox: check instance-level only
                if groups[1] in (groups[1:] + [G.CORE])[a:a + 1] or groups[1] in (groups[1:] + [G.CORE])[b:b + 1]:
                    continue
                return False
    return True


CHPAD = 40.0
SPINE_W0 = G.SPINE_X1 - G.SPINE_X0


def anneal(die, base, iters=600, seed=1, log=print, init='architect'):
    rnd = random.Random(seed)
    FR = FastReduction(die, G.Blocks(die))
    gd = G.group_dims(base)
    st = dict(ws=4924.8, core_dy=0.0, core_dx=0.0, xs_c=0, band={b: ['L', None, 'R0'] for b in range(3)}, up4=None, clk=None)
    pl = G.plan_cluster(base, st['ws'])
    for b, v in pl['band'].items(): st['band'][b] = list(v)
    st['up4'] = list(pl['up4']); st['clk'] = list(pl['clk'])
    if init == 'current':      # start from today's wide27 hub (7.32-mm spine, today's group positions/orientations)
        st['ws'] = SPINE_W0
        for b in range(3):
            x0_, y0_, _, _ = G.bbox(base, G.BAND[b])
            st['band'][b] = ['L', y0_, base[f'sp_port_tiles_{b}']['o'] if base[f'sp_port_tiles_{b}']['o'] in ('R0', 'MX') else 'R0']
        ux, uy, _, _ = G.bbox(base, G.UP4); st['up4'] = [ux - G.SPINE_X0, uy]
        st['clk'] = [base['clk_rx']['x'] - G.SPINE_X0, base['clk_rx']['y']]
        st['core_dx'] = base['sp_vector_memory']['x'] - ((G.SPINE_X0 + G.SPINE_X1) / 2 - base['sp_vector_memory']['w'] / 2)

    def build(s):
        plan = dict(core_y=base['sp_vector_memory']['y'] + s['core_dy'], core_dx=s.get('core_dx', 0.0), band={b: tuple(v) for b, v in s['band'].items()},
                    up4=tuple(s['up4']), clk=tuple(s['clk']))
        m, info = G.hub_layout(base, s['ws'], plan)
        if s['xs_c']:      # x tap centred on the VM top edge; SU stack lifted by one x-tap height + channel
            vm = m['sp_vector_memory']
            lift = m['xs_tap']['h'] + 108
            G.translate(m, [n for n in G.CORE if n not in ('sp_vector_memory', 'xs_tap')] + G.UP4, 0, lift)
            m['xs_tap']['x'] = round(vm['x'] + vm['w'] / 2 - m['xs_tap']['w'] / 2, 3); m['xs_tap']['y'] = round(vm['y'] + vm['h'] + 54, 3)
        return m, info

    def J(s):
        m, info = build(s)
        x0, x1 = info['spine_x']
        if not legal(m, die, x0, x1): return None, None, None
        j, d = fast_eval(die, m, FR)
        return j, d, (m, info)

    cur = copy.deepcopy(st); jc, dc, mc = J(cur)
    assert jc is not None, 'start state illegal'
    best = (jc, copy.deepcopy(cur), dc, mc)
    T0 = 400.0; t0 = time.time()
    for it in range(iters):
        T = T0 * (1 - it / iters) + 5
        s = copy.deepcopy(cur); mv = rnd.random()
        if mv < 0.15: s['ws'] = min(7320.7, max(4708.8 + 2 * 108, s['ws'] + rnd.choice((-1, 1)) * 108 * rnd.randint(1, 6)))
        elif mv < 0.20: s['core_dy'] += rnd.choice((-1, 1)) * 108 * rnd.randint(1, 8)
        elif mv < 0.25: s['core_dx'] += rnd.choice((-1, 1)) * 108 * rnd.randint(1, 8)
        elif mv < 0.32: s['xs_c'] ^= 1
        elif mv < 0.85:
            b = rnd.randrange(3); v = s['band'][b]; q = rnd.random()
            if q < 0.2: v[0] = rnd.choice('LRC')
            elif q < 0.35: v[2] = 'MX' if v[2] == 'R0' else 'R0'
            else: v[1] += rnd.choice((-1, 1)) * 108 * rnd.randint(1, 20)
        elif mv < 0.93: s['up4'][1] += rnd.choice((-1, 1)) * 108 * rnd.randint(1, 10)
        else: s['clk'][0] += rnd.choice((-1, 1)) * 108 * rnd.randint(1, 10)
        j, d, m = J(s)
        if j is None: continue
        if j < jc or rnd.random() < math.exp((jc - j) / T):
            cur, jc, dc, mc = s, j, d, m
            if j < best[0]:
                best = (j, copy.deepcopy(s), d, m)
                log(f'  it{it} T{T:.0f} J{j:.0f} exposed{d["exposed"]} me{d["me"]} bd{d["bd"]} red{d["red"]} coll{d["coll"]} kv{d["kv"]} ws{s["ws"]:.0f} xs_c{s["xs_c"]} {time.time()-t0:.0f}s')
    return best


def tile_swap_refine(die, model, P, iters=20000, seed=2, log=print):
    """Tile-level swaps of the logical->physical map (general block shapes), exact per-block path model."""
    rnd = random.Random(seed)
    B = G.Blocks(die)
    ds = G.downstream_stages(die, model)
    inv = {v: k for k, v in P.items()}
    blk_of = {t: k for k, ts in B.tiles.items() for t in ts}

    def bcost(k, Pm):
        out = {}; bu = 0.0
        for r in sorted(B.tree[k], key=lambda r: int(r['b'].split('_')[2])):
            hp, L, _, ends = C.bus_geom(r, model, Pm)[:4]; bu += hp
            src, dst = ends[0][0], ends[-1][0]
            t0 = out.get(src, 0) if r['port'][0] == 'n_y' else 0
            out[dst] = max(out.get(dst, 0), t0 + C.stages(L))
        hp, L, _, ends = C.bus_geom(B.bword[k], model, Pm)[:4]; bu += hp
        return out[ends[0][0]] + C.stages(L) + ds[B.bword[k]['ends'][1][0]], bu
    cost = {k: bcost(k, P) for k in range(48)}

    def tot(cs):
        return sum(p ** 4 for p, _ in cs.values()) + sum(b for _, b in cs.values()) / 1e7
    J = tot(cost)
    phys = [f't_{c}_{r}' for c in range(48) for r in range(16)]
    acc = 0
    for it in range(iters):
        a = rnd.choice(phys); ca, ra = map(int, a.split('_')[1:])
        cb = min(47, max(0, ca + rnd.randint(-3, 3))); rb = min(15, max(0, ra + rnd.randint(-2, 2)))
        b = f't_{cb}_{rb}'
        if a == b: continue
        la, lb = inv[a], inv[b]
        ks = {blk_of[la], blk_of[lb]}
        P[la], P[lb] = b, a
        new = {k: bcost(k, P) for k in ks}
        old = {k: cost[k] for k in ks}
        cost.update(new); Jn = tot(cost)
        T = 2.0e4 * (1 - it / iters) + 1
        if Jn < J or rnd.random() < math.exp((J - Jn) / T):
            J = Jn; inv[a], inv[b] = lb, la; acc += 1
        else:
            P[la], P[lb] = a, b; cost.update(old)
        if it % 5000 == 0:
            log(f'  swap it{it} J{J:.4g} worst{max(p for p, _ in cost.values())} acc{acc}')
    return P, max(p for p, _ in cost.values())
