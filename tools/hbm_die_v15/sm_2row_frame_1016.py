#!/usr/bin/env python3
"""H-SM 2026-10-16: 2-row clock-safe SM frame witness (coordinator option (b)), from the REAL rp4e tile.

Logical source rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv: 8 columns x NP=2 tiles; row/beat bundles run W->E
through tiles from the central front (columns 0-3 west, 4-7 east); gather runs p0 -> p1 -> BE (rp4e gin N / gout S,
gin[k] and gout[k] at identical x, so p0 abuts directly above p1).  Row 1 (top) = the eight p0 tiles, row 2 = the eight
p1 tiles, BE band under row 2, front column in the centre spanning the full height.

Pin windows use the H-DIE cut rule: cut = bits x 0.096 um (2 tracks) / window length; target cut <= 0.55, <= 6 pins/um.
Plan only: no kit, no gate.  Children are the rp4e kit's actual blocks (66381a0f4).
"""
import json, math
from pathlib import Path
D = Path(__file__).resolve().parents[2] / 'results/arch/hbm_die_v15/sm_2row_frame_1016'
fp = json.loads((D / 'rp4e_floorplan_66381a0f4.json').read_text())
TW, TH = fp['die'][2], fp['die'][3]                 # 457.92 x 1529.28
FRONT_W, CLR, BE_H, ROOF = 345.6, 21.6, 237.6, 21.6  # front column (as the landscape frame), clearances, BE band
NHALF = 4                                            # columns per half
W = 2 * NHALF * TW + 2 * CLR + FRONT_W
H = BE_H + CLR + 2 * TH + ROOF
x_front = NHALF * TW + CLR
tiles = []
for row, (p, y) in enumerate([(0, BE_H + CLR + TH), (1, BE_H + CLR)]):
    for c in range(8):
        x = c * TW if c < NHALF else x_front + FRONT_W + CLR + (c - NHALF) * TW
        tiles.append(dict(name=f'g_c[{c}].g_p[{p}].u_t', x=round(x, 3), y=round(y, 3), w=TW, h=TH,
                          orient='MY' if c < NHALF else 'R0', row=row))
be = [dict(name=f'g_c[{c}].u_be', x=t['x'], y=0.0, w=TW, h=BE_H) for c, t in enumerate(tiles[:8])]
front = dict(name='u_front', x=round(x_front, 3), y=0.0, w=FRONT_W, h=round(H, 3))

def window(bits, face, centre, minlen=0.0):
    L = max(minlen, bits * 0.096 / 0.55)
    L = math.ceil(L / 2.16) * 2.16
    return dict(bits=bits, face=face, lo=round(centre - L / 2, 3), hi=round(centre + L / 2, 3), length_um=round(L, 3),
                pins_per_um=round(bits / L, 3), cut=round(bits * 0.096 / L, 4))
xc = x_front + FRONT_W / 2
ports = dict(  # widths from ot_hbm_accel_smh_attn.sv
    xw=1 + 7 + 7 + 2048, sm_hbm=192 + 64 + 1099 + 43, result=1 + 12 + 256 + 1 + 1)
