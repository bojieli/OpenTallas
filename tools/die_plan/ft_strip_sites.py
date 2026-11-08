#!/usr/bin/env python3
"""DIE-HBM-89-SPB2F 11-07: kit-local FT station STRIP sites (q_spb2 vF redesign, 0 PIN CYCLES, netlist unchanged).

Why (measured on q_spb2 vE routed, DIE-HBM-89 18:43): every FT station was a clump (L33x2: 1616 flops in 41x42 um;
slots without explicit sites spiral round one point), so 600-1600 parallel hop wires enter one small box; 4,623 of
16,056 TT slew pins were station D pins.  Form here: each internal station j of a slot becomes a STRIP that spans the
bundle (perpendicular to the local travel direction, extent = bits / TRACKS_PER_UM so the station's track use stays
<= ~0.75 of a 3-layer derated cut) and is a few lanes deep along the travel direction.  Bit order across the strip
follows the input-pin order along the face (left normal of the travel direction), so consecutive stations stay
parallel and a bit keeps the same side of the bundle through every knee (planar U-turns).  Station centres are the
plan's (centroid of the old explicit sites or ft_stations.txt), and a slot may instead keep its plan sites and bit order
translated per stage (--shift SLOT:J:DX:DY) to untangle crossing chains; hops are reported per bit (Manhattan, pin->s1->..->pin) and must stay <=
--max-hop.

Sites are lower-left corners on the kit row grid (y = core_y0 + r*0.27, x = core_x0 + m*COLPITCH) with the slot's
cell envelope, free of macro keep-offs and of each other; face_flops.tcl places them FIRM (ff_put_stage) exactly as
the plan's explicit sites.  Output: ft_bit_sites.tcl (same format as tools/die_plan/ft_bit_sites.py) + JSON report.

    ft_strip_sites.py KIT OUT_TCL OUT_JSON [--strip A,B] [--shift SLOT:J:DX:DY ...] [--max-hop 400]
"""
import argparse, json, math, re, sys
from collections import defaultdict
from pathlib import Path

ROW_H = 0.27
COLPITCH = 2.16
KEEPOFF = 2.0
TRACKS_PER_UM = 16.0 * 0.75     # 3 derated (x0.25) layers of one direction ~16 tracks/um; target use 0.75
CELL_AREA = 4.3                  # lattice area per bit (um^2): flop + its inverter/drive/repeater share at ~0.1 fill
DEFAULT_CELL = (1.404, 0.27)


def read_sites(tcl):
    cells, sites = {}, defaultdict(dict)
    for l in Path(tcl).read_text().splitlines():
        m = re.match(r'dict set ff_bit_site_cells \{(\w+)\} \{([\d.]+) ([\d.]+)\}', l)
        if m:
            cells[m[1]] = (float(m[2]), float(m[3])); continue
        m = re.match(r'dict set ff_bit_sites \{(\w+),(\d+),(\d+)\} \{([\d.eE+-]+) ([\d.eE+-]+)\}', l)
        if m:
            sites[m[1]].setdefault(int(m[2]), {})[int(m[3])] = (float(m[4]), float(m[5]))
    return cells, sites


def read_stations(txt):
    st = {}
    for l in Path(txt).read_text().splitlines():
        if l.startswith('#') or not l.strip():
            continue
        f = l.split()
        k = int(f[1]); pts = [(float(f[i]), float(f[i + 1])) for i in range(4, len(f), 2)]
        st[f[0]] = dict(k=k, fin=f[2], fout=f[3], pts=pts)
    return st


def read_macros(kit):
    lef = Path(kit, 'macros').glob('*.lef')
    size = {}
    for f in lef:
        t = f.read_text()
        for m in re.finditer(r'MACRO (\S+).*?SIZE ([\d.]+) BY ([\d.]+)', t, re.S):
            size[m[1]] = (float(m[2]), float(m[3]))
    boxes = []
    sz = next(iter(size.values())) if len(size) == 1 else None
    for l in Path(kit, 'macro_place.tcl').read_text().splitlines():
        m = re.search(r'-location \{([\d.]+) ([\d.]+)\}', l)
        if m and sz:
            x, y = float(m[1]), float(m[2]); boxes.append((x, y, x + sz[0], y + sz[1]))
    return boxes


def die_core(kit):
    t = Path(kit, 'config.mk').read_text()
    c = [float(v) for v in re.search(r'CORE_AREA = ([\d. ]+)', t)[1].split()]
    return c


