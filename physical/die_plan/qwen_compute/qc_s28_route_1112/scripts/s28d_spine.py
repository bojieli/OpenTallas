#!/usr/bin/env python3
"""QC-S28-D 11-12: cb* 'bc column spine' planner (positions/orients unchanged, +0 cycles).

For each listed type, the bc broadcast column (ring -> u_bin_<bc_i> -> xstn u_st -> d<D> chain -> next xstn ...
-> u_bout_<bc_o>) gets FIRM plan sites for its EXISTING flops via partition_types[T].relay_sites (DIE-KV-59
mechanism, kit_istations rs_place_all: FIRM pre-GPL, released before DPL).  Sites follow free-space L1 geodesics
around the hard cores (9 um halo): each station sits where it minimises its worst hop (predecessor, own tap pin
group via the FIRM u_pc_nk pipe 6 um off the pin, successor chain / out window); bin halfway on the ring->station
geodesic, d-chain stages at equal fractions of the station->station geodesic.

  s28d_spine.py PLAN RTL_DIR PINS_JSON NAMES_DIR TYPES OUT_DIR
     -> OUT_DIR/delta_s28d.json (relay_sites per type), OUT_DIR/hops_s28d.tsv, OUT_DIR/spine_<T>.json (render input)
"""
import collections, heapq, json, math, re, sys
from pathlib import Path

G = 4.32          # grid um
HALO = 9.0        # macro halo (chain_even / ff_put_near convention)
EDGE = 6.0        # keep from outline
PC_OFF = 6.0      # u_pc_nk FIRM offset outside the core pin (core_input_anchor.tcl)
BAR = 40.0        # stage bar length (bits spread across the street)
REACH = 405.0


def core_box(h):
    x, y = h['origin_um']; w, hh = h['outline_um']
    return (x, y, x + w, y + hh)


def tap_points(h, pins):
    """abs (x, y) of the tap pin group's two ends + face, PC_OFF outside the face"""
    w, hh = h['outline_um']; ox, oy = h['origin_um']; o = h.get('orient', 'R0')
    tp = [p for p in pins if re.match(r'tap(\[|$)', p['name'])]
    px = tp[0]['x']; ys = [p['y'] for p in tp]
    fx = (w - px) if o in ('MY', 'R180') else px
    y0, y1 = min(ys), max(ys)
    if o in ('MX', 'R180'):
        y0, y1 = hh - y1, hh - y0
    east = fx > w / 2
    x = ox + fx + (PC_OFF if east else -PC_OFF)
    return [(x, oy + y0), (x, oy + y1)], ('E' if east else 'W')


