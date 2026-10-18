"""KV-LANDSLOT 10-18 (landed-regions standard; lanes/KV-CLOCK.md OWED): the KV die planner RESERVES THE LANDING FRAME.

kv_fwd_lanes.py turns the LAST relay station of every data run that crosses core clock trees (relays on the driver's
tree X, receiver on tree Y != X) into a landing qkd_landsh*_<S> in the same place.  The 36 / 296 / 528-b landings do not
fit the station outlines (KV-LANEKITS gates: GPL util 181 / 128 / 126 %); their kits are 25.92 x 21.6, 51.84 x 47.52 and
51.84 x 82.08 um (kv_rly_std.LAND).  This pass runs on the finished plan (after the relay chains and the pin repair):

  for every point-to-point data bus  relay R (qkd_rly_<W>, tree X) -> block B (tree Y, X & Y = {}):
    R's frame becomes the LANDING frame qkd_rly_<W>[r<rev>]_land (kv_rly_std.layout(..., land=True): the same replicas
    at the landing outlines) and is moved to the RECEIVING BLOCK FACE nearest B's pin (LAND_GAP from the frame, the
    kv_pin_repair keep-out), b face towards B, slid along the face to the first free spot whose in-hop from the previous
    stage stays within the hop reach  -> tier 'abut';
    else the free spot nearest B's pin within reach of both ends (around the old station)   -> tier 'near';
    else R stays a station frame (recorded 'unslotted': kv_fwd_lanes.py refuses a physical laned run with any).
  Stage counts, chains and clocks are unchanged (only the last frame's master / outline / place / orient).
  Verified after the pass: no overlap, no new pin-hop over the reach (a landing that adds one is put back, unslotted).
"""
import re

LAND_GAP = 4.32          # um, landing frame <-> receiving block frame (kv_pin_repair keeps 4.32 um to every frame)
RST_BUS = re.compile(r'^(rst_|hboot|rrs_)')
RLY_MASTER = re.compile(r'^qkd_rly_(\d+)$')
CELL = 43.2


def _rect(it, pad=0.0):
    return (it.x - pad, it.y - pad, it.x + it.w + pad, it.y + it.h + pad)


