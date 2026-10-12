#!/usr/bin/env python3
"""[vm8] 2026-10-11 hardened sub-tiles of a VM8 half (make_vm_vcut8.py VM_ST=<rows>, VM_ST_COLS=<cols>).

WHY: every bf62ad44e / clock-grid route of the open halves stalled in CTS hold repair or missed TT setup on ONE placement
of 350 x 1,000 um with 33k-60k core sinks (single root 284..490 ps FF insertion; grid roots 2x7 / 2x10 still left
355-667 ps tails).  Owner audit (el1011-hbm-vm8.log): class 1 one clock root per tile, <= ~15k sinks, <= ~600 um tree;
class 4 no single-cycle wire > ~500 um (every tile seam is a register, tile width <= ~175 um); class 6 budgeted seam
tracks.  This is the SMH recipe (6f7adfcbc): hardened tiles with their own root, face taps and reset relay, registered
seams, a zero-logic abutment parent with the half's data pins unchanged.

HOW (cycle-exact, generic over the generated RTL): the half (VM_ST ports) is flattened to bit level by yosys
(st_yosys.sh; SRAM / ot_fwd_clk_inv kept as cells) and cut here:
  * units: every flop; every logic cluster is merged with the flops / macro pins it drives, so a cut net is always driven
    by a flop or a macro output, never by logic;
  * anchors: port bits (the tile under the pin), the slice macros and the slice / root core (the core tile); every other
    unit is placed on the Manhattan tile path between its nearest upstream and downstream anchors, in proportion to its
    sequential position (adjacent stages are in the same or an edge-adjacent tile);
  * seams (r2, FULL CYCLE): every negedge flop is merged into the unit of its posedge driver(s), and a cut leaving a pure
    negedge relay carries the relay's posedge source Q instead (same value at every posedge capture), so every seam is a
    posedge flop -> tile pin -> tile pin -> posedge flop crossing between tile roots: full cycle, 0 cycles added, no
    inserted flop (r1 half-cycle hand-offs failed tile IO timing: negedge-launched outputs had ~90 ps of budget).  Where
    a full-cycle hop must cross two tile edges, make_vm_vcut8 VM_ST_K adds uniform per-port stages (report k_demand);
  * tiles sit on the PDN strap pitch (make_vm_vcut8 st_rows / st_cols), seam pins only on free tracks (r1 DRT-0255);
  * row-seam column per chain picked by load per um (detours allowed when the chain has the hops);
  * a tile carries its core clock as its own port ck (die pin ckt<k>), its face taps, its pins at the parent locations
    and a reset relay (the parent reset reaches every tile through registered seams like any other net).
    python3 subtile.py --json nl/<m>.json --master <m> --rows 3 --cols 2 --out st/ [--report-only]
"""
import argparse, collections, json, os, re, sys
from pathlib import Path

D = Path(__file__).resolve().parent
SEQ = re.compile(r'^\$_(DFF|DFFE|SDFF|SDFFE|SDFFCE)_')
HF_CAP = 1024       # r4: loads per seam bit in the sink tile (textbook_lint hf_port_refuse 2,048; replicas above)
SINK_CAP = int(os.environ.get('VM_ST_SINK_CAP', '13500'))   # clock sinks per tile (owner audit class 1: <= ~15k per tree)
BUDGET = 10.0           # seam bits per um of shared edge (two pin layers; the 13.9 b/um N-S faces failed congestion)


def edge_of(t):
    m = re.match(r'^\$_(?:DFF|DFFE|SDFF|SDFFE|SDFFCE)_([PN])', t)
    return m.group(1) if m else None


