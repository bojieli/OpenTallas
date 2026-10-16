#!/usr/bin/env python3
"""Full-die GRT + TT/FF STA case of the v16 HBM die netlist on compact660_v5 (H-DIE-V16CASE 2026-10-16, "d3").

    die_case_v16.py --views VIEWS_DIR --out CASE_DIR [--die-repeaters] [--paths N]

Same pattern as die_case.py (d2: service engine + SM), extended to EVERY v16 source-contract instance
(results/arch/hbm_die_v16/contract.json): views from tools/hbm_die_v15/v16_views.py (+ v16_synth_drive.py / v16_fetch.py),
nets bit-exact from the contract edges, die clock trees per contract clock domain (die_clock_tree.py), die repeaters
(repair_design -max_wire_length 400), global route, TT setup / FF hold STA.  Open inputs stay open (manifest, with
owner); straps are constants of the design and stay open in this timing case (listed); nothing is tied or stubbed.
The v16 strict port bind FAILs (51 exposed input ports) -> every result of this case is labelled NOT_A_DIE_RESULT.

Views: REAL = closed routed view (LEF + TT/FF ETM); SYNTH = current-source mapped-netlist ETM (ideal clocks, no wires,
clock pin re-capped to one 2 fF entry) with a generated abstract: outline = the instance's grant slot when it is the
only instance of that slot, else std area / 0.60 + 1.3 x macro area, square, grown until every port bit fits one
0.048 um track per face over 90 % of the face (pin-bound outlines are flagged); every port on the face that points to
the bit-weighted centroid of its peers (spill to the next face when full), ordered along the face by peer position.
hfd_ckgen (PLL = the allowed analog model, no Liberty) is out of the case: the domain clocks and resets enter as die
ports at its grant slot, as in d2.

Placement order (every generated home is reported in manifest.json 'homes'):
  1. PHY at its grant slot; PC controller leaves over their PHY channel and service groups in their PC band box (d2
     rule); every other instance that is alone in its grant slot at the slot origin/orientation;
  2. instances that share a grant slot or name a compact660_v5 plan block: first fit inside that region, else the
     nearest free area to the region centre ('overflow' = slot misfit, measured);
  3. relays with a planned home (contract note 'home (x, y) um'): nearest free area to that home;
  4. remaining blocks: nearest free area to the bit-weighted centroid of their already placed peers (most-connected
     first); an instance whose slot names another instance goes next to it;
  5. relay chains without homes: evenly along the lanes2.json lane of their end blocks' plan link (else an L path),
     nearest free area to each point.
Generated homes keep a 10.8 um halo (>= 21.6 um channels between them); relays have no halo.
"""
import argparse, hashlib, json, math, re, shutil, sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from die_case import synth_lef, entry_cap, ports_of_lib, rect_of  # noqa: E402
from view_case import lef_pins, lef_xy  # noqa: E402
import die_clock_tree as dct  # noqa: E402

CONTRACT = ROOT / 'results/arch/hbm_die_v16/contract.json'
GRANTS = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
PLAN = ROOT / 'results/arch/hbm_die_v15/compact660_v5/compact.P.json'
LANES = ROOT / 'results/arch/hbm_die_v15/compact660_v5/lanes2.json'
PERIOD = dict(stream=833.333, hbm=1024.0, serial=1111.111)
CKGEN = 'hb_ckgen'
CELL = 5.4      # occupancy grid (um)
HALO = 10.8
PHY_M, CTL_M, SVG_M = 'ot_hbm3e_phy_rc_e8p5', 'ot_hbm_svc_pc_ctrl_leaf', 'ot_hbm_svc_sm_group'
Q = ('SW', 'SE', 'NW', 'NE')
# instance -> the compact660_v5 plan blocks reserved for its function (generated homes try these first)
OWNER = [(r'hb_vms_(SW|SE|NW|NE)', lambda m: rf'(vmh|vmb)_{m.group(1)}\d*'),
         (r'lg_(SW|SE|NW|NE)_\d', lambda m: rf'(vmh|vmb)_{m.group(1)}\d*'),
         (r'sfucore_(SW|SE|NW|NE)', lambda m: rf'sfu_{m.group(1)}\d'),
         (r'hc_(SW|SE|NW|NE)', lambda m: rf'hc_{m.group(1)}\d'),
         (r'hb_quant_(NW)', lambda m: rf'quant_{m.group(1)}\d'),
         (r'hb_(idx|argmax)', lambda m: r'idx_\w+')]


def snap(v, g):
    return round(math.ceil(v / g - 1e-9) * g, 3)


