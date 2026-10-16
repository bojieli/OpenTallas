#!/usr/bin/env python3
"""H-SU 2026-10-16: SFU core (ot_hgi_sfu_scheduled_engine, LG_PATH 24) fit against its die slot.

Inputs: the hierarchical synth (results/arch/hbm_su_f2_static_1014/sfucore_sizing_0600/stat_top.txt) and real
outlines: closed lane ot_su12_sfu 159.84x330.48 (x16), operand-store SRAM ot_sram_1r1w_256x256 172.8x41.04 (x80),
programme/calendar SRAM ot_sram_1r1w_1024x256 174.744x70.47 (x22). SRAM rows are paired back-to-back with one 20 um
pin channel per pair; lane rows have 20 um channels. Standard cells at 60 % util in a strip. Planning only.
"""
import json, math, re, sys
from pathlib import Path

CH, EDGE, GRID = 20.0, 20.0, 2.16
LANE = (159.84, 330.48); OPS = (172.8, 41.04); PRG = (174.744, 70.47)


def pack(width, std_um2):
    inner = width - 2 * EDGE
    rects, y = [], EDGE
    per = int((inner + CH) // (LANE[0] + CH))
    for i in range(16):
        r, c = divmod(i, per)
        rects.append(('lane', EDGE + c * (LANE[0] + CH), EDGE + r * (LANE[1] + CH), *LANE))
    y = EDGE + math.ceil(16 / per) * (LANE[1] + CH)
    for kind, (w, h), n in (('opstore_sram', OPS, 80), ('prog_sram', PRG, 22)):
        per = int((inner + CH) // (w + CH))
        rows = math.ceil(n / per)
        k = 0
        for r in range(rows):
            ry = y + (r // 2) * (2 * h + CH) + (r % 2) * h     # back-to-back pairs, one channel per pair
            for c in range(per):
                if k < n:
                    rects.append((kind, EDGE + c * (w + CH), ry, w, h)); k += 1
        y += math.ceil(rows / 2) * (2 * h + CH)
    std_h = std_um2 / 0.60 / inner
    rects.append(('std_cells_60pct', EDGE, y, inner, std_h))
    y += std_h + EDGE
    return rects, math.ceil(y / GRID) * GRID


def main():
    out = Path(sys.argv[1])
    stat = (out / 'stat_top.txt').read_text()
    std = float(re.search(r"Chip area for top module '\\ot_hgi_sfu_scheduled_engine': ([0-9.]+)", stat)[1])
    slot = dict(sfucore=(763.56, 1936.44), sfus=(763.56, 524.88))
    hard = 16 * LANE[0] * LANE[1] + 80 * OPS[0] * OPS[1] + 22 * PRG[0] * PRG[1]
    res = {}
    for w in (763.56, 1100.16):
        rects, h = pack(w, std)
        res[f'w{w}'] = dict(width=w, height=h, area_mm2=round(w * h / 1e6, 4), rects=[[k, round(x, 2), round(y, 2), ww, hh] for k, x, y, ww, hh in rects])
    granted = sum(a * b for a, b in slot.values()) / 1e6
    summary = dict(schema='opentallas.hsu.sfucore_fit.v1', author='Claude H-SU', date='2026-10-16',
                   top='ot_hgi_sfu_scheduled_engine LG_PATH=24, clock 833 ps (stream)',
                   synth_std_um2=std, hard=dict(lanes_ot_su12_sfu=16, opstore_sram_256x256=80, prog_sram_1024x256=22,
                                                 hard_outline_mm2=round(hard / 1e6, 4)),
                   total_hard_plus_std60_mm2=round((hard + std / 0.6) / 1e6, 4),
                   granted=dict(slots=slot, total_mm2=round(granted, 4)),
                   fit_in_grant=False,
                   needed={k: {kk: vv for kk, vv in v.items() if kk != 'rects'} for k, v in res.items()},
                   status='PLANNING geometry from synth + real macro/lane outlines; no placement/route qualification')
    (out / 'fit.json').write_text(json.dumps(summary, indent=1) + '\n')
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    col = dict(lane='#d0632a', opstore_sram='#4a78c2', prog_sram='#7b4fb0', std_cells_60pct='#cccccc')
    fig, axs = plt.subplots(1, 2, figsize=(9, 10))
    for ax, v in zip(axs, res.values()):
        ax.add_patch(Rectangle((0, 0), v['width'], v['height'], fill=False, ec='k', lw=1.4))
        ax.axhline(1936.44, color='r', ls='--', lw=1); ax.text(5, 1950, 'granted sfucore top 1936.44', color='r', fontsize=7)
        for k, x, y, w, h in v['rects']:
            ax.add_patch(Rectangle((x, y), w, h, fc=col[k], ec='k', lw=0.3))
        ax.set_xlim(-20, 1150); ax.set_ylim(-20, max(r['height'] for r in res.values()) + 50); ax.set_aspect('equal')
        ax.set_title(f"{v['width']} x {v['height']} = {v['area_mm2']} mm2", fontsize=8)
    fig.suptitle(f"SFU core fit: lanes orange, operand SRAM blue, programme SRAM purple, std grey (60%)\n"
                 f"hard {summary['hard']['hard_outline_mm2']} mm2 + std {std/1e6:.4f} mm2 vs granted {summary['granted']['total_mm2']} mm2", fontsize=8)
    fig.tight_layout(); fig.savefig(out / 'fit.png', dpi=120)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
