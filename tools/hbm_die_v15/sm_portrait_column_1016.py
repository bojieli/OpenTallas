#!/usr/bin/env python3
"""H-SM 2026-10-16: native PORTRAIT-COLUMN SM frame witness (A2P), real rp4 tiles (457.92 x 1529.28), no R90.

Logical source ot_hbm_accel_smh_attn.sv: 8 columns x NP=2 tiles; per (half, p) a 4-tile row chain from the front
(rin/bin W face, rout/bout E face, unchanged); gather p0 gout S -> p1 gin N (same x) -> BE.  Portrait stack, top->bottom:
  BE_W band (soft) | W-p1 row (MX) | ch | W-p0 row (MX) | ch | E-p0 row | ch | E-p1 row | BE_E band (soft)
Every row's head tile abuts the front column at the E edge (W half and E half both flow westward physically).
The W half is MX so its gather/BE end faces N: the N short face (xw) and S short face (SM_HBM/result) wires route over the
soft BE bands into the front.  Pin windows by the H-DIE cut rule (bits x 0.096 / L, <= 0.55, <= 6 pins/um).
Two variants: F108 (narrow front, wires over the BE bands) and F363 (front wide enough to hold the windows itself).
"""
import json, math
from pathlib import Path
D = Path(__file__).resolve().parents[2] / 'results/arch/hbm_die_v15/sm_portrait_column_1016'
fp = json.loads((Path(__file__).resolve().parents[2] / 'results/arch/hbm_die_v15/sm_2row_frame_1016/rp4e_floorplan_66381a0f4.json').read_text())
TW, TH = fp['die'][2], fp['die'][3]
CH, TRK, CUT = 21.6, 0.096, 0.55
BITS = dict(xw=2063, sm_hbm=192 + 64 + 1099 + 43, result=271)

def win(bits):
    return math.ceil(bits * TRK / CUT / 2.16) * 2.16

def variant(front_w):
    w = 4 * TW + front_w
    xw_L = win(BITS['xw']); s_L = win(BITS['sm_hbm']) + 10.8 + win(BITS['result'])
    # wires that land west of the front run horizontally over the BE band to the front
    xw_over = max(0.0, xw_L - front_w) / xw_L * BITS['xw']
    s_over = max(0.0, s_L - front_w) / s_L * (BITS['sm_hbm'] + BITS['result'])
    be_n = max(237.6, math.ceil(xw_over * TRK / CUT / 21.6) * 21.6)
    be_s = max(237.6, math.ceil(s_over * TRK / CUT / 21.6) * 21.6)
    h = be_n + 4 * TH + 3 * CH + be_s
    y = h; rows = []
    y -= be_n; bands = [dict(name='BE_W (c0..c3 u_be)', x=0, y=y, w=4 * TW, h=be_n)]
    for name, orient in [('W-p1', 'MX'), ('W-p0', 'MX'), ('E-p0', 'R0'), ('E-p1', 'R0')]:
        y -= TH; rows.append(dict(name=name, y=round(y, 3), orient=orient))
        if name != 'E-p1': y -= CH
    bands.append(dict(name='BE_E (c4..c7 u_be)', x=0, y=0.0, w=4 * TW, h=be_s))
    tiles = []
    for r in rows:
        half, p = r['name'].split('-')
        for k in range(4):            # k = 0 at the front (head), flowing west
            c = (3 - k) if half == 'W' else (4 + k)
            tiles.append(dict(name=f'g_c[{c}].g_p[{p[1]}].u_t', x=round(4 * TW - (k + 1) * TW, 3), y=r['y'], w=TW, h=TH,
                              orient=r['orient'] + '+MY'))   # MY: rin/bin face the front (E); W half MX+MY = R180
    fx = 4 * TW
    pins = dict(
        xw=dict(face='N', lo=round(w - xw_L, 3), hi=round(w, 3), length=xw_L, bits=BITS['xw'],
                pins_per_um=round(BITS['xw'] / xw_L, 3), cut=round(BITS['xw'] * TRK / xw_L, 4), over_be_bits=round(xw_over)),
        sm_hbm=dict(face='S', lo=round(w - s_L, 3), hi=round(w - s_L + win(BITS['sm_hbm']), 3), length=win(BITS['sm_hbm']),
                    bits=BITS['sm_hbm'], pins_per_um=round(BITS['sm_hbm'] / win(BITS['sm_hbm']), 3),
                    cut=round(BITS['sm_hbm'] * TRK / win(BITS['sm_hbm']), 4)),
        result=dict(face='S', lo=round(w - win(BITS['result']), 3), hi=round(w, 3), length=win(BITS['result']), bits=BITS['result'],
                    pins_per_um=round(BITS['result'] / win(BITS['result']), 3), cut=round(BITS['result'] * TRK / win(BITS['result']), 4)),
        clk_rst=dict(face='E', note='clk + rst_n on the front E long face at mid-height (one regional root, root site in the front)'),
        s_over_be_bits=round(s_over))
    # front -> farthest BE (be_cmd): one equal-age copy register per BE band at the front next to that band
    reach = max(4 * TW - TW / 2, 0) + 0.0
    return dict(front_w=front_w, outline_um=[round(w, 3), round(h, 3)], area_mm2=round(w * h / 1e6, 4),
                be_band_h=[be_n, be_s], tiles=tiles, bands=bands, front=dict(x=fx, y=0, w=front_w, h=round(h, 3)),
                pins=pins, be_cmd='two equal-age copies at the front (one beside each BE band); reach to the farthest BE %.1f um' % reach,
                quadrant_width_8_cols_100gap_um=round(8 * w + 7 * 100, 2))