class Occ:
    """occupancy grid with an integral image for O(1) rectangle-free tests."""

    def __init__(self, W, H):
        self.nx, self.ny = int(W / CELL) + 1, int(H / CELL) + 1
        self.g = np.zeros((self.ny, self.nx), np.uint8)
        self.W, self.H = W, H
        self._ii = None

    def mark(self, x, y, w, h, halo=0.0):
        i0 = max(0, int((x - halo) / CELL)); j0 = max(0, int((y - halo) / CELL))
        i1 = min(self.nx, int(math.ceil((x + w + halo) / CELL))); j1 = min(self.ny, int(math.ceil((y + h + halo) / CELL)))
        self.g[j0:j1, i0:i1] = 1
        self._ii = None

    def ii(self):
        if self._ii is None:
            a = np.zeros((self.ny + 1, self.nx + 1), np.int32)
            a[1:, 1:] = self.g.cumsum(0).cumsum(1)
            self._ii = a
        return self._ii

    def find(self, cx, cy, w, h, halo=0.0, region=None, rmax=None):
        """lower-left (x, y) of a free w x h rect (+halo) nearest to centre (cx, cy); region = (x0, y0, x1, y1) limits it."""
        nw = int(math.ceil((w + 2 * halo) / CELL)); nh = int(math.ceil((h + 2 * halo) / CELL))
        ii = self.ii()
        ci = int((cx - w / 2 - halo) / CELL); cj = int((cy - h / 2 - halo) / CELL)
        lo_i, lo_j, hi_i, hi_j = 0, 0, self.nx - nw, self.ny - nh
        if region:
            lo_i = max(lo_i, int(math.ceil(region[0] / CELL))); lo_j = max(lo_j, int(math.ceil(region[1] / CELL)))
            hi_i = min(hi_i, int(region[2] / CELL) - nw); hi_j = min(hi_j, int(region[3] / CELL) - nh)
        if hi_i < lo_i or hi_j < lo_j:
            return None
        R = rmax or max(self.nx, self.ny)
        for r in range(0, R):
            ii_ = np.concatenate([np.arange(ci - r, ci + r + 1), np.full(2 * r - 1 if r else 0, ci - r),
                                  np.full(2 * r - 1 if r else 0, ci + r), np.arange(ci - r, ci + r + 1)]) if r else np.array([ci])
            jj_ = np.concatenate([np.full(2 * r + 1, cj - r), np.arange(cj - r + 1, cj + r),
                                  np.arange(cj - r + 1, cj + r), np.full(2 * r + 1, cj + r)]) if r else np.array([cj])
            ok = (ii_ >= lo_i) & (ii_ <= hi_i) & (jj_ >= lo_j) & (jj_ <= hi_j)
            if not ok.any():
                if r > max(abs(ci - lo_i), abs(ci - hi_i), abs(cj - lo_j), abs(cj - hi_j)) + 1:
                    return None
                continue
            i, j = ii_[ok], jj_[ok]
            s = ii[j + nh, i + nw] - ii[j, i + nw] - ii[j + nh, i] + ii[j, i]
            free = np.nonzero(s == 0)[0]
            if len(free):
                d = (i[free] - ci) ** 2 + (j[free] - cj) ** 2
                k = free[int(np.argmin(d))]
                return round(i[k] * CELL + halo, 3), round(j[k] * CELL + halo, 3)
        return None


def lef_size(lef):
    m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', Path(lef).read_text())
    return float(m.group(1)), float(m.group(2))


