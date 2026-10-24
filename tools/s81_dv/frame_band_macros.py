#!/usr/bin/env python3
"""frame_band_macros.py -- S81-P7 (10-23): hard-core / ROM macro positions of the frame bands in the die-plan frame types.

The frame partitions (die_plan types col_<M>_r<k>*, 1442.88 x 1226.88 um) hold one band of the landed frame: 35 ROM
macros (ot_rom_4096x72_m8) plus the hardened children (q elements, q banks, bf cols / front roots, return nodes, cfg
sequencers, stations, relays).  Sources of the positions (all already GEOM-reviewed frame floorplans):
  col_h9   the three band kits physical/ref_tile/s81frame_col_h9_vgch_b{0,1,2}/spec.json (frame_hier_kit.py; band frame)
  col_h10  no band kits exist (r1 is taller than the partition in that floorplan: its row gaps are compressed): the flat frame kit physical/ref_tile/s81frame_col_h10_vg/spec.json is CUT into the RTL
           bands (instance -> band from the plan contents rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h10_l4_lp_plan.sv);
           the three bands are disjoint in y in that floorplan, so each band is shifted down to its own partition
           frame (y - band ymin + MARGIN), x unchanged.
Every position is checked: inside the partition outline, no two macro boxes overlap.  Output JSON per master/band:
[{inst (path inside the plan content, u_r<k>/...), module, view, lef, lib, origin_um, orient, size_um}] + a PNG per
band for GEOM review.

  frame_band_macros.py --out physical/die_plan/s81/inputs/frame_band_macros.json [--png-dir DIR]
"""
import argparse, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTLINE = (1442.88, 1226.88)
LATTICE = 8.64                     # die-plan grid_um
MARGIN = 21.6                      # h10 band shift: lowest macro edge this far above the band floor (multiple of 2.16/0.27)
MIN_GAP = 13.8                     # S81-P8 10-23 (GEOM-REVIEW5 15:14 h10_r1 FAIL): every facing macro-macro gap >= the 13.8-um
                                   # standard of the reviewed band kits (std-cell + M2-M4 access between macro rows)
# S81-P8 10-23 (COORD/GEOM: r0_p1 GPL did not converge): the four x-forward stations u_xo<j> (dsfd_dvrly_276_NS, pins on
# the N (i) / S (o) edges only) sit next to the W-face xo_o0 window of every r0 frame type (plan windows y 24-336 in the
# type frame), stacked along the free W strip (x 0-43.2) below u_e0 -- not bottom-right, where 1104 b of x/xo crossed the
# ROM field twice.  Origins on the 8.64 lattice; >= 17.28 um to c0_0 (x 51.84) and to each other.
# S81-P8 10-23 plan v4.5 (COORD 15:45 spot-check: internal reg-reg hops > 750 um need a stage; measured 1.2-2.5k per kit):
# connectivity-driven re-site of the E-column macros (qbank_S/N, cfg7, nodes, rstg, sstn, cfifo) next to the elements /
# stations they talk to; ROMs, q elements, bf cols / front roots fixed.  Moves from tools/s81_dv/frame_resite (bit-level
# band netlist + view LEF pins; report resite_report_v45.txt): max modelled hop h9 r1 1212 -> 746, r2 1055 -> 592,
# h10 r2 1055 -> 554; r0 (x bus) and h10 r1 (u_n24) still need RTL stages.
RESITE = Path(__file__).resolve().parents[2] / 'physical/die_plan/s81/inputs/frame_band_resite.json'
XO_SITES = {f'u_r0.u_xo{j}': [8.64, round(86.4 + 34.56 * j, 4)] for j in range(4)}


def git_text(path):
    p = ROOT / path
    if p.is_file():
        return p.read_text()
    return subprocess.run(['git', '-C', str(ROOT), 'show', f'origin/main:{path}'], capture_output=True, text=True,
                          check=True).stdout


def view_files(view):
    n = view.split('/')[-1]
    lef = f'{view}/{n}.lef'
    lib = f'{view}/{n}_tt.lib'
    # ROM clk->q and address capacitance are required for timing and fanout repair.
    # The selected macro ships the same TT/FF naming convention as the hard cores.
    git_text(lib)
    txt = git_text(lef)
    m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', txt)
    return lef, lib, (float(m.group(1)), float(m.group(2)))


def spec(name):
    return json.loads(git_text(f'physical/ref_tile/{name}/spec.json'))