pins = {
    'xw (xw_en/addr/grp/data)': window(ports['xw'], 'N', xc, 360.0),
    'SM_HBM (command/kv_desc/packet/request)': window(ports['sm_hbm'], 'S', xc - 70.2),
    'result (rv/rrow/rdata/fault/schedule_fault)': window(ports['result'], 'S', xc + 140.4),
    'clk + rst_n (regional root entry, root site 60x60 at front centre)': dict(face='N', lo=round(xc + 190.0, 3), hi=round(xc + 195.0, 3), bits=2),
}
assert pins['xw (xw_en/addr/grp/data)']['lo'] >= x_front - CLR and pins['xw (xw_en/addr/grp/data)']['hi'] <= x_front + FRONT_W + CLR
s_lo = min(pins[k]['lo'] for k in pins if pins[k]['face'] == 'S'); s_hi = max(pins[k]['hi'] for k in pins if pins[k]['face'] == 'S')
out = dict(schema='opentallas.hbm.sm_2row_frame.v1', qualification='PLAN_WITNESS_NOT_BUILT',
           tile_source='smh_tile_rp4e 66381a0f4 (claude/hsm-rp4-0030)', tile_um=[TW, TH],
           outline_um=[round(W, 3), round(H, 3)], area_mm2=round(W * H / 1e6, 4), aspect='landscape',
           tile_area_mm2=round(16 * TW * TH / 1e6, 4),
           assumed_portrait_um=[2782.08, 3697.92], assumed_portrait_mm2=round(2782.08 * 3697.92 / 1e6, 4),
           portrait_feasible=False,
           why_not_portrait='16 rp4e tiles alone are %.2f mm2 > %.2f mm2; a row of 8 tiles is %.1f um wide; hard tiles cannot be R90'
                            % (16 * TW * TH / 1e6, 2782.08 * 3697.92 / 1e6, 8 * TW),
           tiles=tiles, be=be, front=front, pins=pins, s_face_span=[s_lo, s_hi],
           we_faces='no SM pins on W/E (tiles abut inside; neighbours keep the 20 um die gap)',
           links=dict(row_hop='tile E face -> next tile W face, abutted (rp4e W y == E y)', gather='p0 gout S -> p1 gin N abutted, same x',
                      be='p1 gout S -> BE directly below', be_cmd_reach_um=round(max(abs(t['x'] + TW / 2 - xc) for t in tiles), 1),
                      xw_to_front='N window directly over the front column'),
           clock='one SM regional root (DIE-CLOCK METHOD 640fa898f): clk at the N face beside xw, root site at the front centre; '
                 'SM-internal subtrees per quadrant (W-p0, W-p1, E-p0, E-p1, front+BE), neighbour budget 80 ps tile-to-tile; '
                 'tile entry pins (clk_hard/pin/oper/region) driven inside the frame, not die pins',
           reset='rst_n beside clk, registered at the front, regional sync reset tree (ot_hbm_accel_smh_rst_tree) per quadrant')
D.mkdir(parents=True, exist_ok=True)
(D / 'witness.json').write_text(json.dumps(out, indent=1) + '\n')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig, ax = plt.subplots(figsize=(12, 10))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, edgecolor='black'))
for t in tiles:
    ax.add_patch(Rectangle((t['x'], t['y']), TW, TH, facecolor='#edf2f5', edgecolor='#708090', lw=.6))
    for b in fp['blocks']:
        bx = t['x'] + (TW - b['x'] - b['w'] if t['orient'] == 'MY' else b['x'])
        ax.add_patch(Rectangle((bx, t['y'] + b['y']), b['w'], b['h'], facecolor='#b9cde0', edgecolor='#708090', lw=.2))
    ax.text(t['x'] + TW / 2, t['y'] + TH / 2, t['name'].replace('.u_t', ''), ha='center', va='center', fontsize=6, rotation=90)
for b in be:
    ax.add_patch(Rectangle((b['x'], 0), TW, BE_H, facecolor='#f6e3c5', edgecolor='#a07040', lw=.5)); ax.text(b['x'] + TW / 2, BE_H / 2, b['name'], ha='center', fontsize=6)
ax.add_patch(Rectangle((front['x'], 0), FRONT_W, H, facecolor='#d8ead2', edgecolor='black')); ax.text(xc, H / 2, 'u_front', rotation=90, ha='center')
for k, p in pins.items():
    y = H if p['face'] == 'N' else 0
    ax.plot([p['lo'], p['hi']], [y, y], lw=6, color='red' if p['face'] == 'N' else 'blue', solid_capstyle='butt')
    ax.text((p['lo'] + p['hi']) / 2, y + (40 if y else -90), k.split(' ')[0], ha='center', fontsize=7)
ax.set(xlim=(-100, W + 100), ylim=(-200, H + 150), aspect='equal',
       title=f'SM 2-row frame (plan witness) {W:.2f} x {H:.2f} um = {W*H/1e6:.2f} mm2; 16 rp4e tiles, front centre, BE band S')
fig.tight_layout(); fig.savefig(D / 'witness.png', dpi=130)
print(json.dumps(dict(outline=out['outline_um'], area=out['area_mm2'], pins=pins, be_cmd_reach_um=out['links']['be_cmd_reach_um']), indent=1))