def pin(port, bits, k):
    return f'{port}[{k}]' if bits > 1 else port


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--contract', type=Path, default=CONTRACT, help='source contract (default: main); freeze it to the synthesis snapshot')
    ap.add_argument('--die-repeaters', action='store_true')
    ap.add_argument('--paths', type=int, default=200000)
    ap.add_argument('--plan', type=Path, default=PLAN, help='die plan (compact660_v5 default; v6 for d4)')
    ap.add_argument('--grants', type=Path, default=GRANTS)
    ap.add_argument('--lanes', type=Path, default=LANES)
    ap.add_argument('--clock-mode', default='hbm=quad,stream=htree,serial=htree')
    ap.add_argument('--clock-bin-um', type=float, default=1600.0)
    ap.add_argument('--no-clock', action='store_true', help='placement/images only (skip die clock trees and run files)')
    a = ap.parse_args()
    C = json.loads(a.contract.read_text()); G = json.loads(a.grants.read_text()); P = json.loads(a.plan.read_text())
    V = json.loads((a.views / 'views.json').read_text())
    lanes = json.loads(a.lanes.read_text())
    slots = {s['name']: s for s in G['slots']}
    W, H = G['floorplan']['die_um']
    I = C['instances']
    out = a.out; vd = out / 'views'; vd.mkdir(parents=True, exist_ok=True); (out / 'out').mkdir(exist_ok=True)

    # ---------------- views ----------------
    cell_of, kinds, excluded, ecap, size = {}, {}, {}, {}, {}
    for c, e in V.items():
        if e['master'] == 'hfd_ckgen':
            excluded[c] = 'PLL model: domain clocks/resets enter as die ports at the ckgen slot'
            continue
        if e['kind'] == 'REAL':
            shutil.copy(ROOT / e['lef'], vd / f'{c}.lef')
            shutil.copy(ROOT / e['tt'], vd / f'{c}_tt.lib'); shutil.copy(ROOT / e['ff'], vd / f'{c}_ff.lib')
            kinds[c] = 'REAL' + (' (TT abstract used at FF: modelled off-die PHY macro)' if e['tt'] == e['ff'] else '')
            size[c] = lef_size(vd / f'{c}.lef')
        else:
            sd = a.views / 'synth' / c
            libs = {k: sd / f"{e['wrapper']}_synth_{k}.lib" for k in ('tt', 'ff')}
            if not all(p.exists() for p in libs.values()):
                excluded[c] = 'SYNTH view not built (see VIEWS/drive/<cell>.json)'
                continue
            for k, p in libs.items():
                t = p.read_text().replace(e['wrapper'], c)
                (vd / f'{c}_{k}.lib').write_text(t)
            ecap[c] = [entry_cap(vd / f'{c}_{k}.lib') for k in ('tt', 'ff')]
            kinds[c] = 'SYNTH'
        for n in e['instances']:
            cell_of[n] = c
    inst = [n for n in I if n in cell_of]
    out_inst = sorted(set(I) - set(inst))
    ports = {c: {p: v['bits'] for p, v in I[V[c]['representative']]['ports'].items()} for c in kinds}
    dirs = {c: {p: v['direction'] for p, v in I[V[c]['representative']]['ports'].items()} for c in kinds}
    for c in kinds:     # view ports must equal the contract ports (REAL checked in v16_views; SYNTH = wrapper ports)
        lp = ports_of_lib(vd / f'{c}_tt.lib')
        bad = {p: (lp.get(p, (None, 0))[1], w) for p, w in ports[c].items() if lp.get(p, (None, 0))[1] != w}
        assert not bad or kinds[c].startswith('REAL'), (c, list(bad.items())[:5])

    # ---------------- outlines of SYNTH cells ----------------
    slot_users = defaultdict(list)
    for n in inst:
        s = I[n].get('slot')
        if s in slots:
            slot_users[s].append(n)
    flags = {}
    kit = json.loads((ROOT / 'physical/ref_tile/hdie_pc_ctrl/floorplan.json').read_text())
    for c in kinds:
        if kinds[c] != 'SYNTH':
            continue
        bits = sum(ports[c].values())
        e = V[c]
        sl = [slots[I[n]['slot']]['outline'] for n in e['instances'] if I[n].get('slot') in slots and len(slot_users[I[n]['slot']]) == 1]
        if e['master'] == CTL_M:
            w, h = kit['die'][2], kit['die'][3]; why = 'pc_ctrl kit outline (physical/ref_tile/hdie_pc_ctrl)'
        elif e['master'] == SVG_M:
            w, h = 1036.8, 228.96; why = 'service group box (d2 feed_wh)'
        elif sl and len(sl) == len(e['instances']) and len({(o['w'], o['h']) for o in sl}) == 1:
            w, h = sl[0]['w'], sl[0]['h']; why = 'grant slot outline'
        else:
            meta = json.loads((a.views / 'synth' / c / 'meta.json').read_text())
            A = meta['std_area_um2'] / 0.60 + 1.3 * sum(n_ * mw * mh for n_, mw, mh in meta['macros'].values())
            big = max([max(mw, mh) for n_, mw, mh in meta['macros'].values()] or [0])
            s_ = max(math.sqrt(A), big + 2 * HALO, 21.6)
            w, h = s_, s_; why = f"area {meta['std_area_um2']:.0f} um2 std / 0.60 + 1.3 x macros"
        need = bits * 0.048 * 1.5 / 0.9           # perimeter (um) for one track per bit + 50 % margin (faces fill unevenly: pins face their peers)
        if 2 * (w + h) < need:
            k = need / (2 * (w + h)); w, h = w * k, h * k
            why += f'; PIN-BOUND grown x{k:.2f} ({bits} bits)'
            flags[c] = 'pin_bound'
        size[c] = (snap(w, 0.216), snap(h, 1.08))
        kinds[c] = f'SYNTH ({why})'

    # ---------------- placement ----------------
    occ = Occ(W, H)
    pl, homes = {}, {}

    def put(n, x, y, o='R0', rule='', halo=0.0):
        w, h = size[cell_of[n]]
        if o in ('R90', 'R270'):
            w, h = h, w
        pl[n] = dict(m=cell_of[n], x=round(x, 3), y=round(y, 3), o=o, w=w, h=h, rule=rule)
        occ.mark(x, y, w, h, halo)

    def put_near(n, cx, cy, rule, region=None, halo=HALO):
        w, h = size[cell_of[n]]
        r = occ.find(cx, cy, w, h, halo, region) if region else None
        tag = rule
        if r is None:
            r = occ.find(cx, cy, w, h, halo)
            if region:
                tag = rule + ' OVERFLOW(region full)'
        if r is None:
            raise SystemExit(f'no free area for {n} ({w}x{h})')
        put(n, r[0], r[1], 'R0', tag, halo)
        homes[n] = dict(rule=tag, target=[round(cx, 1), round(cy, 1)], at=[r[0], r[1]],
                        dist_um=round(abs(r[0] + w / 2 - cx) + abs(r[1] + h / 2 - cy), 1))

    # 1a PHY + controllers + service groups (d2 rule)
    phy_xy = lef_xy(vd / f'{cell_of["phy_SW"]}.lef')
    per = [('row_v', 1), ('row_op', 3), ('row_bank', 5), ('row_row', 19), ('col_v', 1), ('col_we', 1), ('col_bank', 5),
           ('col_col', 5), ('col_data', 256), ('col_strb', 32), ('dram_rvalid', 1), ('dram_rdata', 256)]
    for q in Q:
        s = slots[f'phy_{q}']; b = P[f'phy_{q}']
        north = b['y'] > H / 2; east = b['x'] > W / 2
        po = ('R180' if east else 'MX') if north else ('MY' if east else 'R0')
        put(f'phy_{q}', b['x'], b['y'], po, 'PHY grant/plan')
        cw, ch = size[cell_of[f'ctl_{q}_p00']] if f'ctl_{q}_p00' in cell_of else (0, 0)
        for pc in range(32):
            n = f'ctl_{q}_p{pc:02d}'
            if n not in cell_of:
                continue
            xs = [phy_xy[f'{nn}[{pc * w + k}]'][0] for nn, w in per for k in range(w) if f'{nn}[{pc * w + k}]' in phy_xy]
            mx = sum(xs) / len(xs)
            cx = b['x'] + (b['w'] - mx if po in ('MY', 'R180') else mx)
            y = round(b['y'] - 10.8 - ch, 3) if north else round(b['y'] + b['h'] + 10.8, 3)
            put(n, round(round((cx - cw / 2) / 0.216) * 0.216, 3), y, 'MX' if north else 'R0', 'over its PHY channel (d2)')
        for k in range(8):
            n = f'svg_{q}{k}'
            if n not in cell_of:
                continue
            box = P[f'pc_{q}{k}']; fw, fh = size[cell_of[n]]
            gx = round(round((box['x'] + (box['w'] - fw) / 2) / 0.216) * 0.216, 3)
            gy = round(box['y'] + 4.32, 3) if north else round(box['y'] + box['h'] - fh - 4.32, 3)
            put(n, gx, gy, 'MX' if north else 'R0', 'PC band box (d2)')
    # 1b singleton grant slots (a v15 slot left at the die origin is a placeholder, not a home)
    placeholder = sorted((n, I[n]['slot']) for n in inst if I[n].get('slot') in slots and
                         slots[I[n]['slot']]['origin']['x'] < 100 and slots[I[n]['slot']]['origin']['y'] < 100)
    ph = {n for n, _ in placeholder}
    for s, users in sorted(slot_users.items()):
        if len(users) != 1 or users[0] in pl or users[0] in ph:
            continue
        n = users[0]; sl = slots[s]
        put(n, sl['origin']['x'], sl['origin']['y'], sl['origin'].get('orient', 'R0'), f'grant slot {s}')
    # 2 shared grant slots / plan regions
    for n in inst:
        if n in pl:
            continue
        s = I[n].get('slot')
        if n in ph:
            continue
        if s in slots:
            sl = slots[s]; x0, y0 = sl['origin']['x'], sl['origin']['y']
            reg = (x0, y0, x0 + sl['outline']['w'], y0 + sl['outline']['h'])
        elif s in P and isinstance(P[s], dict):
            b = P[s]; reg = (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])
        else:
            continue
        put_near(n, (reg[0] + reg[2]) / 2, (reg[1] + reg[3]) / 2, f'region {s}', region=reg, halo=0.0)
    # 3 relays with planned homes
    for n in inst:
        if n in pl:
            continue
        m = re.search(r'home \(([\d.]+), ([\d.]+)\) um', I[n].get('note', ''))
        if m:
            w, h = size[cell_of[n]]
            put_near(n, float(m.group(1)) + w / 2, float(m.group(2)) + h / 2, 'planned relay home', halo=0.0)
    # connectivity (instance level, bits)
    adj = defaultdict(lambda: defaultdict(int))
    for e in C['edges']:
        s_, t_ = e['source'][0], e['sink'][0]
        if s_ in cell_of and t_ in cell_of and s_ != t_:
            adj[s_][t_] += e['bits']; adj[t_][s_] += e['bits']

    def centre(n):
        v = pl[n]; return v['x'] + v['w'] / 2, v['y'] + v['h'] / 2
    is_rly = lambda n: I[n]['master'].startswith('hbfd_rly')
    # 4 remaining blocks by connectivity: compact660_v5 plan blocks are reserved for their owners, so a generated home
    # goes to free die area outside every plan block (corner voids beside the LK/EP column, channels) -- never squeezed
    # into a band (H-DIE 01:30 request)
    occ_res = Occ(W, H)
    occ_res.g = occ.g.copy()
    for k_, b in P.items():
        if isinstance(b, dict) and 'x' in b:
            occ_res.mark(b['x'], b['y'], b['w'], b['h'])
    # band strips (bounding box of every band block per half) are reserved for blocks >= 0.1 mm2: those go to the
    # corner voids beside the PHYs / LK-EP column (H-DIE 01:30), not into band gaps
    occ_big = Occ(W, H); occ_big.g = occ_res.g.copy()
    band = [b for k_, b in P.items() if isinstance(b, dict) and 'x' in b and k_.split('_')[0] in
            ('su', 'sucore', 'vmb', 'vmh', 'hc', 'sfu', 'coll', 'dbk', 'quant')]
    for half in (lambda b: b['y'] < H / 2, lambda b: b['y'] >= H / 2):
        bb = [b for b in band if half(b)]
        if bb:
            x0 = min(b['x'] for b in bb); y0 = min(b['y'] for b in bb)
            occ_big.mark(x0, y0, max(b['x'] + b['w'] for b in bb) - x0, max(b['y'] + b['h'] for b in bb) - y0)
    todo = [n for n in inst if n not in pl and not is_rly(n)]
    while todo:
        def score(n):
            return sum(b for p, b in adj[n].items() if p in pl)
        todo.sort(key=score, reverse=True)
        n = todo.pop(0)
        s = I[n].get('slot')
        if s in pl:
            cx, cy = centre(s); rule = f'next to {s} (slot names an instance)'
        else:
            pk = [(p, b) for p, b in adj[n].items() if p in pl]
            if pk:
                tb = sum(b for _, b in pk); t2 = sum(b * b for _, b in pk)   # bits^2: the data peer, not the config fan-in
                cx = sum(centre(p)[0] * b * b for p, b in pk) / t2; cy = sum(centre(p)[1] * b * b for p, b in pk) / t2
                rule = f'centroid of {len(pk)} placed peers ({tb} b, bits^2 weighted)'
            else:
                cx, cy = W / 2, H / 2; rule = 'no placed peer: die centre'
        w_, h_ = size[cell_of[n]]
        own = [k_ for pat, f_ in OWNER for k_ in [None] if re.fullmatch(pat, n)
               for k_ in P if isinstance(P[k_], dict) and 'x' in P[k_] and re.fullmatch(f_(re.fullmatch(pat, n)), k_)]
        if own:   # the plan blocks reserved for this instance's function: nearest free fit inside one of them
            best = None
            for k_ in own:
                b = P[k_]; r = occ.find(cx, cy, w_, h_, 0.0, (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
                if r and (best is None or abs(r[0] - cx) + abs(r[1] - cy) < best[0]):
                    best = (abs(r[0] - cx) + abs(r[1] - cy), r, k_)
            if best:
                put(n, best[1][0], best[1][1], 'R0', f'owner plan block {best[2]}', 0.0)
                occ_res.mark(best[1][0], best[1][1], w_, h_); occ_big.mark(best[1][0], best[1][1], w_, h_)
                homes[n] = dict(rule=f'owner plan block {best[2]}', target=[round(cx, 1), round(cy, 1)], at=list(best[1]))
                continue
            rule += f' OWNER-BLOCK MISFIT ({w_:.0f}x{h_:.0f} fits none of {own[:3]}...)'
            r = occ_res.find(cx, cy, w_, h_, HALO)
            if r is not None:
                put(n, r[0], r[1], 'R0', rule, HALO); occ_res.mark(r[0], r[1], w_, h_, HALO); occ_big.mark(r[0], r[1], w_, h_, HALO)
                homes[n] = dict(rule=rule, target=[round(cx, 1), round(cy, 1)], at=list(r),
                                dist_um=round(abs(r[0] + w_ / 2 - cx) + abs(r[1] + h_ / 2 - cy), 1))
                continue
        w_, h_ = size[cell_of[n]]
        big = w_ * h_ >= 1e5
        r = (occ_big if big else occ_res).find(cx, cy, w_, h_, HALO)
        if big and r is not None:
            rule += ' (>= 0.1 mm2: outside the band strips)'
        if r is None:
            put_near(n, cx, cy, rule + ' (no free area outside plan blocks)')
            v_ = pl[n]; occ_res.mark(v_['x'], v_['y'], v_['w'], v_['h'], HALO); occ_big.mark(v_['x'], v_['y'], v_['w'], v_['h'], HALO)
        else:
            put(n, r[0], r[1], 'R0', rule + ' -> outside plan blocks', HALO)
            occ_res.mark(r[0], r[1], w_, h_, HALO); occ_big.mark(r[0], r[1], w_, h_, HALO)
            homes[n] = dict(rule=rule + ' -> outside plan blocks', target=[round(cx, 1), round(cy, 1)], at=list(r),
                            dist_um=round(abs(r[0] + w_ / 2 - cx) + abs(r[1] + h_ / 2 - cy), 1))
    # 5 relay chains without homes
    succ, pred = {}, {}
    for e in C['edges']:
        s_, t_ = e['source'][0], e['sink'][0]
        if t_ in cell_of and is_rly(t_) and e['sink'][1] == 'i':
            pred[t_] = s_
        if s_ in cell_of and is_rly(s_) and e['source'][1] == 'o':
            succ[s_] = t_
    left = [n for n in inst if n not in pl]
    done = set()
    for n in left:
        if n in done:
            continue
        head = n
        while pred.get(head) in left and pred[head] not in done and pred[head] != n:
            head = pred[head]
        chain = [head]
        while succ.get(chain[-1]) in left and succ[chain[-1]] not in chain:
            chain.append(succ[chain[-1]])
        done.update(chain)
        a_ = pred.get(chain[0]); b_ = succ.get(chain[-1])
        p0 = centre(a_) if a_ in pl else None; p1 = centre(b_) if b_ in pl else None
        p0 = p0 or p1 or (W / 2, H / 2); p1 = p1 or p0
        blk = lambda xy: next((k for k, v in P.items() if isinstance(v, dict) and 'x' in v and v['x'] <= xy[0] <= v['x'] + v['w']
                               and v['y'] <= xy[1] <= v['y'] + v['h']), None)
        ba, bb = blk(p0), blk(p1)
        lane = next((v for k, v in lanes.items() if ba and bb and k.startswith(f'{ba}>{bb}:')), {})
        if 'v' in lane:
            path = [p0, (lane['v'], p0[1]), (lane['v'], p1[1]), p1]
        elif 'h' in lane:
            path = [p0, (p0[0], lane['h']), (p1[0], lane['h']), p1]
        else:
            path = [p0, (p1[0], p0[1]), p1]
        seg = [abs(path[i + 1][0] - path[i][0]) + abs(path[i + 1][1] - path[i][1]) for i in range(len(path) - 1)]
        L = sum(seg) or 1.0
        for r, rn in enumerate(chain):
            t = L * (r + 1) / (len(chain) + 1); i = 0
            while i < len(seg) - 1 and t > seg[i]:
                t -= seg[i]; i += 1
            (x0, y0), (x1, y1) = path[i], path[i + 1]
            f = t / seg[i] if seg[i] else 0
            put_near(rn, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f,
                     f"relay chain {chain[0]}..{chain[-1]} ({len(chain)}) between {a_} and {b_}, lane {lane or 'L'}", halo=0.0)
    assert all(n in pl for n in inst)
    # overlap + outline check
    bad = []
    items = sorted(pl.items(), key=lambda kv: kv[1]['x'])
    for i, (l1, v1) in enumerate(items):
        if v1['x'] < -0.01 or v1['y'] < -0.01 or v1['x'] + v1['w'] > W + 0.01 or v1['y'] + v1['h'] > H + 0.01:
            bad.append(('outside', l1))
        for l2, v2 in items[i + 1:]:
            if v2['x'] >= v1['x'] + v1['w'] - 0.01:
                break
            if v1['y'] < v2['y'] + v2['h'] - 0.01 and v2['y'] < v1['y'] + v1['h'] - 0.01:
                bad.append(('overlap', l1, l2))
    print('placement problems', len(bad), bad[:10])

    # ---------------- nets ----------------
    nets = {}            # driver pin key -> [driver, loads...]
    used = defaultdict(set)
    dropped = defaultdict(int)
    for e in C['edges']:
        (si, sp, slo, sw), (ti, tp, tlo, tw) = e['source'], e['sink']
        if si not in cell_of or ti not in cell_of:
            dropped[('excluded_end', e['source'][0] if si not in cell_of else ti)] += e['bits']
            continue
        sb, tb = ports[cell_of[si]][sp], ports[cell_of[ti]][tp]
        for k in range(e['bits']):
            d = (si, pin(sp, sb, slo + k)); l = (ti, pin(tp, tb, tlo + k))
            nets.setdefault(d, [d]).append(l)
            used[si].add(d[1]); used[ti].add(l[1])
    die_ports = []
    for dp in C['die_pins']:
        if dp['instance'] not in cell_of:
            continue
        b = ports[cell_of[dp['instance']]][dp['port']]
        for k in range(dp['bits']):
            pn = pin(dp['port'], b, k)
            die_ports.append((f"{dp['name']}" + (f'[{k}]' if dp['bits'] > 1 else ''), dp['direction'], dp['instance'], pn))
            used[dp['instance']].add(pn)
    # clocks / resets
    clk = defaultdict(lambda: defaultdict(list)); rst = defaultdict(list)
    for r in C['clock_resets']:
        n = r['instance']
        if n not in cell_of:
            continue
        b = ports[cell_of[n]][r['port']]
        pins_ = [pin(r['port'], b, k) for k in range(r['bits'])]
        if r['kind'] == 'clock':
            clk[r['domain']][n] += pins_
        else:
            rst[r['domain']] += [(n, p) for p in pins_]
        used[n].update(pins_)

    # ---------------- SYNTH abstracts (pin faces toward peers) ----------------
    peer_xy = defaultdict(list)   # (inst, port) -> [(x, y, bits)]
    for d, ends in nets.items():
        dx, dy = centre(d[0])
        for l in ends[1:]:
            lx, ly = centre(l[0])
            peer_xy[(d[0], re.sub(r'\[\d+\]$', '', d[1]))].append((lx, ly))
            peer_xy[(l[0], re.sub(r'\[\d+\]$', '', l[1]))].append((dx, dy))
    face_report = {}
    for c in kinds:
        if not kinds[c].startswith('SYNTH'):
            continue
        rep = next(n for n in V[c]['instances'] if n in pl)
        v = pl[rep]; w, h = size[c]; cx, cy = centre(rep)
        cap = {f: 0.9 * (w if f in 'NS' else h) / 0.048 for f in 'NSEW'}
        want = {}
        clockish = set(p for d_ in clk.values() for p in [re.sub(r'\[\d+\]$', '', x) for x in d_.get(rep, [])])
        for p, b in ports[c].items():
            pts = peer_xy.get((rep, p))
            if not pts:
                want[p] = (['S', 'W', 'N', 'E'] if p in clockish else ['W', 'E', 'N', 'S'], 0.0, b)
                continue
            px = sum(x for x, _ in pts) / len(pts) - cx; py = sum(y for _, y in pts) / len(pts) - cy
            if v['o'] in ('MY', 'R180'):
                px = -px
            if v['o'] in ('MX', 'R180'):
                py = -py
            sc = {'E': px / w, 'W': -px / w, 'N': py / h, 'S': -py / h}
            order = sorted(sc, key=lambda f: -sc[f])
            along = (px if order[0] in 'NS' else py)
            want[p] = (order, along, b)
        faces = {f: [] for f in 'NSEW'}; usedc = {f: 0 for f in 'NSEW'}
        for p, (order, along, b) in sorted(want.items(), key=lambda kv: -kv[1][2]):
            base, left = 0, b      # a bus that does not fit its preferred face continues on the next face (bit slices)
            for f in order + [max(usedc, key=lambda f: cap[f] - usedc[f])]:
                room = int(cap[f] - usedc[f])
                if room <= 0:
                    continue
                k = min(room, left)
                faces[f].append((along, p, base, k)); usedc[f] += k; base += k; left -= k
                if not left:
                    break
            if left:
                raise SystemExit(f'{c}: pins do not fit ({b} b of {p})')
            if base != b or len([1 for f in faces for x in faces[f] if x[1] == p]) > 1:
                flags.setdefault(c, 'bus_split_over_faces')
        pinlist = []
        for f, L in faces.items():
            if not L:
                continue
            Lf = w if f in 'NS' else h
            tot = sum(k for _, _, _, k in L)
            step = max(0.048, (0.9 * Lf) / max(tot, 1))
            x = 0.05 * Lf
            for _, p, base, k in sorted(L):
                pinlist.append((p, dirs[c][p], f, x, x + k * step, k, base, ports[c][p] > 1)); x += k * step
        fp = {f: L for f, L in faces.items() if L}
        synth_lef(c, w, h, pinlist, vd / f'{c}.lef')
        face_report[c] = {f: sum(x[3] for x in L) for f, L in fp.items()}

    vpins = {c: lef_pins(vd / f'{c}.lef') for c in kinds}
    vxy = {c: lef_xy(vd / f'{c}.lef') for c in kinds}
    exposed = C.get('exposed_inputs', {})
    manifest = dict(schema='opentallas.hbm_v16.die_case.v1',
                    label=f"NOT_A_DIE_RESULT (source contract has {exposed.get('ports', 'unknown')} exposed "
                          f"input ports / {exposed.get('bits', 'unknown')} b; SYNTH views are estimates; "
                          'full native/physical qualification remains OPEN)', die_um=[W, H], contract=str(a.contract),
                    plan=str(a.plan), grants=str(a.grants), lanes=str(a.lanes), views=kinds, flags=flags,
                    excluded_cells=excluded, excluded_instances=out_inst,
                    instances={c: sum(1 for n in inst if cell_of[n] == c) for c in kinds},
                    homes=homes, placeholder_slots_ignored=placeholder, placement_problems=bad, face_bits=face_report,
                    dropped_edge_bits={f'{k[0]}:{k[1]}': v for k, v in dropped.items()},
                    signal_nets=len(nets), die_ports=len(die_ports),
                    synth_clock_entry=dict(rule='SYNTH ETM clock pins re-capped to one 2 fF entry buffer', pins_recapped=ecap),
                    placement=pl, corners='setup TT, hold FF (owner option B); SS not run')
    # Pin the actual consumed bytes, including generated abstracts and recapped SYNTH ETMs.
    # A source path alone cannot establish lineage after another branch changes a view.
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    manifest['input_sha256'] = {name: digest(path) for name, path in
                                [('contract', a.contract), ('plan', a.plan), ('grants', a.grants),
                                 ('lanes', a.lanes), ('view_inventory', a.views / 'views.json'),
                                 ('generator', Path(__file__))]}
    manifest['consumed_view_sha256'] = {p.name: digest(p) for p in sorted(vd.iterdir())
                                        if p.suffix in ('.lef', '.lib')}
    manifest['native_complete'] = False
    render(out, manifest, P, W, H)
    if a.no_clock:
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=1))
        print(json.dumps(dict(insts=len(inst), nets=len(nets), excluded=len(excluded), homes=len(homes), problems=len(bad))))
        return

    # ---------------- die clock trees ----------------
    ck = slots[CKGEN]
    obs = [(v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h']) for n, v in pl.items()]   # every hard outline (relays too)
    quad = {n: ('N' if centre(n)[1] > H / 2 else 'S') + ('E' if centre(n)[0] > W / 2 else 'W') for n in inst}
    trees = {}
    for di, (dom, insts) in enumerate(sorted(clk.items())):
        rx = ck['origin']['x'] + ck['outline']['w'] * (0.2 + 0.3 * di); ry = ck['origin']['y'] + ck['outline']['h'] / 2
        sinks = []
        for n, pl_ in insts.items():
            v = pl[n]; p0 = sorted(pl_)[0]
            px, py = vxy[cell_of[n]].get(p0, (v['w'] / 2, v['h'] / 2))
            x, y = rect_of(v['x'], v['y'], v['w'], v['h'], v['o'], px, py)
            sinks.append((n, p0, x, y))
        mode = dict(kv.split('=') for kv in a.clock_mode.split(',')).get(dom, 'htree')
        t = dct.build(W, H, obs, (rx, ry), sinks, lambda n: quad[n], mode=mode, bin_um=a.clock_bin_um)
        inside = [b for b in t['buffers'] if any(o[0] < b[2] < o[2] and o[1] < b[3] < o[3] for o in obs)]
        assert not inside, (dom, len(inside), inside[:3])   # H-DIE 02:20: no die clock buffer inside any hard outline
        pre = {'hbm': 'dkh', 'stream': 'dks', 'serial': 'dkr'}[dom]
        ren = lambda s, pre=pre: s.replace('dck_', pre + '_')
        port = f'clk_{dom}'
        bufs = [(ren(b), c_, x, y) for b, c_, x, y in t['buffers']]
        tnets = []
        for nn, d, loads in t['nets']:
            d2 = ('port', port) if d[0] == 'port' else (d[0], ren(d[1]))
            l2 = []
            for ld in loads:
                if ld[0] == 'pin':
                    l2 += [('pin', ld[1], p) for p in insts[ld[1]]]
                else:
                    l2.append((ld[0], ren(ld[1])))
            tnets.append((ren(nn), d2, l2))
        trees[dom] = dict(buffers=bufs, nets=tnets, model=t['model'], port=port)
        print('clock', dom, 'sinks', len(sinks), 'buffers', len(bufs), flush=True)

    render(out, manifest, P, W, H, trees)
    # ---------------- die.v ----------------
    netname = {}
    for i_, (d, ends) in enumerate(sorted(nets.items())):
        nm = f'n{i_}'
        for e_ in ends:
            netname[e_] = nm
    for nm_port, dr, n, p in die_ports:
        netname[(n, p)] = 'p_' + re.sub(r'\W', '_', nm_port)
    leafclk = {}
    tw, tb = [], []
    for dom, t in trees.items():
        first = [nn for nn, d, _ in t['nets'] if d == ('port', t['port'])]
        assert len(first) == 1
        ren_net = lambda nn, f=first[0], pt=t['port']: pt if nn == f else nn
        drv, inp = {}, {}
        for nn, d, loads in t['nets']:
            if d[0] == 'buf':
                drv[d[1]] = ren_net(nn)
            for ld in loads:
                if ld[0] == 'buf':
                    inp[ld[1]] = ren_net(nn)
                else:
                    leafclk[(ld[1], ld[2])] = ren_net(nn)
            if nn != first[0]:
                tw.append(f'  wire {nn};')
        for b, cell_, x, y in t['buffers']:
            tb.append(f'  {cell_} {b} (.A({inp[b]}), .Y({drv.get(b, b + "_nc")}));')
            if b not in drv:
                tw.append(f'  wire {b}_nc;')
    for dom, lst in rst.items():
        for (n, p) in lst:
            leafclk[(n, p)] = f'rst_{dom}'
    nc = []
    body = []
    for n in sorted(inst):
        c = cell_of[n]
        bus = defaultdict(dict); scal = []
        for p in vpins[c]:
            if p in ('VDD', 'VSS'):
                continue
            net_ = leafclk.get((n, p)) or netname.get((n, p))
            mm = re.fullmatch(r'(\w+)\[(\d+)\]', p)
            if mm:
                bus[mm.group(1)][int(mm.group(2))] = net_
            elif net_:
                scal.append((p, net_))
        cs = [f'.{p}({nn})' for p, nn in sorted(scal)]
        for p, bits in sorted(bus.items()):
            wv = 1 + max(bits)
            parts = []
            for k in range(wv - 1, -1, -1):
                if bits.get(k):
                    parts.append(bits[k])
                else:
                    nn = f'nc_{n}_{p}_{k}'; nc.append(nn); parts.append(nn)
            cs.append(f'.{p}({{{", ".join(parts)}}})')
        body.append(f'  {c} {n} (\n    ' + ',\n    '.join(cs) + '\n  );')
    hdr = [f'input wire clk_{d}' for d in trees] + [f'input wire rst_{d}' for d in rst]
    for nm_port, dr, n, p in die_ports:
        hdr.append(f"{'input' if dr == 'input' else 'output'} wire {netname[(n, p)]}")
    L = ['// H-DIE v16 full-die case (tools/hbm_die_v15/die_case_v16.py); NOT_A_DIE_RESULT; open pins listed in manifest',
         'module hbm_v16_die (' + ', '.join(hdr) + ');']
    allnets = sorted(set(netname[e_] for d, ends in nets.items() for e_ in ends) - set(netname[(n, p)] for _, _, n, p in die_ports))
    L += [f'  wire {x};' for x in allnets] + [f'  wire {x};' for x in nc] + tw + body + tb + ['endmodule']
    (out / 'die.v').write_text('\n'.join(L) + '\n')

    # ---------------- run.tcl / run.sh ----------------
    plat = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    p_ = 9.6 / 15.0
    plc = [f'place_inst -name {n} -location {{{v["x"]:.3f} {v["y"]:.3f}}} -orientation {v["o"]} -status FIRM' for n, v in sorted(pl.items())]
    for t in trees.values():
        plc += [f'place_inst -name {b} -location {{{x:.3f} {y:.3f}}} -orientation R0 -status FIRM' for b, c_, x, y in t['buffers']]
    cks = '\n'.join(f'place_pin -pin_name clk_{d} -layer M9 -location {{{ck["origin"]["x"] + ck["outline"]["w"] * (0.2 + 0.3 * i):.3f} '
                    f'{ck["origin"]["y"] + ck["outline"]["h"] / 2:.3f}}} -pin_size {{0.4 0.4}}' for i, d in enumerate(sorted(trees)))
    clocks = '\n'.join(f'create_clock -name {d} -period {PERIOD[d]} [get_ports clk_{d}]' for d in sorted(trees))
    groups = 'set_clock_groups -asynchronous ' + ' '.join(f'-group {d}' for d in sorted(trees))
    cells = sorted(kinds)
    tcl = f'''# H-DIE v16 full-die GRT + TT/FF STA (generated by tools/hbm_die_v15/die_case_v16.py) -- NOT_A_DIE_RESULT
read_lef {plat}/lef/asap7_tech_1x_201209.lef
read_lef {plat}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{chr(10).join(f'read_lef /work/views/{c}.lef' for c in cells)}
define_corners tt ff
{chr(10).join(f'read_liberty -corner {k} /work/views/{c}_{k}.lib' for c in cells for k in ('tt', 'ff'))}
{chr(10).join(f'read_liberty -corner {k} {plat}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{k.upper()}_nldm_220122.lib.gz' for k in ('tt', 'ff'))}
read_verilog /work/die.v
link_design hbm_v16_die
initialize_floorplan -die_area {{0 0 {W} {H}}} -core_area {{0 0 {W} {H}}} -site asap7sc7p5t
make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064
make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048
make_tracks M3 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.009 -y_pitch {p_:.3f}
make_tracks M2 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.045 -y_pitch {p_:.3f}
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
{chr(10).join(plc)}
{cks}
place_pins -hor_layers M4 -ver_layers M5 -min_distance 2
source {plat}/setRC.tcl
set blk [ord::get_db_block]
foreach n [$blk getNets] {{ if {{[string match dk?_* [$n getName]] || [string match n_dk?_* [$n getName]] || [string match clk_* [$n getName]]}} {{ $n setSigType CLOCK }} }}
set_wire_rc -clock -layer M8
set_wire_rc -signal -layer M6
set_routing_layers -signal M4-M9 -clock M7-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
{{REPEAT}}
set t0 [clock seconds]
global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
write_db /work/out/grt.odb
estimate_parasitics -global_routing
{clocks}
{groups}
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_*]
proc dump {{corner kind fn}} {{
  set f [open $fn w]
  set n 0
  foreach pe [find_timing_paths -corner $corner -path_delay $kind -group_path_count {a.paths} -endpoint_path_count 1 -slack_max 1e9 -sort_by_slack] {{
    set sp [get_full_name [get_property $pe startpoint]]
    set ep [get_full_name [get_property $pe endpoint]]
    puts $f "$sp $ep [get_property $pe slack]"
    incr n
  }}
  close $f
  puts "OT_PATHS $corner $kind $n"
}}
foreach {{c k}} {{tt max ff min}} {{
  report_checks -corner $c -path_delay $k -group_path_count 5 -format full_clock_expanded -fields {{slew cap input_pins nets fanout}} > /work/out/worst_${{c}}_${{k}}.rpt
  dump $c $k /work/out/paths_${{c}}_${{k}}.txt
}}
report_tns
report_clock_skew -setup > /work/out/clock_skew.rpt
report_clock_skew -hold >> /work/out/clock_skew.rpt
puts OT_DONE
'''
    rep_ = '' if not a.die_repeaters else f'''{clocks}
{groups}
estimate_parasitics -placement
set_dont_touch [get_nets -quiet {{dk?_* n_dk?_* clk_* rst_*}}]
set r0 [clock seconds]
repair_design -max_wire_length 400 -buffer_gain 4.0
puts "OT_REPAIR_S [expr {{[clock seconds]-$r0}}] insts [llength [get_cells *]]"'''
    (out / 'run.tcl').write_text(tcl.replace('{REPEAT}', rep_))
    (out / 'run.sh').write_text('''#!/bin/bash
# OpenROAD in the pinned ORFS image; writes out/run.log, out/run.exit
D=$(cd $(dirname $0) && pwd); N=hdie-v16case-$$
docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-256}g -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/run.tcl > /work/out/run.log 2>&1; rc=\\$?; chmod -R a+rwX /work/out; exit \\$rc"
echo $? > $D/out/run.exit
''')
    open_pins = defaultdict(lambda: defaultdict(int))
    for n in inst:
        for p in vpins[cell_of[n]]:
            if p not in used[n] and p not in ('VDD', 'VSS'):
                open_pins[cell_of[n]][re.sub(r'\[\d+\]$', '', p)] += 1
    manifest.update(open_pins_by_cell={c: dict(v) for c, v in open_pins.items()},
                    exposed_inputs_owner=C.get('exposed_inputs'), straps_open=len(C.get('straps', [])),
                    clock_domains={d: dict(period_ps=PERIOD[d], sink_insts=len(clk[d]), sink_pins=sum(len(x) for x in clk[d].values()))
                                   for d in clk},
                    die_clock_trees={d: t['model'] for d, t in trees.items()},
                    reset='die ports rst_<domain> straight to every reset pin (false path; distribution not modelled)')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1, default=str))
    print(json.dumps(dict(insts=len(inst), nets=len(nets), excluded=len(excluded), homes=len(homes), problems=len(bad),
                          clock={d: len(t['buffers']) for d, t in trees.items()})))