out = dict(schema='opentallas.hbm.sm_portrait_column.v1', qualification='PLAN_WITNESS_NOT_BUILT',
           tile='rp4 (rp4e 66381a0f4 geometry; rp4f/g one-root ot_hbm_smh_rp4_one 8359eb9d4 same outline)', tile_um=[TW, TH],
           h_die_planned_um=[1807.2, 7755.84],
           variants=dict(F108=variant(108.0), F363=variant(362.88)),
           leaf_pin_changes_needed=[
               'clk: W face -> N face (beside rst_n). Row tiles abut W/E, so a W-face clk is buried in the seam for 3 of 4 tiles per row.',
               'rin/bin W, rout/bout E, gin N, gout S, xs/xss N/S: unchanged (rows stay horizontal; gather stacks p0 over p1 at equal x).'],
           channels='21.6 um between the four tile rows: p1 xs/rst_n/clk access and the p0->p1 gather hop (100 b at equal x)',
           strips='row bundles stay on the abutted W/E faces: 3,705 b over y 249.6-1,281.6 = 3.59 pins/um, cut 0.345')
D.mkdir(parents=True, exist_ok=True)
(D / 'witness.json').write_text(json.dumps(out, indent=1) + '\n')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig, axs = plt.subplots(1, 2, figsize=(10, 15))
for ax, (vn, v) in zip(axs, out['variants'].items()):
    W, H = v['outline_um']
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, edgecolor='black'))
    for b in v['bands']:
        ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], facecolor='#f6e3c5', edgecolor='#a07040')); ax.text(b['w'] / 2, b['y'] + b['h'] / 2, b['name'], ha='center', va='center', fontsize=7)
    for t in v['tiles']:
        ax.add_patch(Rectangle((t['x'], t['y']), TW, TH, facecolor='#edf2f5', edgecolor='#708090', lw=.6))
        mx = 'MX' in t['orient']; my = 'MY' in t['orient']
        for b in fp['blocks']:
            bx = t['x'] + (TW - b['x'] - b['w'] if my else b['x']); by = t['y'] + (TH - b['y'] - b['h'] if mx else b['y'])
            ax.add_patch(Rectangle((bx, by), b['w'], b['h'], facecolor='#b9cde0', edgecolor='#708090', lw=.2))
        ax.text(t['x'] + TW / 2, t['y'] + TH / 2, t['name'].replace('.u_t', ''), rotation=90, ha='center', va='center', fontsize=6)
    f = v['front']; ax.add_patch(Rectangle((f['x'], 0), f['w'], f['h'], facecolor='#d8ead2', edgecolor='black')); ax.text(f['x'] + f['w'] / 2, H / 2, 'u_front', rotation=90, ha='center')
    for k, col, y in [('xw', 'red', H), ('sm_hbm', 'blue', 0), ('result', 'navy', 0)]:
        p = v['pins'][k]; ax.plot([p['lo'], p['hi']], [y, y], lw=6, color=col, solid_capstyle='butt'); ax.text((p['lo'] + p['hi']) / 2, y + (60 if y else -160), k, ha='center', fontsize=7)
    ax.set(xlim=(-150, W + 150), ylim=(-300, H + 200), aspect='equal', title=f'{vn}: {W:.2f} x {H:.2f} um = {v["area_mm2"]:.2f} mm2')
fig.suptitle('SM portrait column (plan witness): 16 rp4 tiles, 4 rows of 4, front at E edge, BE bands N/S')
fig.tight_layout(); fig.savefig(D / 'witness.png', dpi=110)
print(json.dumps({k: dict(outline=v['outline_um'], area=v['area_mm2'], be=v['be_band_h'], quad=v['quadrant_width_8_cols_100gap_um'],
                          xw=v['pins']['xw'], sm_hbm=v['pins']['sm_hbm'], s_over=v['pins']['s_over_be_bits']) for k, v in out['variants'].items()}, indent=1))