def band_of(master):
    txt = (ROOT / f'rtl/dsrom_sys/s81_dv/frame_lp/plan/{master}_l4_lp_plan.sv').read_text()
    band = {}
    for m in re.split(r'^module ', txt, flags=re.M)[1:]:
        if m.split()[0].endswith('_nx'):
            continue
        k = int(m.split()[0].split('_r')[-1].rstrip('#( '))
        for inst in re.findall(r'^\s+\w+ (?:#\(.*?\) )?(u_\w+) \(', m, flags=re.M):
            band[inst] = k
    return band


def entry(c, k, dx, dy):
    lef, lib, sz = view_files(c['view'])
    o = c.get('orient', 'R0')
    w, h = (sz[1], sz[0]) if o in ('R90', 'R270', 'MXR90', 'MYR90') else sz
    inst = c['inst']   # flat synthesis (SYNTH_HIERARCHICAL 0): Yosys names a nested instance u_r<k>.<path>
    return dict(inst=f'u_r{k}.{inst}', module=c['view'].split('/')[-1], view=c['view'], lef=lef, lib=lib,
                origin_um=[round(c['at'][0] + dx, 4), round(c['at'][1] + dy, 4)], orient=o, size_um=[w, h])


def check(lst, tag):
    errs = []
    for e in lst:
        x, y = e['origin_um']
        w, h = e['size_um']
        if x < 0 or y < 0 or x + w > OUTLINE[0] + 1e-6 or y + h > OUTLINE[1] + 1e-6:
            errs.append(f'{tag} {e["inst"]} outside outline: {x},{y} {w}x{h}')
    for i, a in enumerate(lst):
        for b in lst[i + 1:]:
            ax, ay = a['origin_um']
            bx, by = b['origin_um']
            if ax < bx + b['size_um'][0] - 1e-6 and bx < ax + a['size_um'][0] - 1e-6 and \
               ay < by + b['size_um'][1] - 1e-6 and by < ay + a['size_um'][1] - 1e-6:
                errs.append(f'{tag} overlap {a["inst"]} / {b["inst"]}')
    return errs


def facing_gap(a, c):
    """(dx, dy) clearance of two boxes; one of them is 0 when they face each other (overlap in the other axis)"""
    ax, ay = a['origin_um']; aw, ah = a['size_um']
    cx, cy = c['origin_um']; cw, ch = c['size_um']
    return max(cx - (ax + aw), ax - (cx + cw), 0.0), max(cy - (ay + ah), ay - (cy + ch), 0.0)