def render(out, man, P, W, H, trees=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(18, 12.5))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for n, b in P.items():
        if isinstance(b, dict) and 'x' in b:
            ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], fill=False, lw=0.3, ls='--', color='0.5'))
    col = lambda v: ('tab:green' if v['m'].startswith('hbfd_rly') else
                     'tab:gray' if 'phy' in v['m'] else
                     'tab:red' if 'OVERFLOW' in v['rule'] else
                     'tab:purple' if v['rule'].startswith(('centroid', 'next to', 'no placed')) else
                     'tab:blue' if man['views'].get(v['m'], '').startswith('REAL') else 'tab:orange')
    for n, v in man['placement'].items():
        ax.add_patch(Rectangle((v['x'], v['y']), v['w'], v['h'], color=col(v), alpha=0.6, lw=0.2))
        if v['w'] * v['h'] > 1.5e5:
            ax.text(v['x'] + 10, v['y'] + 10, n, fontsize=4)
    for dom, t in (trees or {}).items():
        xs = [b[2] for b in t['buffers']]; ys = [b[3] for b in t['buffers']]
        ax.plot(xs, ys, '.', ms=0.8, color={'hbm': 'magenta', 'stream': 'cyan', 'serial': 'olive'}.get(dom, 'k'),
                label=f'{dom} clock buffers ({len(xs)})')
    for k, c in [('REAL view', 'tab:blue'), ('SYNTH view (slot/plan)', 'tab:orange'), ('generated home (peer centroid)', 'tab:purple'),
                 ('region overflow (slot misfit)', 'tab:red'), ('relay', 'tab:green'), ('PHY', 'tab:gray')]:
        ax.plot([], [], 's', color=c, label=k)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal'); ax.legend(loc='upper right', fontsize=7)
    ax.set_title(f"v16 full die case: {len(man['placement'])} instances, {man['signal_nets']} nets, excluded cells "
                 f"{len(man['excluded_cells'])}, placement problems {len(man['placement_problems'])}", fontsize=9)
    fig.savefig(out / 'layout.png', dpi=110, bbox_inches='tight')


if __name__ == '__main__':
    main()