class Grid:
    def __init__(self, core, blocked, cell):
        self.x0, self.y0, self.x1, self.y1 = core
        self.blocked = blocked; self.cw, self.ch = cell
        self.occ = set()          # (col, row)

    def legal(self, c, r):
        x = self.x0 + c * COLPITCH; y = self.y0 + r * ROW_H
        if c < 0 or r < 0 or x + self.cw > self.x1 or y + self.ch > self.y1:
            return False
        if (c, r) in self.occ:
            return False
        for a, b, cc, d in self.blocked:
            if x < cc and a < x + self.cw and y < d and b < y + self.ch:
                return False
        return True

    def take(self, x, y, maxrad=400):
        c0 = int(round((x - self.x0) / COLPITCH)); r0 = int(round((y - self.y0) / ROW_H))
        # spiral in (col, row) with a metric that treats one column ~ 8 rows (2.16 vs 0.27 um)
        for rad in range(0, maxrad):
            best = None
            for dc in range(-(rad // 8) - 1, (rad // 8) + 2):
                for dr in (rad - abs(dc) * 8, -(rad - abs(dc) * 8)):
                    if abs(dc) * 8 > rad:
                        continue
                    c, r = c0 + dc, r0 + dr
                    if self.legal(c, r):
                        d = math.hypot(dc * COLPITCH, dr * ROW_H)
                        if best is None or d < best[0]:
                            best = (d, c, r)
            if best:
                _, c, r = best; self.occ.add((c, r))
                return (round(self.x0 + c * COLPITCH, 4), round(self.y0 + r * ROW_H, 4))
        raise RuntimeError(f'no free site near {x},{y}')


def unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)


FACE_IN = {'N': (0, -1), 'S': (0, 1), 'W': (1, 0), 'E': (-1, 0)}


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kit'); ap.add_argument('out_tcl'); ap.add_argument('out_json')
    ap.add_argument('--strip', default='', help='slots rebuilt as strips (comma list)')
    ap.add_argument('--shift', action='append', default=[], help='SLOT:J:DX:DY translate the plan sites of stage J')
    ap.add_argument('--max-hop', type=float, default=400.0)
    a = ap.parse_args()
    kit = Path(a.kit)
    cells, old = read_sites(kit / 'ft_bit_sites.tcl')
    stations = read_stations(kit / 'ft_stations.txt')
    pins = json.loads((kit / 'pins.json').read_text())
    pin = defaultdict(dict)
    for p in pins:
        pin[p['bus']][p['bit']] = (p['x'], p['y'])
    core = die_core(kit)
    blocked = [(x0 - KEEPOFF, y0 - KEEPOFF, x1 + KEEPOFF, y1 + KEEPOFF) for x0, y0, x1, y1 in read_macros(kit)]
    blocked = [(x0 - KEEPOFF, y0 - KEEPOFF, x1 + KEEPOFF, y1 + KEEPOFF) for x0, y0, x1, y1 in read_macros(kit)]
    shift = defaultdict(dict)
    for c in a.shift:
        s, j, dx, dy = c.split(':'); shift[s][int(j)] = (float(dx), float(dy))
    strip = set(filter(None, a.strip.split(',')))
    grid = Grid(core, blocked, DEFAULT_CELL)
    todo = [s for s in stations if s in strip or s in shift]
    # reserve the explicit sites of every slot left as the plan wrote it
    for name, bits in old.items():
        if name in todo:
            continue
        for st_ in bits.values():
            for xy in st_.values():
                grid.occ.add((int(round((xy[0] - core[0]) / COLPITCH)), int(round((xy[1] - core[1]) / ROW_H))))
    out_cells, out_sites, report = dict(cells), {k: v for k, v in old.items() if k not in todo}, {}
    for name in todo:
        st = stations[name]; k = st['k']; pi, po = pin[name + '_i'], pin[name + '_o']; n = len(pi)
        A = (sum(p[0] for p in pi.values()) / n, sum(p[1] for p in pi.values()) / n)
        B = (sum(p[0] for p in po.values()) / n, sum(p[1] for p in po.values()) / n)
        cell = cells.get(name, DEFAULT_CELL)
        grid.cw, grid.ch = cell
        new, srep = {}, []
        if name in shift:
            # SHIFT form: the plan's own station shape and bit order, translated (untangles crossing chains)
            for j in range(1, k):
                dx, dy = shift[name].get(j, (0.0, 0.0))
                new[j] = {}; disp = []
                for b in sorted(old[name][j]):
                    x, y = old[name][j][b]
                    got = grid.take(x + dx, y + dy)
                    disp.append(math.hypot(got[0] - x - dx, got[1] - y - dy))
                    new[j][b] = got
                xs = [q[0] for q in new[j].values()]; ys = [q[1] for q in new[j].values()]
                srep.append(dict(stage=j, form='shift', shift=[dx, dy], bbox=[min(xs), min(ys), max(xs) + cell[0], max(ys) + cell[1]],
                                 disp_max=round(max(disp), 2)))
        else:
            # STRIP form across the bundle at the plan's station centre, bit order = input pin order (left normal)
            cen = {}
            for j in range(1, k):
                if name in old and j in old[name]:
                    v = list(old[name][j].values()); cen[j] = (sum(q[0] for q in v) / len(v), sum(q[1] for q in v) / len(v))
                else:
                    cen[j] = st['pts'][j]
            path = [A] + [cen[j] for j in range(1, k)] + [B]
            t0 = FACE_IN[st['fin']]; n0 = (-t0[1], t0[0])
            rank = {b: i for i, b in enumerate(sorted(pi, key=lambda b: (pi[b][0] * n0[0] + pi[b][1] * n0[1], b)))}
            P = n / TRACKS_PER_UM
            for j in range(1, k):
                t = unit((path[j + 1][0] - path[j - 1][0], path[j + 1][1] - path[j - 1][1]))
                nn = (-t[1], t[0])
                L = max(1, int(math.ceil(n * 1.08 / P)))
                nslots = int(math.ceil(n / L)); pp = P / nslots
                apitch = CELL_AREA / pp
                c = cen[j]
                new[j] = {}; disp = []
                for b in sorted(pi, key=lambda b: rank[b]):
                    s, lane = divmod(rank[b], L)
                    u = (s - (nslots - 1) / 2) * pp; v = (lane - (L - 1) / 2) * apitch
                    x = c[0] + u * nn[0] + v * t[0]; y = c[1] + u * nn[1] + v * t[1]
                    x = min(max(x, core[0] + cell[0] / 2 + 1), core[2] - cell[0] / 2 - 1)
                    y = min(max(y, core[1] + cell[1] / 2 + 1), core[3] - cell[1] / 2 - 1)
                    got = grid.take(x - cell[0] / 2, y - cell[1] / 2)
                    disp.append(math.hypot(got[0] + cell[0] / 2 - x, got[1] + cell[1] / 2 - y))
                    new[j][b] = got
                xs = [q[0] for q in new[j].values()]; ys = [q[1] for q in new[j].values()]
                srep.append(dict(stage=j, form='strip', centre=[round(c[0], 2), round(c[1], 2)], travel=[round(t[0], 3), round(t[1], 3)],
                                 strip_um=round(P, 1), lanes=L, perp_pitch=round(pp, 3), along_pitch=round(apitch, 3),
                                 bbox=[min(xs), min(ys), max(xs) + cell[0], max(ys) + cell[1]],
                                 disp_max=round(max(disp), 2), disp_p95=round(sorted(disp)[int(.95 * len(disp))], 2)))
        # per-bit hops (Manhattan, lower-left sites, pin -> s1 -> .. -> pin), new vs plan sites
        def hops(sites, per):
            hs = []
            for b in pi:
                seq = [pi[b]] + [sites[j][b] for j in range(1, k)] + [po.get(b, B)]
                hh = [md(seq[i], seq[i + 1]) for i in range(len(seq) - 1)]
                for i, h in enumerate(hh):
                    per[i] = max(per.get(i, 0), round(h, 1))
                hs.append(max(hh))
            return hs
        per_new, per_old = {}, {}
        hn = sorted(hops(new, per_new))
        ho = sorted(hops({j: old[name][j] for j in range(1, k)}, per_old)) if name in old else None
        report[name] = dict(bits=n, k=k, stations=srep, hop_max=round(hn[-1], 1), hop_p95=round(hn[int(.95 * n)], 1),
                            old_hop_max=round(ho[-1], 1) if ho else None, old_hop_p95=round(ho[int(.95 * n)], 1) if ho else None,
                            hops_over=sum(h > a.max_hop for h in hn), hop_max_by_index=per_new, old_hop_max_by_index=per_old)
        out_cells[name] = cell
        out_sites[name] = new
    lines = ['# Generated explicit FT cell lower-left sites (um); stage j starts at 1.',
             '# DIE-HBM-89-SPB2F vF: strip sites by tools/die_plan/ft_strip_sites.py for ' + ','.join(todo),
             'set ff_bit_sites {}', 'set ff_bit_site_cells {}']
    for name in sorted(out_sites):
        w, h = out_cells[name]
        lines.append(f'dict set ff_bit_site_cells {{{name}}} {{{w:.9g} {h:.9g}}}')
        for j in sorted(out_sites[name]):
            for b in sorted(out_sites[name][j]):
                x, y = out_sites[name][j][b]
                lines.append(f'dict set ff_bit_sites {{{name},{j},{b}}} {{{x:.9g} {y:.9g}}}')
    Path(a.out_tcl).write_text('\n'.join(lines) + '\n')
    Path(a.out_json).write_text(json.dumps(report, indent=1))
    for nme, r in report.items():
        print(nme, 'bits', r['bits'], 'hop max', r['hop_max'], 'p95', r['hop_p95'], 'old', r['old_hop_max'], r['old_hop_p95'],
              'over', r['hops_over'], 'per', r['hop_max_by_index'], 'oldper', r['old_hop_max_by_index'])
        for s in r['stations']:
            print('   ', s)
    return 1 if any(r['hops_over'] for r in report.values()) else 0


if __name__ == '__main__':
    sys.exit(main())
