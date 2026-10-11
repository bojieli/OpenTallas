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
  * seams: a cut net whose source and sink capture on the SAME edge gets an opposite-edge flop at the seam in the source
    tile, clocked by the source flop's own clock (pos -> neg -> pos is still one cycle); pos -> neg / neg -> pos nets cross
    as they are.  Every seam is a registered half-cycle hand-off (T/2 hold margin against tile-to-tile skew), 0 cycles;
  * a tile carries its core clock as its own port ck (die pin ckt<k>), its face taps, its pins at the parent locations
    and a reset relay (the parent reset reaches every tile through registered seams like any other net).
    python3 subtile.py --json nl/<m>.json --master <m> --rows 3 --cols 2 --out st/ [--report-only]
"""
import argparse, collections, json, os, re, sys
from pathlib import Path

D = Path(__file__).resolve().parent
SEQ = re.compile(r'^\$_(DFF|DFFE|SDFF|SDFFE|SDFFCE)_')
SINK_CAP = 13500     # clock sinks per tile (owner audit class 1: <= ~15k per tree)
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
    def path(ka, kb, var=0):
        """tiles from ka to kb, one edge per step; var picks the column of the row crossing (source / middle /
        destination) so N-S traffic spreads over the three columns of the row seam"""
        (ca, ra), (cb, rb) = cr(ka), cr(kb)
        cols_ = list(range(ca, cb + (1 if cb >= ca else -1), 1 if cb >= ca else -1))
        cx = cols_[min(var, len(cols_) - 1)] if var < 2 else cols_[len(cols_) // 2]
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
    for cn in cells:
        if is_mac[cn] or core_src.search(str(cells[cn].get('attributes', {}).get('src', ''))):
            set_anchor(U[cn], core_k, 'core')
    for un, cs in units.items():
        if len(cs) > 64 and sum(comb(x) for x in cs) > 32:
            set_anchor(un, core_k, 'logic cluster')
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
        dist, at = {}, {}
        dq = collections.deque()
        for un, (k, _) in anchor.items():
            dist[un], at[un] = 0, k; dq.append(un)
        while dq:
            x = dq.popleft()
            for y in adjm[x]:
                if y not in dist:
                    dist[y], at[y] = dist[x] + 1, at[x]; dq.append(y)
        return dist, at
    db, kb = bfs(succ); df, kf = bfs(pred)
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
    def target(un):
        if un in db and un in df:
            p = path(kb[un], kf[un], hash(un) % 3)
            return p[int(round((len(p) - 1) * db[un] / (db[un] + df[un])))]
        return kb.get(un, kf.get(un, core_k))
    for un in sorted((u_ for u_ in units if u_ not in anchor), key=lambda u_: (db.get(u_, 10 ** 6), u_)):
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
            grp[(kd, bool(es) and next(iter(es)) == se)].append((lc, lp, k))
        for (kd, ins), ls in grp.items():
            ck = cells[cn]['connections']['C'][0] if is_seq[cn] else cells[cn]['connections']['clk'][0]
            cuts.append((b, ks, kd, ins, ck, edge_cell.get(cn) or 'P', ls))
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
    rep = dict(master=m, grid=f'{C}x{R}', cols=cols, rows=rows, core_tile=cr(core_k), cells=len(cells), units=len(units),
               anchored=len(anchor), conflicts=len(conflict), infeasible=infeas, infeasible_ex=dbg, conflict_ex=[str(x)[:160] for x in conflict[:4]],
               violations=len(viol), viol_ex=viol[:4], viol_classes={' | '.join(map(str, k_)): v_ for k_, v_ in vcls.most_common(12)}, mixed=len(mixed), mixed_ex=mixed[:4], cuts=len(cuts),
               inserted=sum(1 for c in cuts if c[3]), seam_bits=dict(sorted(seamn.items())),
               seam_b_per_um=dict(sorted(load.items())), over_budget=over,
               sinks_per_tile={str(cr(k)): v + seam_sinks.get(k, 0) for k, v in sorted(sinks.items())},
               sink_src={str(k_): v_ for k_, v_ in srcmix.most_common(10)}, tap_split=len(tapx), tap_split_ex=dict(list(tapx.items())[:4]))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / f'{m}_st_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep))
    bad = conflict or viol or mixed
    if a.report_only or bad:
        sys.exit(2 if bad else 0)
    emit(g, out, m, h, mod, cells, rows, tiles, cr, tile, U, cuts, seam_of, port_of, pins, nm, drv, clkports,
         is_seq, is_mac, core_k)


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
         is_seq, is_mac, core_k):
    """per-tile Verilog (generic cells; flops (* keep *)), the parent shell, per-tile pins / views / sdc / macros"""
    NT, R = len(tiles), len(rows)
    used, wname = set(), {}
    def wn(b):
        if b in wname:
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
                y = round(round((y0m + j * (41.04 + 28.08)) / 0.27) * 0.27 + 0.54, 3)
                ml.append(f'place_macro -macro_name {{{mac_inst[cn]}}} -location {{{xm} {y}}} -orientation R0')
            (out / f'{m}_t{k}_macro_place.tcl').write_text('\n'.join(ml) + '\n')


def seam_pins(g, n, w, sw, tile, k, cr):
    """pins of seam bus n on its shared tile edge: up/down buses on the N/S edges (M5/M7), east/west buses on the E/W
    edges (M4/M6); the two directions of one edge interleave on the same span (forward even slots, backward odd)"""
    mm = re.fullmatch(r'([udew])(\d+)_(\d+)(_o)?', n)
    d_, a_, b_ = mm.group(1), int(mm.group(2)), int(mm.group(3))
    x0, x1, y0, y1 = tile
    pair = {'u': 'd', 'd': 'u', 'e': 'w', 'w': 'e'}[d_]
    nf, nb = sw.get(f'{d_}{a_}_{b_}', 0), sw.get(f'{pair}{a_}_{b_}', 0)
    first = d_ in 'ue'
    mn, tot = min(nf, nb), nf + nb
    vert = d_ in 'ud'
    L = (x1 - x0) if vert else (y1 - y0)
    pitch = (L - 6.0) / max(tot, 1)
    if vert:
        near = cr(k)[1] == b_                     # row b sees the b / b+1 boundary on its top edge
    else:
        near = cr(k)[0] == b_                     # column b sees the b / b+1 boundary on its east edge
    out = []
    for j in range(w):
        s_ = 2 * j + (0 if first else 1) if j < mn else 2 * mn + (j - mn)
        a = 3.0 + (s_ + 0.5) * pitch
        if vert:
            dense = tot / (L - 6.0) > BUDGET            # a dense row seam also uses M3 (three vertical pin layers)
            ly = ('M5', 'M7', 'M3')[s_ % 3] if dense else ('M5' if s_ % 2 == 0 else 'M7')
            grid, step = {'M5': (0.012, 0.048), 'M7': (0.016, 0.064), 'M3': (0.018, 0.036)}[ly]
            x = round(grid + round((a - grid) / step) * step, 4)
            out.append((n, j, ly, x, round((y1 - y0) - 0.096, 4) if near else 0.096, None))
        else:
            ly = 'M4' if s_ % 2 == 0 else 'M6'
            grid, step = (0.012, 0.048) if ly == 'M4' else (0.016, 0.064)
            y = round(grid + round((a - grid) / step) * step, 4)
            out.append((n, j, ly, round((x1 - x0) - 0.096, 4) if near else 0.096, y, None))
    return out


if __name__ == '__main__':
    main()
