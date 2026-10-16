#!/usr/bin/env python3
"""Whole-die GRT + TT/FF STA case of the v15 HBM die over the HBM service engine and the SM array (H-DIE 2026-10-15 18:15).

    die_case.py --out CASE_DIR --ctrl-view DIR --feed-view DIR --sm-view DIR [--clock-pads JSON]

Composition (owner rule 10-14, all on-chip execution real hardware; only the PHY is modelled):
  phy_<q>            ot_hbm3e_phy_rc_e8p5       PHY-ONLY abstract (row/column/data boundary), plan block, pins face the die
  ctl_<q>_pNN  (128) ot_hbm_svc_pc_ctrl_leaf    REAL controller per PC (r14 sequencer + FIFO + response SRAM), over its
                                                PHY channel window (pcrow_rc placement of view_case.py)
  svg_<q><k>   (32)  ot_hbm_svc_sm_feed_programmed (LBANKS 4)  SM k's service group (landing/cache/programme SRAMs +
                                                four-PC producer), in PC band box pc_<q><k> above its four controllers
  sm_<q><k>    (32)  ot_hbm_accel_smh_static    SM tile at its v6 grant slot (outline, orient, pins = the grant)
Nets (bit exact, from the RTL of ot_hbm_svc_sm_stack_native/_programmed/_leaves): PHY <-> controller row/column/data per
PC; controller p <-> service group p//4 K port lane p%4; service group -> SM packet (1099) + command (83, sm_command).
Every other pin is OUT OF CASE (listed in manifest.json with its owner), never tied.
Views: each master's dir holds <master>.lef + <master>_{tt,ff}.lib.  A SYNTH view (mapped netlist ETM, ideal clocks, no
wires) gets a generated abstract (synth_lef): the real outline and the grant's pins (SM) or the kit's faces.
Clocks: two die domains from the hb_ckgen slot, each an explicit die tree (tools/hbm_die_v15/die_clock_tree.py, repeaters in
free area only): stream 833.333 ps (SM clk, group stream/bank clocks) and hbm 1024 ps (controller, PHY, group hbm/fifo/pc
clocks; HBM3E controller CK/2 = 1.024 ns, the r14 timing basis).  stream <-> hbm cross only inside the group's async FIFOs:
the domains are asynchronous (set_clock_groups), as the RTL.  Setup TT, hold FF, 60/25 ps uncertainty.
"""
import argparse, json, re, shutil, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from view_case import lef_pins, lef_xy  # noqa: E402
import die_clock_tree as dct  # noqa: E402

GRANTS = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
PLAN = ROOT / 'results/arch/hbm_die_v15/compact660_v5/compact.P.json'
PHY_M = 'ot_hbm3e_phy_rc_e8p5'
CTL_M = 'ot_hbm_svc_pc_ctrl_leaf'
SVG_M = 'ot_hbm_svc_sm_feed_programmed'
SM_M = 'ot_hbm_accel_smh_static'
PERIOD = dict(stream=833.333, hbm=1024.0)
TILE = 9.6
Q = ('SW', 'SE', 'NW', 'NE')


def ports_of_netlist(nl, top):
    """{port: (dir, width)} of module `top` in a yosys netlist (header + port declarations)."""
    t = Path(nl).read_text()
    m = re.search(r'\nmodule\s+\\?' + re.escape(top) + r'\s*\((.*?)\);(.*?)\nendmodule', t, re.S)
    assert m, (nl, top)
    out = {}
    for d, rng, name in re.findall(r'^\s*(input|output|inout)\s+(?:wire\s+)?(?:signed\s+)?(\[\d+:\d+\])?\s*\\?(\w+)\s*;',
                                   m.group(2), re.M):
        w = 1
        if rng:
            a, b = map(int, rng[1:-1].split(':'))
            w = abs(a - b) + 1
        out[name] = (d, w)
    return out