class Grid:
    def __init__(self, W, H, blocks):
        self.W, self.H = W, H
        self.nx, self.ny = int(W // G), int(H // G)
        self.free = [[True] * self.ny for _ in range(self.nx)]
        for i in range(self.nx):
            x = (i + 0.5) * G
            for j in range(self.ny):
                y = (j + 0.5) * G
                if x < EDGE or y < EDGE or x > W - EDGE or y > H - EDGE:
                    self.free[i][j] = False; continue
                for (a, b, c, d) in blocks:
                    if a - HALO < x < c + HALO and b - HALO < y < d + HALO:
                        self.free[i][j] = False; break
        # clearance (cells) to the nearest blocked cell: prefers street centre lines
        self.clr = self._clearance()

    def _clearance(self):
        INF = 10 ** 9
        dist = [[INF] * self.ny for _ in range(self.nx)]
        q = collections.deque()
        for i in range(self.nx):
            for j in range(self.ny):
                if not self.free[i][j]:
                    dist[i][j] = 0; q.append((i, j))
        while q:
            i, j = q.popleft()
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= a < self.nx and 0 <= b < self.ny and dist[a][b] > dist[i][j] + 1:
                    dist[a][b] = dist[i][j] + 1; q.append((a, b))
        return dist

    def cell(self, p):
        i = min(self.nx - 1, max(0, int(p[0] // G))); j = min(self.ny - 1, max(0, int(p[1] // G)))
        if self.free[i][j]:
            return (i, j)
        best = None
        for r in range(1, 60):
            for a in range(i - r, i + r + 1):
                for b in (j - r, j + r):
                    if 0 <= a < self.nx and 0 <= b < self.ny and self.free[a][b]:
                        d = abs(a - i) + abs(b - j)
                        if best is None or d < best[0]: best = (d, (a, b))
            for b in range(j - r, j + r + 1):
                for a in (i - r, i + r):
                    if 0 <= a < self.nx and 0 <= b < self.ny and self.free[a][b]:
                        d = abs(a - i) + abs(b - j)
                        if best is None or d < best[0]: best = (d, (a, b))
            if best: return best[1]
        raise SystemExit(f'no free cell near {p}')

    def xy(self, c):
        return ((c[0] + 0.5) * G, (c[1] + 0.5) * G)

    def field(self, p):
        """L1 geodesic distance (um) from point p (its nearest free cell; + the snap distance)"""
        c = self.cell(p); sx, sy = self.xy(c); snap = abs(sx - p[0]) + abs(sy - p[1])
        INF = 10 ** 9
        d = [[INF] * self.ny for _ in range(self.nx)]
        d[c[0]][c[1]] = 0; q = collections.deque([c])
        while q:
            i, j = q.popleft()
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= a < self.nx and 0 <= b < self.ny and self.free[a][b] and d[a][b] == INF:
                    d[a][b] = d[i][j] + 1; q.append((a, b))
        return lambda cc: (d[cc[0]][cc[1]] * G + snap) if d[cc[0]][cc[1]] < INF else 1e9, d

    def path(self, a, b):
        """geodesic cell path a->b (points), descending b's field, preferring clearance then straightness"""
        _, d = self.field(b)
        cur = self.cell(a); out = [cur]; last = None
        while d[cur[0]][cur[1]] > 0:
            i, j = cur; cand = []
            for a2, b2 in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= a2 < self.nx and 0 <= b2 < self.ny and d[a2][b2] == d[i][j] - 1:
                    dirn = (a2 - i, b2 - j)
                    cand.append((-min(self.clr[a2][b2], 12), 0 if dirn == last else 1, (a2, b2), dirn))
            if not cand:
                break
            cand.sort(); _, _, nxt, last = cand[0]
            cur = nxt; out.append(cur)
        return [self.xy(c) for c in out]


def at_frac(pts, f):
    L = [0.0]
    for k in range(1, len(pts)):
        L.append(L[-1] + abs(pts[k][0] - pts[k - 1][0]) + abs(pts[k][1] - pts[k - 1][1]))
    t = f * L[-1]
    for k in range(1, len(pts)):
        if L[k] >= t:
            seg = L[k] - L[k - 1] or 1.0
            u = (t - L[k - 1]) / seg
            p = (pts[k - 1][0] + u * (pts[k][0] - pts[k - 1][0]), pts[k - 1][1] + u * (pts[k][1] - pts[k - 1][1]))
            dx, dy = pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]
            return p, ('V' if abs(dy) >= abs(dx) else 'H')
    return pts[-1], 'V'


def parse_rtl(txt):
    st = {}
    for m in re.finditer(r'qfd_c_xstnw?\s+(u_u_fab_u_x_(\d)_(\d))\s*\(([^;]*?)\);', txt, re.S):
        body = m.group(4)
        b = re.search(r'\.b_d\(\s*([A-Za-z0-9_]+)', body).group(1)
        st[m.group(1)] = dict(name=m.group(1), r=m.group(2), c=m.group(3), b_src=b)
    dly = {}
    for m in re.finditer(r'ot_dp_dly\s*#\(\s*\.W\((\d+)\)\s*,\s*\.D\((\d+)\)\s*\)\s+(u_d\d+_u_fab_u_x_\d_\d_a_d)\s*\(', txt):
        dly[m.group(3)] = int(m.group(2))
    tap = {}
    for m in re.finditer(r'u_pc_nk_u_t_(\d)_(\d)_tap\s*\(\s*\.clk\(clk\),\s*\.d\(w_u_fab_u_x_(\d)_(\d)_tap_d', txt):
        tap[f'u_u_fab_u_x_{m.group(3)}_{m.group(4)}'] = f'u_t{m.group(1)}{m.group(2)}'
    # QC-S28-ROUTE 11-12 (cbx_q10): a station whose tap feeds the core directly (NL tile, no u_pc_nk pipe)
    for m in re.finditer(r'qfd_tile_\w+\s+u_u_t_(\d)_(\d)\s*\(([^;]*?)\);', txt, re.S):
        for t_ in re.finditer(r'\.tap\(\s*w_u_fab_u_x_(\d)_(\d)_tap_d', m.group(3)):
            tap.setdefault(f'u_u_fab_u_x_{t_.group(1)}_{t_.group(2)}', f'u_t{m.group(1)}{m.group(2)}')
    bout = {}
    for m in re.finditer(r'ot_dp_st\s*#\(\.W\(\d+\)\)\s+u_bout_(\w+)\s*\([^;]*?\.d\(w_u_fab_u_x_(\d)_(\d)_a_d', txt):
        bout[f'u_u_fab_u_x_{m.group(2)}_{m.group(3)}'] = m.group(1)
    return st, dly, tap, bout


def main(a):
    plan, rtl, pinsf, names_dir, types, outd = a
    P = json.load(open(plan)); pins = json.load(open(pinsf))['pins']
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    delta = dict(schema='opentallas.qc_s28d_delta.v1', base_plan_sha256_12=None, fields=['partition_types[T].relay_sites'],
                 changes={})
    rows = ['type\tcolumn\thop\tfrom\tto\tlen_um\tover_reach\tnote']
    for tn in types.split(','):
        t = P['partition_types'][tn]; W, H = t['outline_um']
        if t.get('relay_sites'):
            raise SystemExit(f'{tn}: already has relay_sites')
        hc = {h['inst']: h for h in t['hard_cores']}
        blocks = [core_box(h) for h in t['hard_cores']]
        grid = Grid(W, H, blocks)
        txt = open(Path(rtl) / f'{tn}.sv').read()
        st, dly, tap, bout = parse_rtl(txt)
        names = [l.strip() for l in open(Path(names_dir) / f'names_{tn}.txt') if l.strip()]
        names = sorted(set(names))
        buses = {b['name']: b for b in t['buses']}
        bands = t['clock'].get('landing_contract', {}).get('bands', {})

        def window_pt(b):
            w0, w1 = b['window_um']; m = (w0 + w1) / 2
            return {'S': (m, 0.0), 'N': (m, H), 'W': (0.0, m), 'E': (W, m)}[b['face']]

        def in_point(bus):
            if bus in bands and bands[bus].get('rect_um'):
                a_, b_, c_, d_ = bands[bus]['rect_um']; return ((a_ + c_) / 2, (b_ + d_) / 2), 'band'
            ch = [h for h in t['hard_cores'] if h['inst'] == f'cl_{bus}']
            if ch:
                a_, b_, c_, d_ = core_box(ch[0]); b = buses[bus]
                return (((a_ + c_) / 2, d_ if b['face'] == 'S' else b_) if b['face'] in 'SN'
                        else ((c_ if b['face'] == 'W' else a_), (b_ + d_) / 2)), 'hard_cland'
            return window_pt(buses[bus]), 'window'

        # chains: first station fed by a bin (b_src '<bus>_q'), next ones by a d chain of the previous station
        cols = []
        for s in st.values():
            m = re.match(r'(bc_i\w+?)_q$', s['b_src'])
            if m:
                chain = [s['name']]
                while True:
                    nxt = [x for x in st.values() if x['b_src'] == f"d{dly.get('u_d6_' + chain[-1][2:] + '_a_d', 6)}_{chain[-1][2:]}_a_d"
                           or re.fullmatch(rf'd\d+_{chain[-1][2:]}_a_d', x['b_src'])]
                    if not nxt: break
                    chain.append(nxt[0]['name'])
                cols.append((m.group(1), chain))
        rs = {}; spine = dict(type=tn, outline=[W, H], cores=[core_box(h) + (h['inst'], h.get('orient', 'R0')) for h in t['hard_cores']],
                             bands={k: v.get('rect_um') for k, v in bands.items() if v.get('rect_um')}, columns=[])
        for bus, chain in cols:
            inp, inkind = in_point(bus)
            taps = {}
            for s in chain:
                core = tap[s]; tp, face = tap_points(hc[core], pins); taps[s] = (core, tp, face)
            outp = {s: window_pt(buses[bout[s]]) for s in chain if s in bout and bout[s] in buses}
            D = {s: dly.get('u_d' + str(re.search(r'd(\d+)_', st[n]['b_src']).group(1)) + '_' + s[2:] + '_a_d', 0)
                 for s, n in zip(chain[:-1], chain[1:])}
            # nodes: bin, per station k: SB_k (b_q + ctl: feeds next chain / bout and hold/cap), ST_k (t_q + hold + cap:
            # feeds the core tap via the FIRM u_pc_nk pipe), per chain k->k+1: L_k (its last stage; feeds SB/ST of k+1).
            # Both SB_k and ST_k capture the same input (ot_qfd_xcst a_d -> b_q and t_q), hold/cap read b_q.
            fixed = {'ring': inp}
            for k, s in enumerate(chain):
                for j, tp in enumerate(taps[s][1]):
                    fixed[f'tap{k}_{j}'] = tp
                if s in outp:
                    fixed[f'out{k}'] = outp[s]
            edges = [('ring', 'bin', 1)]
            for k, s in enumerate(chain):
                pred = 'bin' if k == 0 else f'L{k-1}'
                edges += [(pred, f'SB{k}', 1), (pred, f'ST{k}', 1), (f'SB{k}', f'ST{k}', 1)]
                edges += [(f'ST{k}', f'tap{k}_{j}', 1) for j in range(len(taps[s][1]))]
                if s in outp:
                    edges.append((f'SB{k}', f'out{k}', 1))
                if k + 1 < len(chain):
                    edges.append((f'SB{k}', f'L{k}', D[s]))
            init = {'bin': inp}
            for k, s in enumerate(chain):
                init[f'SB{k}'] = init[f'ST{k}'] = taps[s][1][0]
                if k + 1 < len(chain):
                    init[f'L{k}'] = taps[chain[k + 1]][1][0]
            pos = dict(fixed); pos.update({n: grid.xy(grid.cell(v)) for n, v in init.items()})
            mov = list(init)
            cells = [(i, j) for i in range(0, grid.nx, 2) for j in range(0, grid.ny, 2) if grid.free[i][j]]
            fcache = {}
            def fld(n):
                key = (n, pos[n])
                if key not in fcache:
                    fcache[key] = grid.field(pos[n])[0]
                return fcache[key]
            for it in range(8):
                moved = 0
                for n in mov:
                    inc = [(b if a == n else a, dv) for a, b, dv in edges if n in (a, b)]
                    fs = [(fld(o), dv) for o, dv in inc]
                    best = None
                    for c in cells:
                        terms = [f(c) / dv for f, dv in fs]
                        key = (round(max(terms), 1), round(sum(terms), 1), -grid.clr[c[0]][c[1]])
                        if best is None or key < best[0]:
                            best = (key, c)
                    np_ = grid.xy(best[1])
                    if np_ != pos[n]:
                        moved += 1; pos[n] = np_
                if not moved:
                    break
            hop = lambda p, q: grid.field(q)[0](grid.cell(p))
            col = dict(bus=bus, in_point=inp, in_kind=inkind, stations=[], hops=[], nodes={k: v for k, v in pos.items()})
            groups = [(f'u_bin_{bus}', pos['bin'], 'V')]
            col['hops'].append(('ring', 'bin', hop(inp, pos['bin'])))
            for k, s in enumerate(chain):
                pred, predn = (pos['bin'], 'bin') if k == 0 else (pos[f'L{k-1}'], f'u_d{D[chain[k-1]]}_{chain[k-1][2:]}_a_d[{D[chain[k-1]]-1}]')
                groups.append((s + '#B', pos[f'SB{k}'], 'V')); groups.append((s + '#T', pos[f'ST{k}'], 'V'))
                col['stations'].append(dict(st=s, b_q=pos[f'SB{k}'], t_q=pos[f'ST{k}'], core=taps[s][0], tap=taps[s][1]))
                col['hops'] += [(predn, s + '.b_q', hop(pred, pos[f'SB{k}'])), (predn, s + '.t_q', hop(pred, pos[f'ST{k}'])),
                                (s + '.b_q', s + '.hold/cap', hop(pos[f'SB{k}'], pos[f'ST{k}'])),
                                (s + '.t_q', f'pc@{taps[s][0]}.tap', max(hop(pos[f'ST{k}'], p) for p in taps[s][1]))]
                if s in outp:
                    col['hops'].append((s + '.b_q', f'bout@{bout[s]}', hop(pos[f'SB{k}'], outp[s])))
                if k + 1 < len(chain):
                    Dk = D[s]; dn = 'u_d%d_%s_a_d' % (Dk, s[2:])
                    pth = grid.path(pos[f'SB{k}'], pos[f'L{k}'])
                    prev, prevn = pos[f'SB{k}'], s + '.b_q'
                    for j in range(Dk):
                        p, dr = (at_frac(pth, (j + 1) / Dk) if j < Dk - 1 else (pos[f'L{k}'], 'V'))
                        groups.append((f'{dn}#{j}', p, dr)); col['hops'].append((prevn, f'{dn}[{j}]', hop(prev, p)))
                        prev, prevn = p, f'{dn}[{j}]'
            # flop keys per group, spread on a bar across the route
            for g, p, dr in groups:
                if g.endswith('#B'):
                    pat = re.compile(re.escape(g[:-2]) + r'\.u_st\.(b_d\[\d+\]|cnt\[\d+\]|run)$')
                elif g.endswith('#T'):
                    pat = re.compile(re.escape(g[:-2]) + r'\.u_st\.(tap_d\[\d+\]|cap\[\d+\])$')
                elif '#' in g:
                    dn, j = g.split('#'); j = int(j); Dk = int(re.match(r'u_d(\d+)_', dn).group(1))
                    pat = re.compile(re.escape(dn) + (r'\.q\[\d+\]$' if j == Dk - 1 else r'\.r\[%d\]\[\d+\]$' % j))
                elif g.startswith('u_bin_'):
                    pat = re.compile(re.escape(g) + r'/(q\[\d+\]|eq)$')
                fl = [n for n in names if pat.search(n)]
                if not fl:
                    raise SystemExit(f'{tn}: no flops for {g}')
                fl.sort(key=lambda n: [int(x) for x in re.findall(r'\d+', n.split('.')[-1].split('/')[-1])] or [0])
                n = len(fl)
                for i, nm in enumerate(fl):
                    off = (i / max(1, n - 1) - 0.5) * BAR
                    x, y = (p[0] + off, p[1]) if dr == 'V' else (p[0], p[1] + off)
                    c = grid.cell((x, y)); x, y = grid.xy(c)
                    rs[nm] = [round(x, 3), round(y, 3)]
                col.setdefault('groups', []).append(dict(group=g, xy=[round(p[0], 2), round(p[1], 2)], flops=n))
            covered = set(rs)
            col['unsited'] = sorted(n for n in names if (n.startswith('u_bin_' + bus + '/') or any(n.startswith(s + '.') or n.startswith('u_d') and s[2:] in n for s in chain)) and n not in covered)[:20]
            for f_, t_, L in col['hops']:
                rows.append(f'{tn}\t{bus}\t{f_}->{t_}\t{f_}\t{t_}\t{L:.1f}\t{"OVER" if L > REACH else ""}\t')
            spine['columns'].append(col)
        delta['changes'][tn] = dict(relay_sites=dict(sorted(rs.items())), flops=len(rs))
        (outd / f'spine_{tn}.json').write_text(json.dumps(spine, indent=1, default=list) + '\n')
        print(tn, 'columns', [(b, c) for b, c in cols], 'relay_sites', len(rs), flush=True)
    (outd / 'delta_s28d.json').write_text(json.dumps(delta, indent=1) + '\n')
    (outd / 'hops_s28d.tsv').write_text('\n'.join(rows) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
