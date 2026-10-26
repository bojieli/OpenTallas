#!/usr/bin/env python3
"""H-SU 2026-10-16: clean SU slice height for the v6b band (die may grow; no boundary shaving).

Packs one PG slice of each kind with the real hard outlines and 20 um macro/tile channels:
  heavy slice (G0/G1): 32 store banks r12 369.36x151.2, 16 heavy (KIND1 SFU) lanes, 16 LIGHT kind0 leaves 151.2^2
  light slice (G2/G3): 32 store banks, 32 LIGHT leaves
Row unit = a two-bank stack (151.2+20+151.2 = 322.4) beside the lanes that read it; a heavy lane is planned
330.48 tall (row height) x 166.32 (54,966 um2 = KIND1 synth 22,528 um2 / 0.416 measured kind0 synth:outline ratio,
the same ratio the closed LIGHT leaf has). The remaining width is the slice service column (pgslice bridges,
programme SRAM share, VM leaves, RF/reset glue). Planning geometry only: no placement/route qualification.
"""
import json, math, sys
from pathlib import Path

CH = 20.0           # macro/tile channel (20 um pin-face rule)
EDGE = 20.0         # slot edge clearance
GRID = 2.16         # H-DIE slot height grid
BANK = (369.36, 151.2)
LIGHT = (151.2, 151.2)
HEAVY = (166.32, 330.48)
STACK_H = 2 * BANK[1] + CH          # 322.4
ROW_H = max(HEAVY[1], STACK_H)      # 330.48


def heavy_slice(width):
    # row: H | BB | LL | BB | H  -> 2 heavy, 4 banks, 2..4 LIGHT (two LIGHT stacked); 16 heavy -> 8 rows
    rects, y = [], EDGE
    for r in range(8):
        x = EDGE
        for kind in ('H', 'BB', 'LL', 'BB', 'H'):
            if kind == 'H':
                rects.append(('heavy', x, y, *HEAVY)); x += HEAVY[0] + CH
            elif kind == 'BB':
                rects += [('bank', x, y, *BANK), ('bank', x, y + BANK[1] + CH, *BANK)]; x += BANK[0] + CH
            else:
                rects += [('light', x, y, *LIGHT), ('light', x, y + LIGHT[1] + CH, *LIGHT)]; x += LIGHT[0] + CH
        y += ROW_H + CH
    # 8 rows x LL stack = 16 LIGHT, as the slice needs
    used_w = x - CH
    return rects, used_w, y - CH


def light_slice(width):
    # row: LL | BB | LL | BB | LL | BB -> 6 banks + 6 LIGHT per row; 32 of each -> 6 rows (last partial)
    rects, y, nb, nl = [], EDGE, 0, 0
    used_w = 0
    while nb < 32 or nl < 32:
        x = EDGE
        for kind in ('LL', 'BB') * 3:
            if kind == 'BB' and nb < 32:
                rects += [('bank', x, y, *BANK), ('bank', x, y + BANK[1] + CH, *BANK)]; nb += 2; x += BANK[0] + CH
            elif kind == 'LL' and nl < 32:
                rects += [('light', x, y, *LIGHT), ('light', x, y + LIGHT[1] + CH, *LIGHT)]; nl += 2; x += LIGHT[0] + CH
        used_w = max(used_w, x - CH)
        y += STACK_H + CH
    return rects, used_w, y - CH


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    width = 1797.12                                     # v6b-recovery su_<q><k> width (unchanged: die width is reticle-bound)
    v6b_h = 2671.92
    res = {}
    for name, fn in (('heavy_G0G1', heavy_slice), ('light_G2G3', light_slice)):
        rects, uw, uh = fn(width)
        h_need = math.ceil((uh + EDGE) / GRID) * GRID
        cnt = {k: sum(1 for r in rects if r[0] == k) for k in ('bank', 'heavy', 'light')}
        hard = sum(r[3] * r[4] for r in rects) / 1e6
        svc_w = width - uw - CH - EDGE
        res[name] = dict(counts=cnt, array_w=round(uw, 2), array_h=round(uh, 2), slot_h_needed=round(h_need, 2),
                         fits_v6b_2671_92=h_need <= v6b_h + 1e-6, hard_mm2=round(hard, 4),
                         service_column_w=round(svc_w, 2), slot_mm2=round(width * max(h_need, v6b_h) / 1e6, 4))
        res[name]['rects'] = [[k, round(x, 2), round(y, 2), w, h] for k, x, y, w, h in rects]
    band_h = max(r['slot_h_needed'] for r in res.values())
    summary = dict(schema='opentallas.hsu.su_slice_band_v6.v1', author='Claude H-SU', date='2026-10-16',
                   slot_w=width, v6b_slot_h=v6b_h, clean_band_slot_h=band_h, delta_h_per_band=round(band_h - v6b_h, 2),
                   die_height_delta_two_bands_um=round(2 * (band_h - v6b_h), 2),
                   outlines=dict(bank_r12=BANK, light_kind0_leaf=LIGHT, heavy_planned=HEAVY, channel=CH, edge=EDGE),
                   basis='heavy outline 166.32x330.48 planned from KIND1 synth 22,528 um2 at the measured kind0 0.416 synth:outline ratio; '
                         'bank r12 CLOSED, kind0 leaf CLOSED; balanced 8-heavy/PG remap (Codex B) avoids growth but needs an atomic '
                         'RTL+compiler LID remap, so the band grows instead (owner 10-16 02:15: die may grow)',
                   slices={k: {kk: vv for kk, vv in v.items() if kk != 'rects'} for k, v in res.items()},
                   status='PLANNING geometry: rectangles only, no standard-cell placement, pins, GRT or timing')
    (out / 'band_v6.json').write_text(json.dumps(summary, indent=1) + '\n')
    (out / 'band_v6_rects.json').write_text(json.dumps({k: v['rects'] for k, v in res.items()}) + '\n')
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axs = plt.subplots(1, 2, figsize=(11, 8.5))
    col = dict(bank='#4a78c2', heavy='#d0632a', light='#5aa55a')
    for ax, (name, v) in zip(axs, res.items()):
        H = max(band_h, v6b_h)
        ax.add_patch(Rectangle((0, 0), width, band_h, fill=False, lw=1.5, ec='k'))
        ax.axhline(v6b_h, color='r', ls='--', lw=1); ax.text(10, v6b_h + 15, f'v6b slot top {v6b_h}', color='r', fontsize=7)
        for k, x, y, w, h in v['rects']:
            ax.add_patch(Rectangle((x, y), w, h, fc=col[k], ec='k', lw=0.3))
        sx = v['array_w'] + CH
        ax.add_patch(Rectangle((sx, EDGE), width - sx - EDGE, band_h - 2 * EDGE, fc='#dddddd', ec='k', lw=0.3, hatch='//'))
        ax.text(sx + 5, band_h / 2, 'service column\n(bridges, prog SRAM,\nVM leaves, glue)', fontsize=6, rotation=90)
        ax.set_xlim(-20, width + 20); ax.set_ylim(-20, H + 60); ax.set_aspect('equal')
        ax.set_title(f"{name}: needs {v['slot_h_needed']} um (v6b {v6b_h})\n{v['counts']} hard {v['hard_mm2']} mm2", fontsize=8)
    fig.suptitle(f'SU slice {width} wide: clean band height {band_h} um (bank blue, heavy orange, LIGHT green)', fontsize=9)
    fig.tight_layout(); fig.savefig(out / 'band_v6.png', dpi=130)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