def pins_of(io):
    out = {}
    for l in Path(io).read_text().splitlines():
        m = re.search(r'-pin_name \{(\w+)\[(\d+)\]\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+ [\d.]+)\}', l)
        if m:
            out[(m.group(1), int(m.group(2)))] = (m.group(3), float(m.group(4)), float(m.group(5)), m.group(6))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True); ap.add_argument('--master', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--rows', type=int, default=2); ap.add_argument('--cols', type=int, default=3)
    ap.add_argument('--report-only', action='store_true'); ap.add_argument('--core-row', type=int, default=-1)
    ap.add_argument('--vector-net', action='append', default=[], help='keep this net as one vector reg in the core tile (bench force)')
    ap.add_argument('--probe', default='', help='<scope>:<prefix>:<n1,n2,...> bench probe block in the core tile')
    ap.add_argument('--tb-out', default='', help='bench include (vm_st_tb.svh) with VM_CFG / VM_RT / VM_ROOT for the tiled half')
    a = ap.parse_args()
    os.environ['VM_ST'] = str(a.rows); os.environ['VM_ST_COLS'] = str(a.cols)
    os.environ.setdefault('VM_TAPS_LONG', '48'); os.environ.setdefault('VM_TAPS_SHORT', '32')
    sys.path.insert(0, str(D))
    import make_vm_vcut8 as g          # noqa: E402
    m = a.master; q, h = m.split('_')[2], m.split('_')[3]
    rows, cols = g.st_rows(h), g.st_cols(h, q); R, C = len(rows), len(cols)
    tiles = g.st_tiles(h, q)
    def tile_xy(x, y):
        c = next(i for i, (lo, hi) in enumerate(cols) if x < hi or i == C - 1)
        r = next(i for i, (lo, hi) in enumerate(rows) if y < hi or i == R - 1)
        return c * R + r
    cr = lambda k: (k // R, k % R)
    def path(ka, kb, cx=None):
        """tiles from ka to kb, one edge per step, crossing the row seam in column cx (default: the source column; r2:
        cx may lie outside [ca, cb] -- a detour that spreads N-S traffic over every column of the row seam)"""
        (ca, ra), (cb, rb) = cr(ka), cr(kb)
        cx = ca if cx is None else cx
        p = [ka]; c, r = ca, ra
        while c != cx:
            c += 1 if cx > c else -1; p.append(c * R + r)
        while r != rb:
            r += 1 if rb > r else -1; p.append(c * R + r)
        while c != cb:
            c += 1 if cb > c else -1; p.append(c * R + r)
        return p
    mod = json.load(open(a.json))['modules'][m]
    pins = pins_of(D / 'ports' / m / 'io_place.tcl')
    port_of = {}
    for pn, pd in mod['ports'].items():
        for i, b in enumerate(pd['bits']):
            if isinstance(b, int):
                port_of.setdefault(b, (pn, i, pd['direction']))
    clkports = {pn for pn in mod['ports'] if pn == 'ck' or re.fullmatch(r'ck[wensgt]\d+', pn)}
    cells = mod['cells']
    drv, loads = {}, collections.defaultdict(list)
    for cn, c in cells.items():
        for pn, bits in c['connections'].items():
            d = c['port_directions'][pn]
            for k, b in enumerate(bits):
                if isinstance(b, int):
                    if d == 'output':
                        drv[b] = (cn, pn, k)
                    else:
                        loads[b].append((cn, pn, k))
    nm = {}
    for n, nd in sorted(mod['netnames'].items(), key=lambda kv: (kv[1].get('hide_name', 0), len(kv[0]))):
        for i, b in enumerate(nd['bits']):
            if isinstance(b, int) and b not in nm:
                nm[b] = (n, i, len(nd['bits']))
    is_seq = {cn: bool(SEQ.match(c['type'])) for cn, c in cells.items()}
    is_mac = {cn: c['type'].startswith('ot_sram') for cn, c in cells.items()}
    is_fci = {cn: c['type'] == 'ot_fwd_clk_inv' for cn, c in cells.items()}
    comb = lambda cn: not is_seq[cn] and not is_mac[cn] and not is_fci[cn]
    def clockpin(c, pn):
        return (is_seq[c] and pn == 'C') or (is_mac[c] and pn == 'clk') or is_fci[c]
    par = {cn: cn for cn in cells}
    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for b, (cn, pn, _) in drv.items():
        if comb(cn):
            for lc, lp, _ in loads.get(b, []):
                if not clockpin(lc, lp):
                    x, y = f(cn), f(lc)
                    if x != y:
                        par[y] = x
    # r2 FULL-CYCLE SEAMS: every negedge flop joins the unit of its posedge driver(s) (through its D cone), so no cut is
    # ever P -> N; a cut leaving a pure negedge relay ($_DFF_N_ whose D is a posedge flop's Q) carries that posedge Q
    # instead (relay bypass: its posedge loads capture the same value one full cycle after launch).  Every seam is then a
    # posedge -> posedge full-cycle crossing between tile roots: 0 cycles added, no inserted flop, no half-cycle tile IO.
    edge0 = {cn: edge_of(c['type']) for cn, c in cells.items()}
    relay_d, nfunc = {}, []
    for cn, c in cells.items():
        if not (is_seq[cn] and edge0[cn] == 'N'):
            continue
        d = c['connections']['D'][0]
        dv = drv.get(d)
        if c['type'] == '$_DFF_N_' and dv and is_seq[dv[0]] and edge0[dv[0]] == 'P':
            relay_d[cn] = d
            x, y = f(dv[0]), f(cn)
            if x != y:
                par[y] = x
            continue
        nfunc.append(cn)
        todo, seen = [b_ for pn_, bs in c['connections'].items() if c['port_directions'][pn_] == 'input' and pn_ != 'C'
                      for b_ in bs if isinstance(b_, int)], set()
        while todo:
            b_ = todo.pop()
            if b_ in seen or b_ not in drv:
                continue
            seen.add(b_); dc = drv[b_][0]
            x, y = f(dc), f(cn)
            if x != y:
                par[y] = x
            if comb(dc):
                todo += [bb for pn_, bs in cells[dc]['connections'].items() if cells[dc]['port_directions'][pn_] == 'input'
                         for bb in bs if isinstance(bb, int)]
    U = {cn: f(cn) for cn in cells}
    units = collections.defaultdict(list)
    for cn in cells:
        units[U[cn]].append(cn)
    core_re = re.compile(r'^(u_mr|u_slice)\.')
    def qname(cn):
        cx = cells[cn]['connections']
        for pn, bits in cx.items():
            if cells[cn]['port_directions'][pn] == 'output' and bits and isinstance(bits[0], int) and bits[0] in nm:
                return nm[bits[0]][0]
        return cn
    has_mac = any(is_mac.values())
    # core (slice / root) in the middle column; row: the slice macros' row (0), else the row holding more pin bits
    pr = collections.Counter(tile_xy(p_[1], p_[2]) % R for (pn_, _), p_ in pins.items() if not re.fullmatch(r'ck\w*|rst', pn_))
    core_k = (C // 2) * R + (a.core_row if a.core_row >= 0 else (0 if has_mac else max(range(R), key=lambda r: pr.get(r, 0))))
    anchor, conflict = {}, []
    def set_anchor(un, k, why):
        if un in anchor and anchor[un][0] != k:
            conflict.append((qname(un), anchor[un][1], why)); return
        anchor.setdefault(un, (k, why))
    core_src = re.compile(r'ot_hfd_vm_slice\.sv|ot_hfd_vm_root_x\.sv|ot_sram')
    # r10 (VM_ST_CORE_SEQ='<q>_<h>,...', opt-in): a unit anchors in the core only through a core FLOP or macro, not through
    # core combinational cells.  r9 sw_e: the root's output decode (seat_data -> tap_data, 4 copies) is merged with the
    # ~9.7k output-chain flops it drives (a logic cluster joins the flops it drives), and its root src attribute pulled
    # all of them into the core tile (20.5k core-anchored sinks, 25.7k in the tile).  Those units read root flops only, so
    # they may sit one tile edge away (flop -> seam -> decode -> flop, full cycle; same cycles); SINK_CAP then spreads them.
    core_seq = f'{q}_{h}' in os.environ.get('VM_ST_CORE_SEQ', '').replace(' ', '').split(',')
    for cn in cells:
        if is_mac[cn] or (core_src.search(str(cells[cn].get('attributes', {}).get('src', ''))) and (not core_seq or is_seq[cn])):
            set_anchor(U[cn], core_k, 'core')
    # r10 (VM_ST_CLUSTER_TILE='<q>_<h>:<c>/<r>', opt-in): the large logic clusters that hold no root / slice cell (e.g.
    # the root's seat_data decode merged with the 4k output-chain flops it drives) anchor in that tile, edge-adjacent to
    # the core, instead of the core: r9 sw_e core tile 25.7k clock sinks (root_x 10.8k + 9.5k of such chain flops + half
    # glue) against the <= 15k per-tree rule.  The decode reads root flops only, so the core -> cluster seam is a flop ->
    # logic -> flop full cycle like every other seam (same cycles).
    # 'free' instead of '<c>/<r>': such clusters are not anchored at all; they are placed like every other unit, between
    # their upstream / downstream anchors under SINK_CAP (r10 sw_e: the per-tap decode copies of ODUP head W-bound and
    # E-bound output chains, so one shared tile would be wrong for half of them).
    ctile, cfree = None, False
    for kv in os.environ.get('VM_ST_CLUSTER_TILE', '').replace(' ', '').split(','):
        if kv == f'{q}_{h}:free':
            cfree = True
        elif kv.startswith(f'{q}_{h}:'):
            cc_, rr_ = (int(x) for x in kv.split(':')[1].split('/'))
            ctile = cc_ * R + rr_
            assert sum(abs(x - y) for x, y in zip(cr(ctile), cr(core_k))) == 1, ('cluster tile not adjacent to core', kv)
    for un, cs in units.items():
        if len(cs) > 64 and sum(comb(x) for x in cs) > 32 and not (cfree and un not in anchor):
            set_anchor(un, ctile if (ctile is not None and un not in anchor) else core_k, 'logic cluster')
    vecbits = {}
    for vn in a.vector_net:
        for i, b in enumerate(mod['netnames'][vn]['bits']):
            vecbits[b] = (vn, i)
            if b in drv:
                set_anchor(U[drv[b][0]], core_k, f'vector {vn}')
    def pin_k(pn, i):
        p = pins[(pn, i)]
        return tile_xy(p[1], p[2])
    for b, (pn, i, d) in port_of.items():
        if pn in clkports:
            continue
        if d == 'input':
            for lc, lp, _ in loads.get(b, []):
                set_anchor(U[lc], pin_k(pn, i), f'in {pn}[{i}]')
        elif b in drv:
            set_anchor(U[drv[b][0]], pin_k(pn, i), f'out {pn}[{i}]')
    succ, pred = collections.defaultdict(set), collections.defaultdict(set)
    for b, (cn, pn, _) in drv.items():
        if comb(cn) or is_fci[cn]:
            continue
        for lc, lp, _ in loads.get(b, []):
            if not clockpin(lc, lp) and U[lc] != U[cn]:
                succ[U[cn]].add(U[lc]); pred[U[lc]].add(U[cn])
    def bfs(adjm):
        dist, at, org = {}, {}, {}
        dq = collections.deque()
        for un, (k, _) in anchor.items():
            dist[un], at[un], org[un] = 0, k, un; dq.append(un)
        while dq:
            x = dq.popleft()
            for y in adjm[x]:
                if y not in dist:
                    dist[y], at[y], org[y] = dist[x] + 1, at[x], org[x]; dq.append(y)
        return dist, at, org
    db, kb, ob = bfs(succ); df, kf, of_ = bfs(pred)
    NT_ = len(tiles); ALL = (1 << NT_) - 1
    nb_ = [0] * NT_
    for k in range(NT_):
        for j in range(NT_):
            if sum(abs(x - y) for x, y in zip(cr(k), cr(j))) <= 1:
                nb_[k] |= 1 << j
    def grow(mask):
        o = 0
        for k in range(NT_):
            if mask >> k & 1:
                o |= nb_[k]
        return o
    # feasible tiles: every downstream / upstream anchor reachable at one tile edge per flop hop (bitmask fixpoint)
    def fix(adjm):
        fe = {un: (1 << anchor[un][0]) if un in anchor else ALL for un in units}
        order = sorted((un for un in units if un not in anchor), key=lambda un: -(db.get(un, 0)))
        for _ in range(64):
            ch = 0
            for un in order:
                v = ALL
                for y in adjm[un]:
                    v &= grow(fe[y])
                v &= fe[un]
                if v != fe[un]:
                    fe[un] = v; ch += 1
            if not ch:
                break
        return fe
    fd, fu = fix(succ), fix(pred)
    tile = {un: anchor[un][0] for un in anchor}
    infeas = 0; dbg = []
    nseq = {un: sum(1 for x in cs if is_seq[x] or is_mac[x]) for un, cs in units.items()}
    load_t = [0] * NT_
    for un in anchor:
        load_t[tile[un]] += nseq[un]
    # r2: the row seam column of a chain (its upstream / downstream anchor pair) is picked once, least loaded per um of
    # column width among the columns the chain spans (r1: a per-unit hash put 2/3 of the N-S traffic through the core
    # column: 22-57 b/um on its 116 um row seam)
    xload, xpick, xalt = [0.0] * C, {}, collections.Counter()
    # r9 (VM_ST_XBAL='<q>_<h>,...'): the r2 pick above is greedy in unit order and counts CHAINS, not seam BITS, so the
    # chains that can only cross in the core column arrive after the flexible ones have already filled it (r7 sw_e:
    # col 1 row seam 4,453 bits / 129.6 um = 12.1 b/um/layer on M3/M5/M7, col 2 1,443 / 91.56 um).  Here every chain
    # is pre-assigned before placement: its weight is its widest depth level (= the seam bits it puts on the row
    # seam), forced chains (one feasible column) load their column first, then flexible chains in descending weight
    # take the column with the least bits per um after adding them.  Same feasibility rule, same cycles; only the
    # crossing column of a flexible chain changes.
    if f'{q}_{h}' in os.environ.get('VM_ST_XBAL', '').replace(' ', '').split(','):
        kinfo, kw_ = {}, collections.defaultdict(collections.Counter)
        for un in units:
            if un in anchor or un not in db or un not in df:
                continue
            key = (ob[un], of_[un])
            kw_[key][db[un]] += 1
            if key not in kinfo:
                (ca, ra), (cb, rb) = cr(kb[un]), cr(kf[un])
                if ra == rb:
                    kinfo[key] = None
                else:
                    hops = db[un] + df[un]
                    kinfo[key] = ([c_ for c_ in range(C) if abs(ca - c_) + abs(c_ - cb) + abs(ra - rb) <= hops] or [ca], ca, cb)
        wid = lambda c_: cols[c_][1] - cols[c_][0]
        # row-seam bits that do NOT come from a chain pick (core-tile logic, one-sided units, anchor neighbours) per
        # column, measured on a previous run of the same half (report seam_bits u/d minus row_cross_chains):
        # VM_ST_XBAL_SEED='<q>_<h>:<c0>/<c1>/<c2>'.  The chain pass then balances the TOTAL row-seam bits per um.
        for kv in os.environ.get('VM_ST_XBAL_SEED', '').replace(' ', '').split(','):
            if kv.startswith(f'{q}_{h}:'):
                for c_, v_ in enumerate(kv.split(':')[1].split('/')):
                    xload[c_] += float(v_)
        ks_ = sorted((k_ for k_, v_ in kinfo.items() if v_ is not None),
                     key=lambda k_: (len(kinfo[k_][0]) > 1, -max(kw_[k_].values()), str(k_)))
        for k_ in ks_:
            cs, ca, cb = kinfo[k_]; w_ = max(kw_[k_].values())
            xalt[len(cs) > 1] += 1
            cx = min(cs, key=lambda c_: ((xload[c_] + w_) / wid(c_), abs(ca - c_) + abs(c_ - cb)))
            xload[cx] += w_; xpick[k_] = cx
        for k_, v_ in kinfo.items():
            if v_ is None:
                xpick[k_] = None
    def target(un):
        if un in db and un in df:
            key = (ob[un], of_[un])
            if key not in xpick:
                (ca, ra), (cb, rb) = cr(kb[un]), cr(kf[un])
                hops = db[un] + df[un]
                if ra != rb:     # any column whose detour fits the chain's hops (|ca-cx| + |cx-cb| + |ra-rb| tile edges)
                    cs = [c_ for c_ in range(C) if abs(ca - c_) + abs(c_ - cb) + abs(ra - rb) <= hops] or [ca]
                    xalt[len(cs) > 1] += 1
                    cx = min(cs, key=lambda c_: ((xload[c_] + 1) / (cols[c_][1] - cols[c_][0]), abs(ca - c_) + abs(c_ - cb)))
                    xload[cx] += 1
                else:
                    cx = None
                xpick[key] = cx
            cx = xpick[key]
            p = path(kb[un], kf[un], cx)
            return p[int(round((len(p) - 1) * db[un] / (db[un] + df[un])))]
        return kb.get(un, kf.get(un, core_k))
    # r10 (VM_ST_FFIRST='<q>_<h>,...'): units with ONE feasible tile are placed before every flexible unit, so the flexible
    # ones see the true load of the core tile (r10 sw_e scan: flexible units filled the core to the cap first, then 2-4k
    # forced chain flops pushed it to 17.7k).  Same feasibility, same cycles; only who yields to the cap changes.
    ffirst = f'{q}_{h}' in os.environ.get('VM_ST_FFIRST', '').replace(' ', '').split(',')
    def porder(u_):
        return ((bin(fd[u_] & fu[u_]).count('1') > 1) if ffirst else 0, db.get(u_, 10 ** 6), u_)
    for un in sorted((u_ for u_ in units if u_ not in anchor), key=porder):
        cand = fd[un] & fu[un]
        for y in list(pred[un]) + list(succ[un]):
            if y in tile:
                c2 = cand & nb_[tile[y]]
                if c2:
                    cand = c2
        if not cand:
            infeas += 1
            if len(dbg) < 3:
                dbg.append(dict(u=qname(un), n=len(units[un]), fd=bin(fd[un]), fu=bin(fu[un]),
                                pred=[(qname(y), tile.get(y), bin(fd[y] & fu[y])) for y in list(pred[un])[:3]],
                                succ=[(qname(y), tile.get(y), anchor.get(y, ('', ''))[1]) for y in list(succ[un])[:4]]))
            cand = fd[un] or fu[un] or ALL
        t0 = target(un)
        tile[un] = min((k for k in range(NT_) if cand >> k & 1),
                       key=lambda k: (load_t[k] + nseq[un] > SINK_CAP, sum(abs(x - y) for x, y in zip(cr(k), cr(t0))), load_t[k]))
        load_t[tile[un]] += nseq[un]
    adj = lambda ka, kb_: sum(abs(x - y) for x, y in zip(cr(ka), cr(kb_))) <= 1
    edge_cell = {cn: edge_of(c['type']) for cn, c in cells.items()}
    def sink_edges(lc):
        if is_seq[lc]:
            return {edge_cell[lc]}
        if is_mac[lc]:
            return {'P'}
        es, todo, seen = set(), [lc], set()
        while todo:
            x = todo.pop()
            if x in seen:
                continue
            seen.add(x)
            for pn, bits in cells[x]['connections'].items():
                if cells[x]['port_directions'][pn] != 'output':
                    continue
                for b in bits:
                    if not isinstance(b, int):
                        continue
                    if b in port_of:
                        es.add('O')
                    for y, yp, _ in loads.get(b, []):
                        if clockpin(y, yp):
                            continue
                        if is_seq[y]:
                            es.add(edge_cell[y])
                        elif is_mac[y]:
                            es.add('P')
                        else:
                            todo.append(y)
        return es
    viol, mixed, cuts = [], [], []
    vcls = collections.Counter()
    halfcut, relayed = [], 0
    cutd = collections.OrderedDict()
    for b, (cn, pn, _) in drv.items():
        if comb(cn) or is_fci[cn]:
            continue
        ks = tile[U[cn]]
        grp = collections.defaultdict(list)
        for lc, lp, k in loads.get(b, []):
            if clockpin(lc, lp):
                continue
            kd = tile[U[lc]]
            if kd == ks:
                continue
            if not adj(ks, kd):
                wk = lambda un: (anchor[un][1].split()[0] + (' ' + anchor[un][1].split()[1].split('[')[0] if ' ' in anchor[un][1] else '')) if un in anchor else 'free'
                dist_ = sum(abs(x - y) for x, y in zip(cr(ks), cr(kd)))
                viol.append((nm.get(b, (str(b),))[0], cr(ks), cr(kd)))
                vcls[(wk(U[cn]), edge_cell.get(cn) or 'M', wk(U[lc]), ''.join(sorted(sink_edges(lc))), dist_)] += 1
                continue
            se = edge_cell.get(cn) or 'P'
            es = sink_edges(lc) - {'O'}
            if len(es) > 1:
                mixed.append((nm.get(b, (str(b),))[0], sorted(es))); continue
            if (se == 'N' and cn not in relay_d) or 'N' in es:
                halfcut.append((qname(cn), se, sorted(es))); continue
            grp[kd].append((lc, lp, k))
        for kd, ls in grp.items():
            sc, sb = (drv[relay_d[cn]][0], relay_d[cn]) if cn in relay_d else (cn, b)
            relayed += cn in relay_d
            ck = cells[sc]['connections']['C'][0] if is_seq[sc] else cells[sc]['connections']['clk'][0]
            cutd.setdefault((sb, kd), (sb, ks, kd, False, ck, 'P', []))[6].extend(ls)
    cuts = list(cutd.values())
    # r4 [vm8] 2026-10-11 (textbook_lint high_fanout REFUSE swet2 @f0104f2ac: seam e0_0[2216] = the reset relay rst_c,
    # 5,531 async-reset loads behind ONE tile pin): a cut whose sink tile has > HF_CAP loads is split into kept REPLICAS of
    # its posedge source flop in the source tile, one seam bit each, <= HF_CAP loads per bit (grouped by cell name so a
    # copy serves one logical region; the placer co-locates each copy's sinks).  Same D / clock / reset as the source:
    # cycle-identical, 0 cycles added, no new register stage.
    hfsplit = []
    for i_, (sb, ks, kd, ins, ck, se, ls) in enumerate(list(cuts)):
        if len(ls) <= HF_CAP or ins:
            continue
        sc = drv[sb][0]
        if not is_seq[sc] or tile[U[sc]] != ks:
            raise SystemExit(f'high-fanout cut {nm.get(sb, (sb,))[0]} ({len(ls)} loads) not driven by a flop in its source tile')
        ls = sorted(ls, key=lambda x: (str(x[0]), str(x[1]), x[2]))
        n_ = -(-len(ls) // HF_CAP); per = -(-len(ls) // n_)
        cuts[i_] = (sb, ks, kd, ins, ck, se, ls[:per])
        for j in range(1, n_):
            cuts.append((('HF', sb, j, sc), ks, kd, ins, ck, se, ls[j * per:(j + 1) * per]))
        hfsplit.append((nm.get(sb, (str(sb),))[0], cr(ks), cr(kd), len(ls), n_))
    # r2: violations / infeasible units by the output port anchor downstream of them -> make_vm_vcut8 VM_ST_K (+1 full
    # stage on every bit of that port per round)
    def out_anchor(un):
        o = of_.get(un)
        w_ = anchor.get(o, (0, ''))[1] if o is not None else ''
        return w_.split()[1].split('[')[0] if w_.startswith('out ') else ('?' + w_.split(' ')[0])
    kdem = collections.Counter()
    for b, (cn, pn, _) in drv.items():
        if comb(cn) or is_fci[cn]:
            continue
        for lc, lp, _ in loads.get(b, []):
            if not clockpin(lc, lp) and not adj(tile[U[cn]], tile[U[lc]]):
                kdem[out_anchor(U[lc])] += 1
    for un in units:
        if un not in anchor and un in fd and not (fd[un] & fu[un]):
            kdem[out_anchor(un)] += 1
    tapuse = collections.defaultdict(set)
    for cn, c in cells.items():
        for pn_, bits in c['connections'].items():
            if clockpin(cn, pn_) and bits and isinstance(bits[0], int) and bits[0] in port_of:
                tp = port_of[bits[0]][0]
                if tp != 'ck' and tp in clkports:
                    tapuse[tp].add(tile[U[cn]])
    tapx = {t: sorted(cr(x) for x in v) for t, v in tapuse.items() if len(v) > 1 or pin_k(t, 0) not in v}
    def seam_of(ks, kd):
        (c1, r1), (c2, r2) = cr(ks), cr(kd)
        if c1 == c2:
            return f'u{c1}_{min(r1, r2)}' if r2 > r1 else f'd{c1}_{min(r1, r2)}'
        return f'e{r1}_{min(c1, c2)}' if c2 > c1 else f'w{r1}_{min(c1, c2)}'
    seamn = collections.Counter(seam_of(ks, kd) for _, ks, kd, *_ in cuts)
    def seam_len(s):
        a_ = int(s[1:].split('_')[0])
        return (cols[a_][1] - cols[a_][0]) if s[0] in 'ud' else (rows[a_][1] - rows[a_][0])
    load = {}
    for s in seamn:
        pair = s[0].translate(str.maketrans('udew', 'duwe')) + s[1:]
        load[s] = round((seamn[s] + seamn.get(pair, 0)) / (seam_len(s) - 6.0), 2)
    over = {s: v for s, v in load.items() if v > BUDGET}
    sinks = collections.Counter(tile[U[cn]] for cn in cells if is_seq[cn] or is_mac[cn])
    srcmix = collections.Counter((cr(tile[U[cn]]), re.sub(r':.*', '', str(cells[cn].get('attributes', {}).get('src', '?')).split('/')[-1]))
                                 for cn in cells if is_seq[cn])
    seam_sinks = collections.Counter(ks for _, ks, kd, ins, *_ in cuts if ins)
    anc_sinks = collections.Counter()
    for un_, (k_, why_) in anchor.items():
        anc_sinks[f'{cr(k_)} {why_.split()[0]}'] += nseq[un_]
    core_units = []
    for un_ in sorted((u_ for u_, (k_, w_) in anchor.items() if k_ == core_k), key=lambda u_: -nseq[u_])[:6]:
        sc_ = collections.Counter(os.path.basename(str(cells[x].get('attributes', {}).get('src', '?')).split(':')[0])
                                  for x in units[un_] if is_seq[x])
        core_units.append(dict(nseq=nseq[un_], cells=len(units[un_]), src=dict(sc_), why=anchor[un_][1],
                               ex=sorted({re.sub(r'\[\d+\]', '', qname(x)) for x in units[un_] if is_seq[x]})[:12]))
    core_free = collections.Counter()
    for un_, k_ in tile.items():
        if k_ == core_k and un_ not in anchor:
            core_free[re.sub(r'\d+', '#', re.sub(r'\[\d+\]', '', qname(un_)))[:60] + f' cand={bin(fd[un_] & fu[un_]).count("1")}'] += nseq[un_]
    rep = dict(core_free=dict(core_free.most_common(14)), core_units=core_units, anchor_sinks=dict(anc_sinks.most_common(12)), master=m, grid=f'{C}x{R}', cols=cols, rows=rows, core_tile=cr(core_k), cells=len(cells), units=len(units),
               anchored=len(anchor), conflicts=len(conflict), infeasible=infeas, infeasible_ex=dbg, conflict_ex=[str(x)[:160] for x in conflict[:4]],
               k_demand=dict(kdem.most_common()), row_cross_chains=[xload, dict(xalt)], violations=len(viol), viol_ex=viol[:4], viol_classes={' | '.join(map(str, k_)): v_ for k_, v_ in vcls.most_common(12)}, mixed=len(mixed), mixed_ex=mixed[:4], cuts=len(cuts),
               inserted=sum(1 for c in cuts if c[3]), relays=len(relay_d), relay_cuts=relayed, neg_functional=len(nfunc),
               hf_split=hfsplit, half_cycle_cuts=len(halfcut), half_cycle_ex=[str(x)[:120] for x in halfcut[:4]], seam_bits=dict(sorted(seamn.items())),
               seam_b_per_um=dict(sorted(load.items())), over_budget=over,
               sinks_per_tile={str(cr(k)): v + seam_sinks.get(k, 0) for k, v in sorted(sinks.items())},
               sink_src={str(k_): v_ for k_, v_ in srcmix.most_common(10)}, tap_split=len(tapx), tap_split_ex=dict(list(tapx.items())[:4]))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / f'{m}_st_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep))
    bad = conflict or viol or mixed or halfcut
    if a.report_only or bad:
        sys.exit(2 if bad else 0)
    # r5 [vm8] 2026-10-11 (hbm_vm8st3_swwt5 @9a98b69aa EARLY_FAIL_CONGESTION, GRT markers stuck at 10,000, vertical overflow
    # in a y 160-280 band across the whole 89.9 um column at 14% utilisation): seam bits were slotted in cut order, so the
    # e2w feed-through bits left t5 on its W seam in REVERSED y order w.r.t. their fixed E-face pins (corr -0.89, mean
    # |dy| 231 um over a 482 um tile): every bit crossed the tile centre vertically.  VM_ST_SEAM_ORDER='<q>_<h>,...': the
    # bits of every seam of that half are slotted by the along-edge coordinate of the bit's straight line between its
    # upstream and downstream port anchors (interpolated at the seam), so a seam pin sits where the wire passes anyway.
    # Pin slots, seam widths, layers and the RTL are unchanged; only which bit takes which slot.
    # 'sw_w' orders every seam of the half; 'sw_w:w1_1+u2_0' only the named seams (the other tiles stay byte-identical).
    so_ = {}
    for kv in os.environ.get('VM_ST_SEAM_ORDER', '').replace(' ', '').split(','):
        if kv:
            so_[kv.split(':')[0]] = set(kv.split(':')[1].split('+')) if ':' in kv else None
    if f'{q}_{h}' in so_:
        so_s = so_[f'{q}_{h}']
        def pin_at(un):
            mm_ = re.fullmatch(r'(?:in|out) (\w+)\[(\d+)\]', anchor.get(un, (0, ''))[1]) if un is not None else None
            p_ = pins.get((mm_.group(1), int(mm_.group(2)))) if mm_ else None
            return (p_[1], p_[2]) if p_ else None
        def seam_key(c_):
            sb_, ks_, kd_, *_r, ls_ = c_
            s_ = seam_of(ks_, kd_)
            a_ = int(s_[1:].split('_')[1])   # e/w: column boundary, u/d: row boundary
            sc_ = sb_[3] if isinstance(sb_, tuple) else drv[sb_][0]
            us_, ud_ = U[sc_], (U[ls_[0][0]] if ls_ else None)
            pu, pd = pin_at(ob.get(us_)), pin_at(of_.get(ud_) if ud_ is not None else None)
            ax = 1 if s_[0] in 'ew' else 0          # E/W seams run along y, N/S seams along x
            at = cols[a_][1] if s_[0] in 'ew' else rows[a_][1]
            if pu and pd:
                if abs(pd[1 - ax] - pu[1 - ax]) > 1e-6:
                    t_ = min(1.0, max(0.0, (at - pu[1 - ax]) / (pd[1 - ax] - pu[1 - ax])))
                else:
                    t_ = 0.5
                return (s_, pu[ax] + t_ * (pd[ax] - pu[ax]))
            if pu or pd:
                return (s_, (pu or pd)[ax])
            lo_, hi_ = (rows[int(s_[1:].split('_')[0])] if s_[0] in 'ew' else cols[int(s_[1:].split('_')[0])])
            return (s_, (lo_ + hi_) / 2)
        # reorder only within the selected seams, in place: every other cut keeps its position (other tiles byte-identical)
        sel_ = [i_ for i_, c_ in enumerate(cuts) if seam_key(c_)[1] is not None and (so_s is None or
                seam_of(c_[1], c_[2]) in so_s or (seam_of(c_[1], c_[2])[0].translate(str.maketrans('udew', 'duwe')) +
                                                  seam_of(c_[1], c_[2])[1:]) in so_s)]
        bys_ = collections.defaultdict(list)
        for i_ in sel_:
            bys_[seam_of(cuts[i_][1], cuts[i_][2])].append(i_)
        new_ = list(cuts)
        for s_, ix_ in bys_.items():
            for i_, c_ in zip(ix_, sorted((cuts[i_] for i_ in ix_), key=seam_key)):
                new_[i_] = c_
        cuts = new_
    emit(g, out, m, h, mod, cells, rows, tiles, cr, tile, U, cuts, seam_of, port_of, pins, nm, drv, clkports,
         is_seq, is_mac, core_k, vecbits, a, loads)


FLOP_TPL = {
    '$_DFF_P_': 'always @(posedge {C}) {Q} <= {D};', '$_DFF_N_': 'always @(negedge {C}) {Q} <= {D};',
    '$_DFF_PP0_': "always @(posedge {C} or posedge {R}) if ({R}) {Q} <= 1'b0; else {Q} <= {D};",
    '$_DFF_PP1_': "always @(posedge {C} or posedge {R}) if ({R}) {Q} <= 1'b1; else {Q} <= {D};",
    '$_DFF_PN0_': "always @(posedge {C} or negedge {R}) if (!{R}) {Q} <= 1'b0; else {Q} <= {D};",
    '$_DFF_PN1_': "always @(posedge {C} or negedge {R}) if (!{R}) {Q} <= 1'b1; else {Q} <= {D};",
    '$_DFFE_PP_': 'always @(posedge {C}) if ({E}) {Q} <= {D};', '$_DFFE_PN_': 'always @(posedge {C}) if (!{E}) {Q} <= {D};',
    '$_DFFE_PP0P_': "always @(posedge {C} or posedge {R}) if ({R}) {Q} <= 1'b0; else if ({E}) {Q} <= {D};",
    '$_DFFE_PP0N_': "always @(posedge {C} or posedge {R}) if ({R}) {Q} <= 1'b0; else if (!{E}) {Q} <= {D};",
    '$_DFFE_PN0P_': "always @(posedge {C} or negedge {R}) if (!{R}) {Q} <= 1'b0; else if ({E}) {Q} <= {D};",
    '$_DFFE_PN0N_': "always @(posedge {C} or negedge {R}) if (!{R}) {Q} <= 1'b0; else if (!{E}) {Q} <= {D};",
    '$_DFFE_PP1P_': "always @(posedge {C} or posedge {R}) if ({R}) {Q} <= 1'b1; else if ({E}) {Q} <= {D};",
}
COMB_TPL = {'$_AND_': '{A} & {B}', '$_OR_': '{A} | {B}', '$_XOR_': '{A} ^ {B}', '$_XNOR_': '~({A} ^ {B})',
            '$_NAND_': '~({A} & {B})', '$_NOR_': '~({A} | {B})', '$_NOT_': '~{A}', '$_BUF_': '{A}',
            '$_MUX_': '{S} ? {B} : {A}', '$_ANDNOT_': '{A} & ~{B}', '$_ORNOT_': '{A} | ~{B}'}


def emit(g, out, m, h, mod, cells, rows, tiles, cr, tile, U, cuts, seam_of, port_of, pins, nm, drv, clkports,
         is_seq, is_mac, core_k, vecbits, a, loads):
    """per-tile Verilog (generic cells; flops (* keep *)), the parent shell, per-tile pins / views / sdc / macros"""
    NT, R = len(tiles), len(rows)
    used, wname = set(), {}
    def wn(b):
        if b in wname:
            return wname[b]
        if b in vecbits:
            wname[b] = f'{vecbits[b][0]}[{vecbits[b][1]}]'
            return wname[b]
        base = (f'{nm[b][0]}_{nm[b][1]}' if nm[b][2] > 1 else nm[b][0]) if b in nm else f'n{b}'
        base = re.sub(r'_+', '_', re.sub(r'[^0-9A-Za-z_]', '_', base)).strip('_') or f'n{b}'
        if base[0].isdigit():
            base = 'n' + base
        n, k = base, 1
        while n in used:
            k += 1; n = f'{base}_{k}'
        used.add(n); wname[b] = n
        return n
    tk = {cn: tile[U[cn]] for cn in cells}
    ports_t = {k: set() for k in range(NT)}
    portbits_t = {k: collections.defaultdict(dict) for k in range(NT)}
    def tport(k, pn, i):
        mp = portbits_t[k][pn]
        if i not in mp:
            mp[i] = len(mp)
        return f'{pn}__t[{mp[i]}]'
    decl = {k: set() for k in range(NT)}
    subst, seams = {}, collections.defaultdict(list)
    for b, ks, kd, ins, ck, se, ls in cuts:
        s = seam_of(ks, kd); idx = len(seams[s]); seams[s].append((b, ks, kd, ins, ck, se))
        for lc, lp, kk in ls:
            subst[(lc, lp, kk)] = f'{s}[{idx}]'
    def src(k, b, cell=None, pin=None, kk=None):
        if cell is not None and (cell, pin, kk) in subst:
            return subst[(cell, pin, kk)]
        if not isinstance(b, int):
            return {'0': "1'b0", '1': "1'b1"}.get(b, "1'b0")
        if b in port_of and b in drv:
            decl[k].add(wn(b)); return wn(b)
        if b in port_of:
            pn, i, d = port_of[b]
            if pn == 'ck' or pn.startswith('ckt'):
                return 'ck[0]'
            if pn in clkports:
                tp_ = pins[(pn, 0)]
                if not (tiles[k][0] <= tp_[1] <= tiles[k][1] and tiles[k][2] <= tp_[2] <= tiles[k][3]):
                    return 'ck[0]'      # a face tap of another tile: this tile's own root (same die clock, same REF)
                ports_t[k].add(pn); return f'{pn}[0]'
            return tport(k, pn, i)
        decl[k].add(wn(b)); return wn(b)
    L = {k: [] for k in range(NT)}
    regs = {k: set() for k in range(NT)}
    mac_inst = {}
    for cn, c in cells.items():
        k = tk[cn]; t = c['type']; cx = c['connections']
        if is_seq[cn]:
            if t not in FLOP_TPL:
                raise SystemExit(f'unsupported flop {t}')
            qb = cx['Q'][0]
            qn = wn(qb); regs[k].add(qn)        # a flop driving an output port bit: the tile port is assigned from it
            L[k].append('(* keep *) ' + FLOP_TPL[t].format(Q=qn, **{p: src(k, cx[p][0], cn, p, 0) for p in cx if p != 'Q'}))
        elif t in COMB_TPL:
            yb = cx['Y'][0]
            decl[k].add(wn(yb))
            L[k].append(f'assign {wn(yb)} = {COMB_TPL[t].format(**{p: src(k, cx[p][0], cn, p, 0) for p in cx if p != "Y"})};')
        else:
            conns = []
            for p, bits in cx.items():
                if c['port_directions'][p] == 'output':
                    for b in bits:
                        if isinstance(b, int):
                            decl[k].add(wn(b))
                    conns.append(f'.{p}({{{", ".join(wn(b) if isinstance(b, int) else "" for b in reversed(bits))}}})')
                else:
                    conns.append(f'.{p}({{{", ".join(src(k, b, cn, p, kk) for kk, b in reversed(list(enumerate(bits))))}}})')
            iname = 'u_' + re.sub(r'_+', '_', re.sub(r'[^0-9A-Za-z_]', '_', cn)).strip('_')
            if is_mac[cn]:
                mac_inst[cn] = iname
            L[k].append(f'{t} {iname} ({", ".join(conns)});')
    for pn, pd in mod['ports'].items():
        if pd['direction'] != 'output':
            continue
        for i, b in enumerate(pd['bits']):
            if isinstance(b, int) and b in drv:
                k = tk[drv[b][0]]
                L[k].append(f'assign {tport(k, pn, i)} = {wn(b)};')
                decl[k].add(wn(b))
            else:
                p = pins[(pn, i)]
                k = next(kk for kk, (x0, x1, y0, y1) in enumerate(tiles) if x0 <= p[1] <= x1 and y0 <= p[2] <= y1)
                L[k].append(f'assign {tport(k, pn, i)} = {src(k, b)};')
    sw = {}
    for s, lst in seams.items():
        sw[s] = len(lst)
        for idx, (b, ks, kd, ins, ck, se) in enumerate(lst):
            if isinstance(b, tuple):        # r4 high-fanout replica: a kept copy of the source flop, one seam bit per copy
                _, sb, j, sc = b; c = cells[sc]; cx = c['connections']
                v = f'{wn(sb)}_hf{j}'; regs[ks].add(v)
                L[ks].append('(* keep *) ' + FLOP_TPL[c['type']].format(Q=v, **{p: src(ks, cx[p][0], sc, p, 0) for p in cx if p != 'Q'}))
                L[ks].append(f'assign {s}_o[{idx}] = {v};')
                continue
            v = src(ks, b)
            if ins:
                r_ = f'{s}_r{idx}'
                L[ks].append(f"(* keep *) reg {r_}; always @({'negedge' if se == 'P' else 'posedge'} {src(ks, ck)}) {r_} <= {v};")
                v = r_
            L[ks].append(f'assign {s}_o[{idx}] = {v};')
    def seam_tiles(s):
        a_, b_ = (int(x) for x in s[1:].split('_'))
        lo, hi = (a_ * R + b_, a_ * R + b_ + 1) if s[0] in 'ud' else (b_ * R + a_, (b_ + 1) * R + a_)
        return (lo, hi) if s[0] in 'ue' else (hi, lo)          # (source tile, sink tile)
    def core_view(b):
        if not isinstance(b, int):
            return {'0': "1'b0", '1': "1'b1"}.get(b, "1'b0")
        for lc, lp, kk in loads.get(b, []):
            if tk[lc] == core_k and (lc, lp, kk) in subst:
                return subst[(lc, lp, kk)]
        if b in drv and tk[drv[b][0]] == core_k:
            return wn(b)
        if b in port_of:
            return src(core_k, b)
        raise SystemExit(f'probe bit {b} not visible in the core tile')
    texts = {}
    for k in range(NT):
        ps = [('input', 'ck', 1)] + [('input', pn, 1) for pn in sorted(ports_t[k])]
        ps += [(mod['ports'][pn]['direction'], f'{pn}__t', len(mp)) for pn, mp in portbits_t[k].items()]
        for s, w in sorted(sw.items()):
            so, si = seam_tiles(s)
            if so == k:
                ps.append(('output', f'{s}_o', w))
            if si == k:
                ps.append(('input', s, w))
        x0, x1, y0, y1 = tiles[k]
        body = [f'// GENERATED by vm/vcut8/subtile.py from {m}: hardened tile {cr(k)} x {x0:.3f}..{x1:.3f} y {y0:.3f}..{y1:.3f} um',
                f'module {m}_t{k} (', ',\n'.join(f'    {d} wire [{w-1}:0] {n}' for d, n, w in ps), ');']
        vec_here = {vn for (vn, _) in vecbits.values()} if k == core_k else set()
        for vn in sorted(vec_here):
            body.append(f"reg [{len(mod['netnames'][vn]['bits']) - 1}:0] {vn};")
        decl[k] = {x for x in decl[k] if not re.fullmatch(r'\w+\[\d+\]', x)}
        regs[k] = {x for x in regs[k] if not re.fullmatch(r'\w+\[\d+\]', x)}
        if k == core_k and a.probe:
            scope, pre, names = a.probe.split(':')
            body.append(f'if (1) begin : {scope}   // bench probes: the values the {pre.rstrip(".")} cells see in this tile')
            for n_ in names.split(','):
                bits = mod['netnames'][pre + n_]['bits']
                el = [core_view(b) for b in reversed(bits)]
                body.append(f'    wire [{len(bits) - 1}:0] {n_} = {{' + ', '.join(el) + '};')
            body.append('end')
        dw = sorted(decl[k] - regs[k])
        body += ['wire ' + ', '.join(dw[i:i + 32]) + ';' for i in range(0, len(dw), 32)]
        rg = sorted(regs[k])
        body += ['reg ' + ', '.join(rg[i:i + 32]) + ';' for i in range(0, len(rg), 32)]
        body += L[k] + ['endmodule', '']
        (out / f'{m}_t{k}.v').write_text('\n'.join(body))
        texts[k] = ps
    pp = [(pd['direction'], pn, len(pd['bits'])) for pn, pd in mod['ports'].items()]
    body = [f'// GENERATED by vm/vcut8/subtile.py: {m} as {NT} hardened tiles (abutted; zero logic)',
            f'module {m} (', ',\n'.join(f'    {d} wire [{w-1}:0] {n}' for d, n, w in pp), ');']
    body += [f'wire [{w-1}:0] {s};' for s, w in sorted(sw.items())]
    for k in range(NT):
        cs = [f'.ck(ckt{k})'] + [f'.{pn}({pn})' for pn in sorted(ports_t[k])]
        for pn, mp in portbits_t[k].items():
            el = [f'{pn}[{i}]' for i, _ in sorted(mp.items(), key=lambda kv: -kv[1])]
            cs.append(f'.{pn}__t({{' + ',\n        '.join(', '.join(el[j:j + 16]) for j in range(0, len(el), 16)) + '})')
        for d, n, w in texts[k]:
            if re.fullmatch(r'[udew]\d+_\d+_o', n):
                cs.append(f'.{n}({n[:-2]})')
            elif re.fullmatch(r'[udew]\d+_\d+', n):
                cs.append(f'.{n}({n})')
        body.append(f'{m}_t{k} u_t{k} (' + ',\n    '.join(cs) + ');')
    (out / f'{m}.v').write_text('\n'.join(body + ['endmodule', '']))
    if a.tb_out:
        scope = a.probe.split(':')[0] if a.probe else ''
        tl = [f'// generated by subtile.py ({m}): bench handles of the tiled half (tb_vm_vcut8.sv `VM_ST)']
        for vn in a.vector_net:
            tl += ['`undef VM_CFG', f'`define VM_CFG u.u_sw`SWH.u_t{core_k}.{vn}']
        if scope:
            tl += ['`undef VM_RT', f'`define VM_RT u.u_sw`SWH.u_t{core_k}.{scope}']
        tl += ['`undef VM_ROOT', '`define VM_ROOT vm_st_dbg   // root internals are flattened: debug display only (VM_DBG)']
        Path(a.tb_out).write_text('\n'.join(tl) + '\n')
    fsd = {k: [f'# generated by subtile.py from {m}_fwd_clk.sdc: forwarded-clock outputs of {m}_t{k}'] for k in range(NT)}
    for l in (D / f'{m}_fwd_clk.sdc').read_text().splitlines():
        mm = re.search(r'\[get_ports \{(\w+)\[(\d+)\]\}\]$', l)
        if l.startswith('#') or not mm:
            continue
        pn, i = mm.group(1), int(mm.group(2))
        k = next(kk for kk in range(NT) if i in portbits_t[kk].get(pn, {}))
        fsd[k].append(l.replace(f'[get_ports {{{pn}[{i}]}}]', f'[get_ports {{{pn}__t[{portbits_t[k][pn][i]}]}}]'))
    for k in range(NT):
        (out / f'{m}_t{k}_fwd_clk.sdc').write_text('\n'.join(fsd[k]) + '\n')
    for k in range(NT):
        x0, x1, y0, y1 = tiles[k]; P = []
        cp = pins[(f'ckt{k}', 0)]
        P.append(('ck', 0, cp[0], cp[1] - x0, cp[2] - y0, cp[3]))
        for pn in sorted(ports_t[k]):
            q_ = pins[(pn, 0)]
            P.append((pn, 0, q_[0], q_[1] - x0, q_[2] - y0, q_[3]))
        for pn, mp in portbits_t[k].items():
            for i, j in mp.items():
                q_ = pins[(pn, i)]
                P.append((f'{pn}__t', j, q_[0], min(max(q_[1] - x0, 0.0), x1 - x0), min(max(q_[2] - y0, 0.0), y1 - y0), q_[3]))
        for d, n, w in texts[k]:
            if re.fullmatch(r'[udew]\d+_\d+(_o)?', n):
                P += seam_pins(g, n, w, sw, tiles[k], k, cr)
        lines = [f'# generated by subtile.py: {m}_t{k} pins (tile-local coordinates)']
        for pn, b, ly, x, y, sz in P:
            lines.append(f'place_pin -pin_name {{{pn}[{b}]}} -layer {ly} -location {{{x:.4f} {y:.4f}}} -pin_size {{{sz or dict(g.SZ, M3="0.0180 0.1920")[ly]}}}')
        pd_ = D / 'ports' / f'{m}_t{k}'; pd_.mkdir(exist_ok=True)
        (pd_ / 'io_place.tcl').write_text('\n'.join(lines) + '\n')
        (pd_ / 'ports.json').write_text(json.dumps(dict(master=f'{m}_t{k}', kind='vm8st', parent=m, tile=list(cr(k)),
            x0=x0, x1=x1, y0=y0, y1=y1, w_um=round(x1 - x0, 4), h_um=round(y1 - y0, 4), obs_top=7,
            generator='physical/hbm_accel_die_views/vm/vcut8/subtile.py', pins=len(P)), indent=1) + '\n')
        if k == core_k and mac_inst:
            ml = [f'# {m}_t{k}: slice macros stacked in one column, 28.08 um channels (subtile.py)']
            xm = round(round(((x1 - x0) - 94.824) / 2 / 0.054) * 0.054, 3)
            y0m = ((y1 - y0) - (6 * 41.04 + 5 * 28.08)) / 2          # 28.08 um channels, centred (>= 20 um to the edges)
            for j, cn in enumerate(sorted(mac_inst)):
                y = round(round((y0m + j * (41.04 + 28.08) + 0.54) / 0.048) * 0.048, 3)   # r3: core row offset, SRAM pins on the M4 track (submit_lint MACRO_GRID)
                ml.append(f'place_macro -macro_name {{{mac_inst[cn]}}} -location {{{xm} {y}}} -orientation R0')
            (out / f'{m}_t{k}_macro_place.tcl').write_text('\n'.join(ml) + '\n')


def seam_pins(g, n, w, sw, tile, k, cr):
    """pins of seam bus n on its shared tile edge: up/down buses on the N/S edges (M5/M7, + M3 on a dense seam), east/west
    buses on the E/W edges (M4/M6); the two directions of one edge interleave (forward even slots, backward odd).
    r2: slots map onto the FREE tracks of each layer only (make_vm_vcut8.free: >= 0.1 um off every PDN strap; tile
    origins sit on the strap pitch, so tile-local = half-local), spread evenly along the edge per layer (r1 put seam
    pins over M6 / M7 straps)"""
    mm = re.fullmatch(r'([udew])(\d+)_(\d+)(_o)?', n)
    d_, a_, b_ = mm.group(1), int(mm.group(2)), int(mm.group(3))
    x0, x1, y0, y1 = tile
    pair = {'u': 'd', 'd': 'u', 'e': 'w', 'w': 'e'}[d_]
    nf, nb = sw.get(f'{d_}{a_}_{b_}', 0), sw.get(f'{pair}{a_}_{b_}', 0)
    first = d_ in 'ue'
    mn, tot = min(nf, nb), nf + nb
    vert = d_ in 'ud'
    L = (x1 - x0) if vert else (y1 - y0)
    if vert:
        near = cr(k)[1] == b_                     # row b sees the b / b+1 boundary on its top edge
        lys = ('M5', 'M7', 'M3') if tot / (L - 6.0) > BUDGET else ('M5', 'M7')
    else:
        near = cr(k)[0] == b_                     # column b sees the b / b+1 boundary on its east edge
        lys = ('M4', 'M6')
    TR = {'M3': (0.018, 0.036), 'M4': (0.012, 0.048), 'M5': (0.012, 0.048), 'M6': (0.016, 0.064), 'M7': (0.016, 0.064)}
    free_t = {}
    for ly in lys:
        gr, st = TR[ly]
        free_t[ly] = [round(gr + i * st, 4) for i in range(int((3.0 - gr) / st) + 1, int((L - 3.0 - gr) / st) + 1)
                      if g.free(ly, gr + i * st)]
    per = [tot // len(lys) + (1 if r < tot % len(lys) else 0) for r in range(len(lys))]
    for r, ly in enumerate(lys):
        if per[r] > len(free_t[ly]):
            raise SystemExit(f'seam {n}: {per[r]} pins > {len(free_t[ly])} free {ly} tracks on {L:.1f} um')
    out = []
    for j in range(w):
        s_ = 2 * j + (0 if first else 1) if j < mn else 2 * mn + (j - mn)
        r = s_ % len(lys); ly = lys[r]; i = s_ // len(lys)
        ft = free_t[ly]
        a = ft[min(len(ft) - 1, int((i + 0.5) * len(ft) / per[r]))]
        if vert:
            out.append((n, j, ly, a, round((y1 - y0) - 0.096, 4) if near else 0.096, None))
        else:
            out.append((n, j, ly, round((x1 - x0) - 0.096, 4) if near else 0.096, a, None))
    return out


if __name__ == '__main__':
    main()