def ports_of_lib(lib):
    """{port: (dir, width)} from an ETM liberty (bus(...) / pin(...) at cell level)."""
    t = Path(lib).read_text()
    out = {}
    for m in re.finditer(r'\n\s*bus\s*\(\s*"?(\w+)"?\s*\)\s*\{(.*?)\n\s*bus_type\s*:\s*"?(\w+)"?', t, re.S):
        pass
    types = {m.group(1): abs(int(m.group(2)) - int(m.group(3))) + 1 for m in re.finditer(
        r'type\s*\(\s*"?(\w+)"?\s*\)\s*\{[^}]*?bit_from\s*:\s*(\d+)\s*;[^}]*?bit_to\s*:\s*(\d+)\s*;', t, re.S)}
    for m in re.finditer(r'\n\s*bus\s*\(\s*"?(\w+)"?\s*\)\s*\{\s*bus_type\s*:\s*"?(\w+)"?\s*;\s*direction\s*:\s*(\w+)', t):
        out[m.group(1)] = (m.group(3), types[m.group(2)])
    for m in re.finditer(r'\n\s*pin\s*\(\s*"?(\w+)"?\s*\)\s*\{\s*direction\s*:\s*(\w+)', t):
        if m.group(1) not in out:
            out[m.group(1)] = (m.group(2), 1)
    return out


def entry_cap(lib, ff=2.0):
    """SYNTH ETM (ideal clocks, no tile CTS): its clock pin carries the raw sum of every flop clock pin (e.g. 6.5 pF on the
    controller leaf).  A hardened tile presents one clock-entry buffer: model that (ff fF) so the die tree sees the entry
    it will drive.  The tile-internal insertion is NOT in a SYNTH view (labelled in the manifest)."""
    t = Path(lib).read_text()
    t2, n = re.subn(r'(pin\("?[\w\[\]]+"?\)\s*\{\s*direction\s*:\s*input\s*;\s*clock\s*:\s*true\s*;\s*capacitance\s*:\s*)[\d.]+',
                    lambda m: m.group(1) + f'{ff:.4f}', t)
    Path(lib).write_text(t2)
    return n


def synth_lef(name, w, h, pins, path):
    """Abstract of a SYNTH view: real outline, pins at the given (face, lo, hi) spans, every bit on a track (M5 N/S at
    x = 0.012 + 0.048 k, M4 E/W at y = 0.012 + 0.048 k), OBS M1..M5 (the die routes M6+ over it, M4/M5 in channels)."""
    L = ['VERSION 5.7 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f'MACRO {name}', '  CLASS BLOCK ;',
         f'  FOREIGN {name} 0 0 ;', f'  SIZE {w:.3f} BY {h:.3f} ;', '  SYMMETRY X Y ;']
    used = defaultdict(set)
    for (pn, d, face, lo, hi, nb, base, bus) in pins:
        ln = (hi - lo)
        for k in range(nb):
            pos = lo + (k + 0.5) * ln / nb
            tr = round((pos - 0.012) / 0.048)
            while tr in used[face]:
                tr += 1
            used[face].add(tr)
            c = 0.012 + 0.048 * tr
            bit = f'{pn}[{base + k}]' if bus else pn
            if face in ('N', 'S'):
                assert 0 < c < w, (name, pn, face, c, w)
                y0, y1 = (h - 0.192, h) if face == 'N' else (0, 0.192)
                r, lay = (c - 0.012, y0, c + 0.012, y1), 'M5'
            else:
                assert 0 < c < h, (name, pn, face, c, h)
                x0, x1 = (w - 0.192, w) if face == 'E' else (0, 0.192)
                r, lay = (x0, c - 0.012, x1, c + 0.012), 'M4'
            L += [f'  PIN {bit}', f'    DIRECTION {d.upper()} ;',
                  '    USE CLOCK ;' if re.search(r'clk', pn) else '    USE SIGNAL ;', '    PORT', f'      LAYER {lay} ;',
                  f'      RECT {r[0]:.3f} {r[1]:.3f} {r[2]:.3f} {r[3]:.3f} ;', '    END', f'  END {bit}']
    L += ['  OBS'] + [f'    LAYER M{k} ;\n    RECT 0 0 {w:.3f} {h:.3f} ;' for k in range(1, 6)] + ['  END', f'END {name}', '', 'END LIBRARY']
    Path(path).write_text('\n'.join(L) + '\n')