def spread_rows(lst):
    """lift whole macro rows (same origin y) by lattice steps until every vertical facing gap is >= MIN_GAP (the h10 r1
    row-gap compression x0.912 left the small-ROM row 3.24 um above the qxpq ROM); returns the number of rows lifted"""
    lifted = set()
    for _ in range(100):
        moved = False
        for a in sorted(lst, key=lambda e: e['origin_um'][1]):
            need = 0.0
            for c in lst:
                if c is a or c['origin_um'][1] >= a['origin_um'][1]:
                    continue
                dx, dy = facing_gap(a, c)
                if dx == 0.0 and dy < MIN_GAP - 1e-6:
                    need = max(need, c['origin_um'][1] + c['size_um'][1] + MIN_GAP)
            if need:
                y0 = a['origin_um'][1]
                y1 = round(-(-need // LATTICE) * LATTICE, 4)
                for e in lst:
                    if abs(e['origin_um'][1] - y0) < 1e-6:
                        e['origin_um'][1] = y1
                lifted.add(y0)
                moved = True
                break
        if not moved:
            return len(lifted)
    raise SystemExit('spread_rows: no fixpoint')


def gap_check(lst, tag):
    errs = []
    for i, a in enumerate(lst):
        for c in lst[i + 1:]:
            dx, dy = facing_gap(a, c)
            if (dx == 0.0 or dy == 0.0) and max(dx, dy) < MIN_GAP - 1e-6:
                errs.append(f'{tag} gap {max(dx, dy):.2f} < {MIN_GAP}: {a["inst"]} / {c["inst"]}')
    return errs


def render(lst, tag, png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.add_patch(Rectangle((0, 0), *OUTLINE, fill=False, lw=2))
    col = {'ot_rom_4096x72_m8': '#8172b3', 'ot_v41_rom_elem_q_qxpq_w10': '#4c72b0', 'ot_v41_bf_col': '#dd8452',
           'dsfd_bf_front_roots': '#c44e52'}
    for e in lst:
        ax.add_patch(Rectangle(e['origin_um'], *e['size_um'], fc=col.get(e['module'], '#55a868'), ec='k', lw=0.3,
                               alpha=0.8))
        if e['module'] != 'ot_rom_4096x72_m8':
            ax.text(e['origin_um'][0] + 2, e['origin_um'][1] + 2, e['inst'].split('.', 1)[1], fontsize=5)
    ax.set_xlim(-20, OUTLINE[0] + 20)
    ax.set_ylim(-20, OUTLINE[1] + 20)
    ax.set_aspect('equal')
    ax.set_title(f'{tag}: {len(lst)} macros/hard children in the plan frame partition {OUTLINE[0]} x {OUTLINE[1]} um')
    fig.savefig(png, dpi=130, bbox_inches='tight')
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--png-dir')
    a = ap.parse_args()
    res, errs = dict(outline_um=list(OUTLINE), sources={}, masters={}), []
    # col_h9: band kits (already in the band frame)
    res['masters']['col_h9'] = {}
    for k in range(3):
        s = spec(f's81frame_col_h9_vgch_b{k}')
        res['sources'][f'col_h9_r{k}'] = f'physical/ref_tile/s81frame_col_h9_vgch_b{k}/spec.json'
        res['masters']['col_h9'][f'r{k}'] = [entry(c, k, 0.0, 0.0) for c in s['children'] + s['macros']]
    # col_h10: cut the flat kit into the RTL bands
    s = spec('s81frame_col_h10_vg')
    band = band_of('col_h10')
    by = {0: [], 1: [], 2: []}
    for c in s['children'] + s['macros']:
        k = band[c['inst'].split('.')[0]]
        by[k].append(c)
    res['masters']['col_h10'] = {}
    for k, lst in by.items():
        y0 = min(c['at'][1] for c in lst)
        dy = 0.0 if k == 0 else round(MARGIN - y0, 4)
        res['sources'][f'col_h10_r{k}'] = f'physical/ref_tile/s81frame_col_h10_vg/spec.json (cut, y shift {dy})'
        ents = [entry(c, k, 0.0, dy) for c in lst]
        top = max(e['origin_um'][1] + e['size_um'][1] for e in ents)
        if top > OUTLINE[1] - MARGIN:
            # the cut band is taller than the plan partition: compress the row gaps (origins scaled about the floor,
            # macro sizes unchanged), snapped to 0.54 um (2 std-cell rows); check() proves no overlap afterwards
            ttop = max(e['origin_um'][1] for e in ents if e['origin_um'][1] + e['size_um'][1] == top)
            sc = (OUTLINE[1] - MARGIN - (top - ttop) - MARGIN) / (ttop - MARGIN)
            for e in ents:
                y = MARGIN + (e['origin_um'][1] - MARGIN) * sc
                e['origin_um'][1] = round(round(y / 0.54) * 0.54, 4)
            res['sources'][f'col_h10_r{k}'] += f', row gaps x {sc:.4f}'
        res['masters']['col_h10'][f'r{k}'] = ents
    # die-plan hard_cores sit on the 8.64-um lattice (check.py hard_cores; sub-lattice shift < 2.16 um only for track
    # alignment): snap every origin to the nearest lattice point inside the outline (moves <= 4.32 um per axis)
    for m, bands in res['masters'].items():
        for b, lst in bands.items():
            for e in lst:
                e['kit_origin_um'] = list(e['origin_um'])
                for i in (0, 1):
                    v = round(e['origin_um'][i] / LATTICE) * LATTICE
                    while v + e['size_um'][i] > OUTLINE[i] + 1e-6:
                        v -= LATTICE
                    e['origin_um'][i] = round(max(v, 0.0), 4)
    for m, bands in res['masters'].items():
        for e in bands.get('r0', []):
            if e['inst'] in XO_SITES:
                e['origin_um'] = list(XO_SITES[e['inst']])
        rs = json.loads(RESITE.read_text()) if RESITE.is_file() else {}
        for b, lst in bands.items():
            for e in lst:
                if e['inst'] in rs.get(f'{m}.{b}', {}):
                    e['origin_um'] = list(rs[f'{m}.{b}'][e['inst']])
            n = spread_rows(lst)
            if n:
                res['sources'][f'{m}_{b}'] += f', {n} row(s) lifted to the {MIN_GAP}-um macro gap'
    for m, bands in res['masters'].items():
        for b, lst in bands.items():
            errs += check(lst, f'{m}_{b}')
            errs += gap_check(lst, f'{m}_{b}')
            if a.png_dir:
                Path(a.png_dir).mkdir(parents=True, exist_ok=True)
                render(lst, f'{m}_{b}', Path(a.png_dir) / f'{m}_{b}_macros.png')
            print(m, b, len(lst), 'ymax %.1f' % max(e['origin_um'][1] + e['size_um'][1] for e in lst))
    res['errors'] = errs
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    print('errors', len(errs), errs[:6])


if __name__ == '__main__':
    main()