class _Index:
    def __init__(self, items):
        self.cells, self.rects = {}, {}
        for n, r in items:
            self.add(n, r)

    def _keys(self, r):
        for gx in range(int(r[0] // CELL), int(r[2] // CELL) + 1):
            for gy in range(int(r[1] // CELL), int(r[3] // CELL) + 1):
                yield (gx, gy)

    def add(self, n, r):
        self.rects[n] = r
        for k in self._keys(r):
            self.cells.setdefault(k, set()).add(n)

    def drop(self, n):
        r = self.rects.pop(n, None)
        if r is not None:
            for k in self._keys(r):
                self.cells.get(k, set()).discard(n)

    def hits(self, r, skip=()):
        seen = set()
        for k in self._keys(r):
            for n in self.cells.get(k, ()):
                if n in seen or n in skip:
                    continue
                seen.add(n)
                q = self.rects[n]
                if q[0] < r[2] - 1e-6 and r[0] < q[2] - 1e-6 and q[1] < r[3] - 1e-6 and r[1] < q[3] - 1e-6:
                    return n
        return None


def _frame(K, RS, bits, rev):
    fw, fh, _ = RS.layout(bits, rev, land=True)
    fw, fh = fw + K.SHAVE, max(fh + K.SHAVE, bits * .048 + 4 if bits > 512 else 0.0)
    fh = K.up(fh, K.GY) if fh > RS.STD[528][1] + K.SHAVE else fh
    return fw - K.SHAVE, fh - K.SHAVE           # instance outline (frame - SHAVE, as every relay)


def _pins(x, y, w, h, orient):
    a = (x + w if orient == 'MY' else x, y + h / 2)
    b = (x if orient == 'MY' else x + w, y + h / 2)
    return a, b


def reserve(K, m, gap=LAND_GAP):
    import kv_rly_std as RS
    by = {i.name: i for i in m['insts']}
    Wd, Hd = m['die']['w'], m['die']['h']
    tree = {}
    for bid, cl, _b, eps in m['buses']:
        if cl == 'clock_trunk' and bid.startswith('clk_core_'):
            for inst, _p in eps[1:]:
                tree.setdefault(inst, set()).add(bid[len('clk_core_'):])
    isrly = lambda n: n in by and by[n].kind == 'relay' and RLY_MASTER.match(by[n].master)  # noqa: E731
    into = {}
    for bid, cl, bits, eps in m['buses']:
        if len(eps) == 2 and eps[1][1] == 'a' and isrly(eps[1][0]):
            into[eps[1][0]] = (bid, eps[0])
    M = K.masters(m, 1)

    def pin(inst, port):
        it = by[inst]
        try:
            return K._leaf_pin(it, port) or K.pin_xy(it, M[it.master], port.lstrip('*'))
        except (KeyError, TypeError):
            return (it.x + it.w / 2, it.y + it.h / 2)
    hop = K.HOP_REACH if getattr(K, 'HOP', False) else K.PIN_REACH
    phy = getattr(K, 'PHY_REG', False)
    cands = []
    for bid, cl, bits, eps in m['buses']:
        if len(eps) != 2 or cl in K.ABUT or cl in ('clock_trunk', 'reset', 'constant') or RST_BUS.match(bid):
            continue
        (R, pr), (B, pb) = eps
        # the receiver is any non-station block: the V word forks / taps (qkd_pvfork / qkd_pvtap*, plan kind 'relay', on
        # clk_core_c) receive the 16 pvin_<s> 1055-b runs from the stack trees (lstest ae620dbeb: 36 unslotted wide
        # landings, all pvin -> pvfork and the 2 aq runs, because kind 'relay' excluded the forks)
        if pr != 'b' or not isrly(R) or B not in by or isrly(B) or R not in into:
            continue
        tx, ty = tree.get(R, set()), tree.get(B, set())
        if not tx or not ty or tx & ty:
            continue
        cands.append((R, B, pb, bits, bid))
    keep = [(it.name, _rect(it)) for it in m['insts']] + \
        [(f'keepout:{k[0]}', (k[1], k[2], k[1] + k[3], k[2] + k[4])) for k in m.get('keepouts', [])]
    idx = _Index(keep)
    rows, moved = [], {}
    for R, B, pb, bits, bid in sorted(cands):
        it, ib = by[R], by[B]
        ibid, (P, pp) = into[R]
        rev = RS.frame_rev(re.sub(r'^pinfix_', '', bid))
        w, h = _frame(K, RS, bits, rev)
        bp, ppt = pin(B, pb), pin(P, pp)
        lim = min(hop, K.width_reach(bits))
        lim2 = min(lim, K.PHY_REACH) if (phy and ib.master in K.PHY_MASTERS) else lim
        lim1 = min(lim, K.PHY_REACH) if (phy and P in by and by[P].master in K.PHY_MASTERS) else lim
        a0, b0 = _pins(it.x, it.y, it.w, it.h, it.orient)
        old = dict(master=it.master, x=it.x, y=it.y, w=it.w, h=it.h, orient=it.orient)
        old_h1 = abs(a0[0] - ppt[0]) + abs(a0[1] - ppt[1])
        old_h2 = abs(b0[0] - bp[0]) + abs(b0[1] - bp[1])
        idx.drop(R)

        def ok(x, y, o, skipB=False):
            if x < 4.32 or y < 4.32 or x + w + 4.32 > Wd or y + h + 4.32 > Hd:
                return None
            a_, b_ = _pins(x, y, w, h, o)
            h1 = abs(a_[0] - ppt[0]) + abs(a_[1] - ppt[1])
            h2 = abs(b_[0] - bp[0]) + abs(b_[1] - bp[1])
            if h1 > max(lim1, old_h1) + 1e-6 or h2 > max(lim2, old_h2) + 1e-6:
                return None
            r = (x - 4.32, y - 4.32, x + w + 4.32, y + h + 4.32)
            if idx.hits(r, skip={B} if skipB else ()):
                return None
            if skipB:
                q = _rect(ib, gap - 0.01)
                if q[0] < x + w and x < q[2] and q[1] < y + h and y < q[3]:
                    return None
            return (h1, h2)
        got = None
        # tier 1: abutted to the receiving face nearest B's pin, b face towards B
        x0, y0, x1, y1 = _rect(ib)
        dface = dict(W=abs(bp[0] - x0), E=abs(bp[0] - x1), S=abs(bp[1] - y0), N=abs(bp[1] - y1))
        face = min(dface, key=dface.get)
        flow = 'R0' if ppt[0] <= bp[0] else 'MY'
        for g in [gap + k * K.GY for k in range(9)]:
            for s in [0.0] + [sg * j * K.GY for j in range(1, 41) for sg in (1, -1)]:
                if face == 'W':
                    x, y, o = K.F.dn(x0 - g - w, K.GX), K.up(bp[1] - h / 2 + s, K.GY), 'R0'
                elif face == 'E':
                    x, y, o = K.up(x1 + g, K.GX), K.up(bp[1] - h / 2 + s, K.GY), 'MY'
                elif face == 'S':
                    x, y, o = K.up(bp[0] - w / 2 + s, K.GX), K.F.dn(y0 - g - h, K.GY), flow
                else:
                    x, y, o = K.up(bp[0] - w / 2 + s, K.GX), K.up(y1 + g, K.GY), flow
                r_ = ok(x, y, o, skipB=True)
                if r_:
                    got = ('abut', x, y, o, r_, round(g, 3))
                    break
            if got:
                break
        if got is None:
            # tier 2: the free spot nearest B's pin within reach of both ends, around the old station
            best = None
            for i in range(-40, 41):
                for j in range(-40, 41):
                    x, y = K.up(it.x + i * 4.32, K.GX), K.up(it.y + j * 4.32, K.GY)
                    for o in (it.orient, flow):
                        r_ = ok(x, y, o, skipB=True)
                        if r_ and (best is None or r_[1] < best[4][1]):
                            best = ('near', x, y, o, r_, None)
            got = best
        if got is None:
            # tier 3 (lstest ae620dbeb: aq_ES / aq_WS last stations beside the crowded astk N face): a wider ring at 8.64-um
            # steps; the reach of both hops still bounds the spot
            best = None
            for i in range(-120, 121):
                for j in range(-120, 121):
                    if max(abs(i), abs(j)) <= 20:
                        continue
                    x, y = K.up(it.x + i * 8.64, K.GX), K.up(it.y + j * 8.64, K.GY)
                    for o in (it.orient, flow):
                        r_ = ok(x, y, o, skipB=True)
                        if r_ and (best is None or r_[1] < best[4][1]):
                            best = ('near', x, y, o, r_, None)
            got = best
        row = dict(relay=R, bus=bid, bits=bits, rev=rev, receiver=B, receiver_port=pb, face=face,
                   src_tree=sorted(tree[R]), dst_tree=sorted(tree[B]), old=old, old_hops=[round(old_h1, 1), round(old_h2, 1)],
                   lim=[lim1, lim2], frame=[round(w, 3), round(h, 3)])
        if got is None:
            idx.add(R, _rect(it))
            row['tier'] = 'unslotted'
        else:
            tier, x, y, o, (h1, h2), g = got
            it.master = f'qkd_rly_{bits}' + (f'r{rev}' if rev else '') + RS.LAND_SUFFIX
            it.x, it.y, it.w, it.h, it.orient = x, y, w, h, o
            idx.add(R, _rect(it))
            moved[R] = old
            row.update(tier=tier, at=[x, y, o], gap=g, hops=[round(h1, 1), round(h2, 1)])
        rows.append(row)
    # verification: overlaps and pin hops against the reach, before vs after (a landing adding a violation goes back)
    reach = min(hop, getattr(K, 'KV_REACH', 0) or hop)
    put_back = []
    for _ in range(3):
        bad = K.pin_reach(m, K.masters(m, 1), reach=reach)['all']
        hit = {e['a'].split('.')[0] for e in bad} | {e['b'].split('.')[0] for e in bad}
        lim_of = {r['relay']: max(r['lim'] + r['old_hops']) for r in rows if r['relay'] in moved}
        worse = sorted(n for n in hit & set(moved)
                       if any(n in (e['a'].split('.')[0], e['b'].split('.')[0]) and e['um'] > lim_of[n] + 1e-6 for e in bad))
        if not worse:
            break
        for n in worse:
            o_ = moved.pop(n)
            it = by[n]
            it.master, it.x, it.y, it.w, it.h, it.orient = o_['master'], o_['x'], o_['y'], o_['w'], o_['h'], o_['orient']
            put_back.append(n)
            for r in rows:
                if r['relay'] == n:
                    r['tier'] = 'unslotted'
                    r['why'] = 'landing move added a pin hop over the reach'
    leg = K.check(m)
    tiers = {}
    for r in rows:
        tiers[r['tier']] = tiers.get(r['tier'], 0) + 1
    rep = dict(schema='opentallas.qwen_kv_land_slots.v1', gap_um=gap, crossings=len(rows), tiers=tiers,
               unslotted=[r['relay'] for r in rows if r['tier'] == 'unslotted'], put_back=put_back,
               legality=dict(overlaps=leg['overlaps'], outside=leg['outside'], examples=leg['overlap_examples'][:5]),
               masters=sorted({by[n].master for n in moved}), rows=rows)
    m['land_slots'] = rep
    return m