def face_pins(ports, faces, w, h):
    """pins for synth_lef from a {face: [port]} map: each face's ports packed over the middle 90 % of the face in order."""
    out = []
    for f, plist in faces.items():
        L = w if f in ('N', 'S') else h
        bits = sum(ports[p][1] for p in plist)
        step = (0.9 * L) / max(bits, 1)
        assert step >= 0.048, (f, bits, L)
        x = 0.05 * L
        for p in plist:
            d, nb = ports[p]
            out.append((p, d, f, x, x + nb * step, nb, 0, nb > 1))
            x += nb * step
    return out


def grant_pins(slot, ports):
    """pins for synth_lef from a v6 grant slot (pins: [{name 'p[hi:lo]', face, span_um}])."""
    out, extra = [], []
    cover = defaultdict(int)
    for g in slot['pins']:
        m = re.fullmatch(r'(\w+)(?:\[(\d+):(\d+)\])?', g['name'])
        p = m.group(1)
        if p not in ports:
            extra.append(p); continue
        hi_b, lo_b = (int(m.group(2)), int(m.group(3))) if m.group(2) else (0, 0)
        nb = hi_b - lo_b + 1
        cover[p] += nb
        lo, hi = g['span_um']
        if hi - lo < nb * 0.048:     # a grant span shorter than its bits on one track pitch: centre-widen
            c = (lo + hi) / 2; lo, hi = c - nb * 0.024, c + nb * 0.024
        out.append((p, ports[p][0], g['face'], lo, hi, nb, lo_b, ports[p][1] > 1))
    bad = {p: (cover.get(p, 0), w) for p, (d, w) in ports.items() if cover.get(p, 0) != w}
    return out, bad, extra


