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
    if view.endswith('ot_rom_4096x72_m8'):
        lib = None
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
        for b, lst in bands.items():
            errs += check(lst, f'{m}_{b}')
            if a.png_dir:
                Path(a.png_dir).mkdir(parents=True, exist_ok=True)
                render(lst, f'{m}_{b}', Path(a.png_dir) / f'{m}_{b}_macros.png')
            print(m, b, len(lst), 'ymax %.1f' % max(e['origin_um'][1] + e['size_um'][1] for e in lst))
    res['errors'] = errs
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    print('errors', len(errs), errs[:6])


if __name__ == '__main__':
    main()
