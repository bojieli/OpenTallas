#!/usr/bin/env python3
"""H-C27 fit study for the wider dsfd_bf_col (S-DIE 10-16: 529.200 x 198.72 -> BF_FRAME_EXTRA 145.584, frame 1,285.2).

    bfcol_fit_study.py --canonical C --hub-layout H --out DIR [--frame-w 1285.2] [--s14 400]

Street-only cluster mode (no transit channel; W seam roads 0|1 and hub-side pair, 60.48 um each).  Options:
  a  8 W + 9 E columns: the hub must shrink to the gap left between the S14 roads -> deficit
  b1 8 W + 8 E (one E column dropped), b2 7 W + 8 E (also the W hub-side column, 6 frames, dropped)
Frames per die and the hub x room are reported; the ROM / layer mapping (stage map, 128 regions) must be re-partitioned
by the compiler / model owner for b -- this study flags it and changes nothing.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

SEAM = 60.48


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--canonical', required=True)
    ap.add_argument('--hub-layout', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--frame-w', type=float, default=1285.2)
    ap.add_argument('--old-frame-w', type=float, default=1139.616)
    ap.add_argument('--s14', type=float, default=400.0)
    ap.add_argument('--options', default='8+9,8+8,7+8', help='W+E column counts, comma separated')
    a = ap.parse_args()
    d = json.loads(Path(a.canonical).read_text())
    hub = json.loads(Path(a.hub_layout).read_text())
    W, H = d['die_outline_um']
    cols = sorted(d['columns'], key=lambda c: c['x_um'])
    xs = [c['x_um'] for c in cols]
    gaps = [b - x for x, b in zip(xs, xs[1:])]
    nw = max(range(len(gaps)), key=gaps.__getitem__) + 1
    pitch = a.frame_w + 8.64
    frames = {}
    for f in d['placements']:
        frames.setdefault(round(f['origin_um'][0], 3), []).append(f)
    blocks = {k: v for k, v in hub['blocks'].items()}
    bx = [(k, v[0], v[1], v[2], v[3]) for k, v in blocks.items()]
    mix = hub.get('mix4_slot')
    if mix:
        bx.append(('sp_mix4', *mix))
    hub_lo = min(b[1] for b in bx)
    hub_hi = max(b[1] + b[3] for b in bx if b[1] < W * 0.75)
    w_left = xs[0]
    e_right = xs[-1] + a.old_frame_w
    out = {}
    def keep(nW, nE):
        # drop the W columns with the fewest frames (hub-side first on ties), and the hub-side E columns
        wl = list(range(nw))
        order = sorted(wl, key=lambda ci: (len(frames[round(xs[ci], 3)]), -ci))
        wk = sorted(set(wl) - set(order[:nw - nW]))
        ek = list(range(len(cols) - nE, len(cols)))
        return wk, ek
    combos = [tuple(map(int, c.split('+'))) for c in a.options.split(',')]
    fig, axs = plt.subplots(1, len(combos), figsize=(10 * len(combos), 9))
    for ax, (tag, wcols, ecols) in zip(axs, [(f'{w_}W_{e_}E', *keep(w_, e_)) for w_, e_ in combos]):
        place = {}
        x = w_left
        for k, ci in enumerate(wcols):
            if k == 1:
                x += SEAM
            if k == len(wcols) - 1 and k >= 2:
                x += SEAM
            place[ci] = x
            x += pitch
        w_end = x - 8.64
        x = e_right
        for ci in reversed(ecols):
            x -= a.frame_w
            place[ci] = x
            x -= 8.64
        e_start = min(place[ci] for ci in ecols)
        room = (e_start - a.s14) - (w_end + a.s14)
        need = hub_hi - hub_lo
        nf = sum(len(frames[round(xs[ci], 3)]) for ci in wcols + ecols)
        out[tag] = dict(w_columns=len(wcols), e_columns=len(ecols), frames_per_die=nf, frames_delta=nf - 128,
                        w_field_end_um=round(w_end, 1), e_field_start_um=round(e_start, 1), s14_each_um=a.s14,
                        hub_room_um=round(room, 1), hub_span_now_um=round(need, 1), hub_deficit_um=round(max(0.0, need - room), 1),
                        hub_slack_um=round(max(0.0, room - need), 1))
        for ci, cx in place.items():
            for f in frames[round(xs[ci], 3)]:
                ax.add_patch(Rectangle((cx, f['origin_um'][1]), a.frame_w, f['height_um'], fc='#9cf' if ci < nw else '#9c9', ec='k', lw=.4))
        for n, x0, y0, w, h in bx:
            clash = x0 < w_end + a.s14 or x0 + w > e_start - a.s14
            ax.add_patch(Rectangle((x0, y0), w, h, fc='#f99' if clash else '#ddd', ec='k', lw=.6))
            ax.text(x0 + w / 2, y0 + h / 2, n.replace('sp_', ''), ha='center', va='center', fontsize=6)
        for xx in (w_end, w_end + a.s14, e_start - a.s14, e_start):
            ax.axvline(xx, color='orange' if xx in (w_end + a.s14, e_start - a.s14) else 'k', lw=.8, ls='--')
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
        r = out[tag]
        ax.set_title(f"{tag}: {r['frames_per_die']} frames; hub room {r['hub_room_um']:.0f} vs span {r['hub_span_now_um']:.0f} "
                     f"-> deficit {r['hub_deficit_um']:.0f} / slack {r['hub_slack_um']:.0f} um", fontsize=9)
    fig.suptitle(f'S81 bf_col fit: frame {a.frame_w} um (was {a.old_frame_w}), street-only clusters, S14 {a.s14} um each; red = hub block outside room at its CURRENT x (a whole-hub shift may still fit when slack >= 0)', fontsize=11)
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    fig.savefig(o / 'bfcol_fit.png', dpi=60)
    (o / 'bfcol_fit.json').write_text(json.dumps(dict(schema='opentallas.s81.bfcol_fit.v1', frame_w_um=a.frame_w,
                                                      pitch_um=pitch, hub_blocks_x_um=[hub_lo, hub_hi], options=out,
                                                      flag='b1/b2 change frames per die: stage map (128 regions) and ROM/layer mapping must be re-partitioned by the compiler / model owner'), indent=1) + '\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