def rect_of(x, y, w, h, o, px, py):
    if o in ('MY', 'R180'):
        px = w - px
    if o in ('MX', 'R180'):
        py = h - py
    return x + px, y + py


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--ctrl-view', required=True, type=Path)
    ap.add_argument('--ctrl-kind', default='SYNTH (mapped netlist ETM + kit outline/faces)')
    ap.add_argument('--feed-view', required=True, type=Path, help='dir: feed.netlist.v + <SVG_M>_synth_{tt,ff}.lib')
    ap.add_argument('--feed-wh', nargs=2, type=float, default=[1036.8, 194.4])
    ap.add_argument('--sm-view', required=True, type=Path, help='dir: smh netlist + <SM_M>_synth_{tt,ff}.lib')
    ap.add_argument('--paths', type=int, default=200000)
    ap.add_argument('--clock-pads', type=Path)
    ap.add_argument('--ckgen', default='hb_ckgen')
    a = ap.parse_args()
    G = json.loads(GRANTS.read_text()); P = json.loads(PLAN.read_text())
    slots = {s['name']: s for s in G['slots']}
    W, H = G['floorplan']['die_um']
    out = a.out; out.mkdir(parents=True, exist_ok=True)
    vd = out / 'views'; vd.mkdir(exist_ok=True)
    (out / 'out').mkdir(exist_ok=True)
    kinds = {}
    # ---- views ----
    phy_dir = ROOT / f'physical/asap7_memory_macros/{PHY_M}'
    shutil.copy(phy_dir / f'{PHY_M}.lef', vd / f'{PHY_M}.lef')
    for c in ('tt', 'ff'):
        shutil.copy(phy_dir / f'{PHY_M}_{c}.lib', vd / f'{PHY_M}_{c}.lib')
    kinds[PHY_M] = 'hard_macro_abstract (PHY only, the one modelled core)'
    cv = a.ctrl_view
    for c in ('tt', 'ff'):
        shutil.copy(next(cv.glob(f'*_{c}.lib')), vd / f'{CTL_M}_{c}.lib')
    lefs = list(cv.glob('*.lef'))
    ctl_ports = ports_of_lib(vd / f'{CTL_M}_tt.lib')
    ecap = {}
    if 'SYNTH' in a.ctrl_kind:
        ecap[CTL_M] = [entry_cap(vd / f'{CTL_M}_{c}.lib') for c in ('tt', 'ff')]
    if lefs:
        shutil.copy(lefs[0], vd / f'{CTL_M}.lef')
    else:
        spec = json.loads((ROOT / 'physical/ref_tile/hdie_pc_ctrl/floorplan.json').read_text())
        cw, ch = spec['die'][2], spec['die'][3]
        synth_lef(CTL_M, cw, ch, face_pins(ctl_ports, spec['pins'], cw, ch), vd / f'{CTL_M}.lef')
    kinds[CTL_M] = a.ctrl_kind
    fv = a.feed_view
    for c in ('tt', 'ff'):
        shutil.copy(next(fv.glob(f'*_synth_{c}.lib')), vd / f'{SVG_M}_{c}.lib')
    svg_ports = ports_of_lib(vd / f'{SVG_M}_tt.lib')
    ecap[SVG_M] = [entry_cap(vd / f'{SVG_M}_{c}.lib') for c in ('tt', 'ff')]
    fw, fh = a.feed_wh
    kport = ['k_v', 'k_rdy', 'k_addr', 'k_len', 'k_tag', 'k_we', 'k_wdata', 'k_wstrb', 'k_wr_done', 'kr_v', 'kr_rdy',
             'kr_tag', 'kr_beat', 'kr_data']
    smside = ['packet_observe', 'sm_command']
    rest = [p for p in svg_ports if p not in kport + smside]
    clocks = [p for p in rest if re.search(r'clk|rst', p)]
    ctlp = [p for p in rest if p not in clocks]
    synth_lef(SVG_M, fw, fh, face_pins(svg_ports, {'S': kport, 'N': smside, 'W': clocks, 'E': ctlp}, fw, fh),
              vd / f'{SVG_M}.lef')
    kinds[SVG_M] = 'SYNTH (mapped netlist ETM, LBANKS 4, STACK 0 SM 0 representative; generated outline/faces)'
    sv = a.sm_view
    for c in ('tt', 'ff'):
        shutil.copy(next(sv.glob(f'*_synth_{c}.lib')), vd / f'{SM_M}_{c}.lib')
    sm_ports = ports_of_lib(vd / f'{SM_M}_tt.lib')
    ecap[SM_M] = [entry_cap(vd / f'{SM_M}_{c}.lib') for c in ('tt', 'ff')]
    s0 = slots['sm_SW0']
    pins, miss, extra = grant_pins(s0, sm_ports)
    assert not miss, ('SM ports whose grant pins do not cover the view port', miss)
    kinds['sm_grant_ports_absent_in_view'] = extra
    synth_lef(SM_M, s0['outline']['w'], s0['outline']['h'], pins, vd / f'{SM_M}.lef')
    kinds[SM_M] = 'SYNTH (hierarchical mapped netlist ETM, -DOT_SMH_FC_HIER; outline + pins = v6 grant)'
    vpins = {m: lef_pins(vd / f'{m}.lef') for m in (PHY_M, CTL_M, SVG_M, SM_M)}
    vxy = {m: lef_xy(vd / f'{m}.lef') for m in (PHY_M, CTL_M, SVG_M, SM_M)}
    for m in (CTL_M, SVG_M, SM_M):
        lib = ports_of_lib(vd / f'{m}_tt.lib')
        lp = {re.sub(r'\[\d+\]$', '', p) for p in vpins[m]}
        assert set(lib) == lp, (m, sorted(set(lib) ^ lp)[:10])
    sz = {}
    for m in vpins:
        t = (vd / f'{m}.lef').read_text()
        mm = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t)
        sz[m] = (float(mm.group(1)), float(mm.group(2)))
    # ---- placement ----
    leaves = {}
    cw, ch = sz[CTL_M]
    per = [('row_v', 1, 'c'), ('row_op', 3, 'c'), ('row_bank', 5, 'c'), ('row_row', 19, 'c'), ('col_v', 1, 'c'),
           ('col_we', 1, 'c'), ('col_bank', 5, 'c'), ('col_col', 5, 'c'), ('col_data', 256, 'c'), ('col_strb', 32, 'c'),
           ('dram_rvalid', 1, 'p'), ('dram_rdata', 256, 'p')]
    kw = dict(k_v=1, k_rdy=1, k_we=1, k_addr=30, k_len=4, k_tag=17, k_wdata=256, k_wstrb=32, k_wr_done=1, kr_v=1,
              kr_rdy=1, kr_tag=17, kr_beat=4, kr_data=256)
    kdir_ctl = {p: ctl_ports[p][0] for p in kw}
    nets = {}
    used = defaultdict(set)

    def net(name, drv, loads):
        nets[name] = [drv] + loads
        for i, p in [drv] + loads:
            used[i].add(p)

    for q in Q:
        b = P[f'phy_{q}']; north = b['y'] > 10000
        phy = f'phy_{q}'
        leaves[phy] = dict(m=PHY_M, x=b['x'], y=b['y'], o='MX' if north else 'R0', w=b['w'], h=b['h'])
        lp = vxy[PHY_M]
        for pc in range(32):
            xs = [lp[f'{n}[{pc * w + k}]'][0] for n, w, _ in per for k in range(w)]
            cx = b['x'] + sum(xs) / len(xs)
            l = f'ctl_{q}_p{pc:02d}'
            y = round(b['y'] - 10.8 - ch, 3) if north else round(b['y'] + b['h'] + 10.8, 3)
            leaves[l] = dict(m=CTL_M, x=round(round((cx - cw / 2) / 0.216) * 0.216, 3), y=y, o='MX' if north else 'R0',
                             w=cw, h=ch)
            for n, w, d in per:
                for k in range(w):
                    pp = f'{n}[{pc * w + k}]'
                    lpin = f'{n}[{k}]' if w > 1 else n
                    if d == 'c':
                        net(f'n_{q}_{n}_{pc * w + k}', (l, lpin), [(phy, pp)])
                    else:
                        net(f'n_{q}_{n}_{pc * w + k}', (phy, pp), [(l, lpin)])
        for k in range(8):
            box = P[f'pc_{q}{k}']
            g = f'svg_{q}{k}'
            gx = round(round((box['x'] + (box['w'] - fw) / 2) / 0.216) * 0.216, 3)
            gy = round(box['y'] + 4.32, 3) if north else round(box['y'] + box['h'] - fh - 4.32, 3)
            leaves[g] = dict(m=SVG_M, x=gx, y=gy, o='MX' if north else 'R0', w=fw, h=fh)
            for lane in range(4):
                l = f'ctl_{q}_p{4 * k + lane:02d}'
                for p, w in kw.items():
                    for j in range(w):
                        gp = f'{p}[{lane * w + j}]'
                        cp_ = f'{p}[{j}]' if w > 1 else p
                        nn = f'k_{q}{k}_{lane}_{p}_{j}'
                        if kdir_ctl[p] == 'input':
                            net(nn, (g, gp), [(l, cp_)])
                        else:
                            net(nn, (l, cp_), [(g, gp)])
            s = slots[f'sm_{q}{k}']
            leaves[f'sm_{q}{k}'] = dict(m=SM_M, x=s['origin']['x'], y=s['origin']['y'], o=s['origin']['orient'],
                                        w=s['outline']['w'], h=s['outline']['h'])
            for j in range(1099):
                net(f'pk_{q}{k}_{j}', (g, f'packet_observe[{j}]'), [(f'sm_{q}{k}', f'packet[{j}]')])
            for j in range(83):
                net(f'cm_{q}{k}_{j}', (g, f'sm_command[{j}]'), [(f'sm_{q}{k}', f'command[{j}]')])
    ls = list(leaves.items())
    for i, (l1, v1) in enumerate(ls):
        for l2, v2 in ls[i + 1:]:
            if v1['x'] < v2['x'] + v2['w'] and v2['x'] < v1['x'] + v1['w'] and \
                    v1['y'] < v2['y'] + v2['h'] and v2['y'] < v1['y'] + v1['h']:
                raise SystemExit(f'overlap {l1} {l2}')
    # ---- clock domains of every view clock pin ----
    def domain(m, pin):
        b = re.sub(r'\[\d+\]$', '', pin)
        if m in (PHY_M, CTL_M):
            return 'hbm' if b == 'clk' else None
        if m == SM_M:
            return 'stream' if b == 'clk' else None
        if m == SVG_M:
            return {'stream_clk': 'stream', 'stream_bank_clk': 'stream', 'hbm_clk': 'hbm', 'hbm_fifo_clk': 'hbm',
                    'hbm_pc_clk': 'hbm'}.get(b)
    ck = slots[a.ckgen]
    pads = json.loads(a.clock_pads.read_text()) if a.clock_pads else {}
    obs = [(v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h']) for v in leaves.values()]
    for n, b in P.items():
        if isinstance(b, dict) and 'x' in b and n.split('_')[0] not in ('phy', 'pc', 'sm'):
            obs.append((b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
    trees = {}
    clkpins = defaultdict(lambda: defaultdict(list))   # domain -> inst -> [pins]
    for l, v in leaves.items():
        for p in vpins[v['m']]:
            d = domain(v['m'], p)
            if d:
                clkpins[d][l].append(p)
    for di, (dom, insts) in enumerate(sorted(clkpins.items())):
        rx = ck['origin']['x'] + ck['outline']['w'] * (0.3 + 0.4 * di)
        ry = ck['origin']['y'] + ck['outline']['h'] / 2
        sinks = []
        for l, pl in insts.items():
            v = leaves[l]
            px, py = vxy[v['m']][sorted(pl)[0]]
            x, y = rect_of(v['x'], v['y'], v['w'], v['h'], v['o'], px, py)
            sinks.append((l, sorted(pl)[0], x, y))
        dp = pads.get(dom, {})
        t = dct.build(W, H, obs, (rx, ry), sinks, lambda inst: re.search(r'(SW|SE|NW|NE)', inst).group(1),
                      leaf_pads=dp.get('leaf'), quad_pads=dp.get('quadrant'))
        pre = {'hbm': 'dkh', 'stream': 'dks'}[dom]
        ren = lambda s: s.replace('dck_', pre + '_')
        port = f'clk_{dom}'
        bufs = [(ren(b), c, x, y) for b, c, x, y in t['buffers']]
        tnets = []
        for n, d, loads in t['nets']:
            d2 = ('port', port) if d == ('port', 'clk_hbm') else (d[0], ren(d[1]))
            l2 = []
            for ld in loads:
                if ld[0] == 'pin':
                    l2 += [('pin', ld[1], p) for p in insts[ld[1]]]
                else:
                    l2.append((ld[0], ren(ld[1])))
            tnets.append((ren(n), d2, l2))
        trees[dom] = dict(buffers=bufs, nets=tnets, model=t['model'], port=port)
    leafclk = {}
    for dom, t in trees.items():
        for n, d, loads in t['nets']:
            for ld in loads:
                if ld[0] == 'pin':
                    leafclk[(ld[1], ld[2])] = n
    for (l, p) in leafclk:
        used[l].add(p)
    rstp = {PHY_M: ['rst_n'], CTL_M: ['rst_n'], SM_M: ['rst_n'],
            SVG_M: [p for p in svg_ports if p.endswith('rst_n')]}
    # ---- die.v ----
    conn = defaultdict(list)
    for n, ends in nets.items():
        for i, p in ends:
            conn[i].append((p, n))
    for (l, p), n in leafclk.items():
        conn[l].append((p, n))
    L = ['// H-DIE v15 whole-die service+SM case (tools/hbm_die_v15/die_case.py); out-of-case pins open (manifest)',
         'module hbm_v15_die (input wire clk_hbm, input wire clk_stream, input wire rst_n);']
    nc = []
    body = []
    for l in sorted(leaves):
        v = leaves[l]; m = v['m']
        cs = []
        bus = defaultdict(dict); scal = []
        for p, n in conn[l]:
            mm = re.fullmatch(r'(\w+)\[(\d+)\]', p)
            if mm:
                bus[mm.group(1)][int(mm.group(2))] = n
            else:
                scal.append((p, n))
        for rp in rstp[m]:
            wv = sum(1 for q_ in vpins[m] if re.fullmatch(re.escape(rp) + r'(\[\d+\])?', q_))
            if wv <= 1:
                scal.append((rp, 'rst_n'))
            else:
                for k in range(wv):
                    bus[rp][k] = 'rst_n'
            used[l].add(rp)
        for p, n in sorted(scal):
            cs.append(f'.{p}({n})')
        for p, bits in sorted(bus.items()):
            wv = 1 + max(int(re.fullmatch(r'\w+\[(\d+)\]', q_).group(1)) for q_ in vpins[m] if q_.startswith(p + '['))
            parts = []
            for k in range(wv - 1, -1, -1):
                if bits.get(k):
                    parts.append(bits[k])
                else:
                    nn = f'nc_{l}_{p}_{k}'; nc.append(nn); parts.append(nn)
            cs.append(f'.{p}({{{", ".join(parts)}}})')
        body.append(f'  {m} {l} (\n    ' + ',\n    '.join(cs) + '\n  );')
    tw = []
    for dom, t in trees.items():
        drv, inp = {}, {}
        for n, d, loads in t['nets']:
            if d[0] == 'buf':
                drv[d[1]] = n
            for ld in loads:
                if ld[0] == 'buf':
                    inp[ld[1]] = n
        first = [n for n, d, _ in t['nets'] if d == ('port', t['port'])]
        assert len(first) == 1, first
        for n, d, loads in t['nets']:
            if n != first[0]:
                tw.append(f'  wire {n};')
        for b, cell, x, y in t['buffers']:
            i_ = inp[b] if inp[b] != first[0] else t['port']
            o_ = drv.get(b, b + '_nc')
            if o_ == first[0]:
                o_ = t['port']
            body.append(f'  {cell} {b} (.A({i_}), .Y({o_}));')
        # the first net is the port itself: rename its loads' references
        body[:] = [x.replace(f'({first[0]})', f'({t["port"]})') for x in body]
    L += [f'  wire {n};' for n in sorted(nets)] + [f'  wire {n};' for n in nc] + tw + body + ['endmodule']
    (out / 'die.v').write_text('\n'.join(L) + '\n')
    # ---- run.tcl ----
    plat = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    p_ = TILE / 15.0
    pl = [f'place_inst -name {l} -location {{{v["x"]:.3f} {v["y"]:.3f}}} -orientation {v["o"]} -status FIRM'
          for l, v in sorted(leaves.items())]
    for t in trees.values():
        pl += [f'place_inst -name {b} -location {{{x:.3f} {y:.3f}}} -orientation R0 -status FIRM' for b, c, x, y in t['buffers']]
    ms = (PHY_M, CTL_M, SVG_M, SM_M)
    sinks = ' '.join(sorted(leaves))
    tcl = f'''# H-DIE v15 whole-die service+SM GRT + TT/FF STA (generated by tools/hbm_die_v15/die_case.py)
read_lef {plat}/lef/asap7_tech_1x_201209.lef
read_lef {plat}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{chr(10).join(f'read_lef /work/views/{m}.lef' for m in ms)}
define_corners tt ff
{chr(10).join(f'read_liberty -corner {c} /work/views/{m}_{c}.lib' for m in ms for c in ('tt', 'ff'))}
{chr(10).join(f'read_liberty -corner {c} {plat}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{c.upper()}_nldm_220122.lib.gz' for c in ('tt', 'ff'))}
read_verilog /work/die.v
link_design hbm_v15_die
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
{chr(10).join(pl)}
place_pin -pin_name clk_hbm -layer M9 -location {{{ck['origin']['x'] + ck['outline']['w'] * 0.3:.3f} {ck['origin']['y'] + ck['outline']['h'] / 2:.3f}}} -pin_size {{0.4 0.4}}
place_pin -pin_name clk_stream -layer M9 -location {{{ck['origin']['x'] + ck['outline']['w'] * 0.7:.3f} {ck['origin']['y'] + ck['outline']['h'] / 2:.3f}}} -pin_size {{0.4 0.4}}
place_pins -hor_layers M4 -ver_layers M5 -min_distance 2
source {plat}/setRC.tcl
set blk [ord::get_db_block]
foreach n [$blk getNets] {{ if {{[string match dk?_* [$n getName]] || [string match n_dk?_* [$n getName]] || [string match clk_* [$n getName]]}} {{ $n setSigType CLOCK }} }}
set_wire_rc -clock -layer M8
set_wire_rc -signal -layer M6
set_routing_layers -signal M4-M9 -clock M7-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
set t0 [clock seconds]
global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
estimate_parasitics -global_routing
create_clock -name hbm -period {PERIOD['hbm']} [get_ports clk_hbm]
create_clock -name stream -period {PERIOD['stream']} [get_ports clk_stream]
set_clock_groups -asynchronous -group hbm -group stream
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_ports rst_n]
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
foreach c {{tt ff}} {{
  foreach n {{{sinks}}} {{
    report_checks -from [get_cells $n] -corner $c -path_delay [expr {{$c eq "tt" ? "max" : "min"}}] -format full_clock_expanded >> /work/out/sink_paths_$c.rpt
  }}
}}
puts OT_DONE
'''
    (out / 'run.tcl').write_text(tcl)
    (out / 'run.sh').write_text('''#!/bin/bash
# OpenROAD in the pinned ORFS image; writes out/run.log, out/run.exit
D=$(cd $(dirname $0) && pwd); N=hdie-diecase-$$
docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-96}g -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/run.tcl > /work/out/run.log 2>&1; rc=\\$?; chmod -R a+rwX /work/out; exit \\$rc"
echo $? > $D/out/run.exit
''')
    # ---- manifest ----
    owner = {SM_M: 'H-SM (VM SM_X/SM_OUT/KV_DESC peers not in this case)', SVG_M: 'H-DIE (service command source / host loader)',
             CTL_M: 'H-DIE (stack fault glue)', PHY_M: 'H-DIE'}
    open_pins = defaultdict(lambda: defaultdict(int))
    for l, v in leaves.items():
        for p in vpins[v['m']]:
            if p not in used[l] and p not in ('VDD', 'VSS'):
                open_pins[v['m']][re.sub(r'\[\d+\]$', '', p)] += 1
    man = dict(schema='opentallas.hbm_v15.die_case.v1', region='service_engine+SM (whole HBM->SM datapath)', die_um=[W, H],
               grants=str(GRANTS.relative_to(ROOT)), grants_version=G['version'], plan=str(PLAN.relative_to(ROOT)),
               views=kinds, synth_clock_entry=dict(rule='SYNTH ETM clock pins re-capped to one 2 fF entry buffer; tile '
                                                     'insertion not included (no tile CTS yet)', pins_recapped=ecap), instances={m: sum(1 for v in leaves.values() if v['m'] == m) for m in ms},
               signal_nets=len(nets), clock_domains={d: dict(period_ps=PERIOD[d], sinks=sum(len(x) for x in clkpins[d].values()),
                                                             insts=len(clkpins[d])) for d in clkpins},
               die_clock_trees={d: t['model'] for d, t in trees.items()},
               open_pins_by_master={m: dict(v) for m, v in open_pins.items()}, open_owner=owner,
               placement={l: v for l, v in leaves.items()},
               corners='setup TT, hold FF (owner option B); SS not run')
    (out / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps({k: man[k] for k in ('instances', 'signal_nets', 'clock_domains')}))


if __name__ == '__main__':
    main()
