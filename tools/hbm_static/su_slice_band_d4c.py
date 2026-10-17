#!/usr/bin/env python3
"""H-SU 2026-10-16 (d4c, SU/VM band <= 3.30 mm): re-aspect the SU port-group slice ot_hbm_su_static_pgslice.

Same hard outlines, channels and locality rows as su_slice_band_v6.py (bank r12 369.36x151.2 CLOSED, LIGHT kind0 leaf
151.2^2 CLOSED, HEAVY KIND1 lane PLANNED 166.32x330.48; 20 um channels / edges; row = lanes beside the two-bank stack
they read). The band row height sets the slot height (H-DIE: ~3,150); the slot width is what the rows + the service
column (pgslice bridges, programme SRAM share, two VM bank leaves, RF local copy, reset relays, fill/drain glue) need.

Pins: the band's N/S faces abut the SM rows (no channel), so EVERY pin is on W (core/command side, toward sucore) or E
(LG side, toward the VM banks), at a 0.192 um pitch (4 M4 tracks, 5.21 pins/um <= 6/um guidance); clock/reset entries
move from N to W. Planning geometry only: no standard-cell placement, GRT or timing.
"""
import json, math, sys
from pathlib import Path

CH, EDGE, GRID = 20.0, 20.0, 2.16
BANK, LIGHT, HEAVY = (369.36, 151.2), (151.2, 151.2), (166.32, 330.48)
STACK_H = 2 * BANK[1] + CH                      # 322.4
PITCH = 0.192                                   # um per pin (5.21 / um)
H_SLOT = 3149.28                                # <= 3,150 on the 2.16 grid (1458 x 2.16)

# pgslice ports (RTL ot_hbm_su_static_pgslice, bits); face plan
PORTS_W = dict(control=1742, vmr_cmd=60, vmw_cmd=78, rf_bword=128, rf_bcmd=36, rf_dsec=256, red_sel=12, slice_x=32,
               fault=1)
PORTS_W_COLL = dict(inj_rd=2, inj_addr=160, inj_q=1024, dw_v=2, dw_row=18, dw_d=1024)    # COLLPORT ports (die-bound)
PORTS_CLK = dict(pg_clk=1, clk_lane=256, clk_insert=128, rst_lane_n=32, clk_bcast=4, rst_bcast_n=4, clk_bank=32,
                 clk_bank_macro=192, clk_ctl=1, clk_side=6, rst_n=1, bridge_rst_n=1)          # 658
PORTS_E = {'lg_rq/lg_wq/lg_rr/lg_w_done h0': 17 + 281 + 257 + 1, 'lg_rq/lg_wq/lg_rr/lg_w_done h1': 17 + 281 + 257 + 1}


def heavy_rows():
    """8 rows H | BB | LL | BB | H (2 heavy, 4 banks, 2 LIGHT per row) = 16 heavy, 32 banks, 16 LIGHT."""
    rects, y = [], EDGE
    rh = max(HEAVY[1], STACK_H)
    for _ in range(8):
        x = EDGE
        for k in ('H', 'BB', 'LL', 'BB', 'H'):
            if k == 'H':
                rects.append(('heavy', x, y, *HEAVY)); x += HEAVY[0] + CH
            elif k == 'BB':
                rects += [('bank', x, y, *BANK), ('bank', x, y + BANK[1] + CH, *BANK)]; x += BANK[0] + CH
            else:
                rects += [('light', x, y, *LIGHT), ('light', x, y + LIGHT[1] + CH, *LIGHT)]; x += LIGHT[0] + CH
        y += rh + CH
    return rects, x - CH, y - CH


def light_rows(per_row):
    """rows of (LL | BB) x per_row until 32 banks + 32 LIGHT are placed."""
    rects, y, nb, nl, uw = [], EDGE, 0, 0, 0
    while nb < 32 or nl < 32:
        x = EDGE
        for k in ('LL', 'BB') * per_row:
            if k == 'BB' and nb < 32:
                rects += [('bank', x, y, *BANK), ('bank', x, y + BANK[1] + CH, *BANK)]; nb += 2; x += BANK[0] + CH
            elif k == 'LL' and nl < 32:
                rects += [('light', x, y, *LIGHT), ('light', x, y + LIGHT[1] + CH, *LIGHT)]; nl += 2; x += LIGHT[0] + CH
        uw = max(uw, x - CH); y += STACK_H + CH
    return rects, uw, y - CH


def service(width, uw, uh):
    """service area = right column beside the rows + top strip above them (inside the edges)."""
    col_w = max(0.0, width - uw - CH - EDGE)
    col = col_w * (H_SLOT - 2 * EDGE)
    strip_h = max(0.0, H_SLOT - uh - CH - EDGE)
    strip = strip_h * (uw - EDGE)
    return dict(column_w=round(col_w, 2), strip_h=round(strip_h, 2), mm2=round((col + strip) / 1e6, 4))


def windows(face_ports, start, gap=21.6):
    out, y = [], start
    for name, bits in face_ports.items():
        span = bits * PITCH
        out.append(dict(port=name, bits=bits, lo=round(y, 3), hi=round(y + span, 3), span_um=round(span, 3),
                        pins_per_um=round(bits / span, 2)))
        y += span + gap
    return out, y


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    old = dict(w=1797.12, h=2825.28, mm2=round(1797.12 * 2825.28 / 1e6, 4))
    cases = {}
    hr, huw, huh = heavy_rows()
    for name, (rects, uw, uh), width in (('heavy_G0G1_1612.8', (hr, huw, huh), 1612.8),
                                          ('light_G2G3_1612.8', light_rows(2), 1612.8),
                                          ('light_G2G3_1290', light_rows(2), 1290.0),
                                          ('heavy_G0G1_min', (hr, huw, huh), None)):
        fits_h = uh + EDGE <= H_SLOT + 1e-6
        if width is None:
            width = math.ceil((uw + EDGE) / 0.216) * 0.216        # rows only, zero service column
        hard = sum(r[3] * r[4] for r in rects) / 1e6
        slot = width * H_SLOT / 1e6
        cnt = {k: sum(1 for r in rects if r[0] == k) for k in ('bank', 'heavy', 'light')}
        cases[name] = dict(width=round(width, 3), height=H_SLOT, slot_mm2=round(slot, 4), rows_w=round(uw, 2),
                           rows_h=round(uh, 2), fits_height=fits_h, fits_width=uw + EDGE <= width + 1e-6, counts=cnt,
                           hard_mm2=round(hard, 4), hard_util=round(hard / slot, 3), service=service(width, uw, uh),
                           rects=[[k, round(x, 2), round(y, 2), w, h] for k, x, y, w, h in rects])
    # pins (same plan for every slice): W = commands + RF + COLLPORT + clocks; E = the two LG ports
    w_ports = {**PORTS_CLK, **PORTS_W, **PORTS_W_COLL}
    wwin, wend = windows({'clock_reset (658 entries)': sum(PORTS_CLK.values()), **PORTS_W, **PORTS_W_COLL}, 64.8)
    ewin, eend = windows(PORTS_E, 1200.0)
    pins = dict(pitch_um=PITCH, pins_per_um=round(1 / PITCH, 2), N='none (abuts SM row)', S='none (abuts SM row)',
                W=dict(bits=sum(w_ports.values()), windows=wwin, used_um=round(wend - 64.8, 1)),
                E=dict(bits=sum(PORTS_E.values()), windows=ewin, used_um=round(eend - 1200.0, 1)),
                face_avg_pins_per_um=dict(W=round(sum(w_ports.values()) / H_SLOT, 3), E=round(sum(PORTS_E.values()) / H_SLOT, 3)),
                note='old grant: E 2x556 b at 10.0/um, W SU_CORE 256 b windows at 10.0/um, 658 clock/reset entries on N')
    summ = dict(schema='opentallas.hsu.su_slice_band_d4c.v1', author='Claude H-SU/PGSLICE', date='2026-10-16',
                old_slot=old, slot_h=H_SLOT, outlines=dict(bank_r12=BANK, light_kind0_leaf=LIGHT, heavy_planned=HEAVY,
                                                          channel=CH, edge=EDGE),
                cases={k: {kk: vv for kk, vv in v.items() if kk != 'rects'} for k, v in cases.items()}, pins=pins,
                status='PLANNING geometry (rectangles + pin windows). pgslice is RTL-only: no cluster kit; VM bank leaf not '
                       'started; heavy KIND1 outline planned from synth. No placement / GRT / timing.')
    (out / 'band_d4c.json').write_text(json.dumps(summ, indent=1) + '\n')
    (out / 'band_d4c_rects.json').write_text(json.dumps({k: v['rects'] for k, v in cases.items()}) + '\n')
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    show = ['heavy_G0G1_1612.8', 'light_G2G3_1612.8', 'light_G2G3_1290']
    fig, axs = plt.subplots(1, 3, figsize=(14, 9))
    col = dict(bank='#4a78c2', heavy='#d0632a', light='#5aa55a')
    for ax, name in zip(axs, show):
        v = cases[name]; W = v['width']
        ax.add_patch(Rectangle((0, 0), W, H_SLOT, fill=False, lw=1.5, ec='k'))
        for k, x, y, w, h in v['rects']:
            ax.add_patch(Rectangle((x, y), w, h, fc=col[k], ec='k', lw=0.3))
        s = v['service']
        if s['column_w'] > 0:
            ax.add_patch(Rectangle((v['rows_w'] + CH, EDGE), s['column_w'], H_SLOT - 2 * EDGE, fc='#dddddd', ec='k', lw=0.3, hatch='//'))
        if s['strip_h'] > 0:
            ax.add_patch(Rectangle((EDGE, v['rows_h'] + CH), v['rows_w'] - EDGE, s['strip_h'], fc='#dddddd', ec='k', lw=0.3, hatch='//'))
        for wdw in pins['W']['windows']:
            ax.plot([-8, -8], [wdw['lo'], wdw['hi']], color='m', lw=3)
        for wdw in pins['E']['windows']:
            ax.plot([W + 8, W + 8], [wdw['lo'], wdw['hi']], color='m', lw=3)
        ax.set_xlim(-40, max(c['width'] for c in cases.values()) + 40); ax.set_ylim(-20, H_SLOT + 60); ax.set_aspect('equal')
        ax.set_title(f"{name}\n{W} x {H_SLOT} = {v['slot_mm2']} mm2, hard util {v['hard_util']}\n"
                     f"service {s['mm2']} mm2 (col {s['column_w']}, strip {s['strip_h']})", fontsize=8)
    fig.suptitle('pgslice d4c re-aspect (bank blue, heavy orange, LIGHT green, service grey; pins magenta: W cmds/RF/COLL/clk, E LG; 5.2/um)', fontsize=9)
    fig.tight_layout(); fig.savefig(out / 'band_d4c.png', dpi=110)
    print(json.dumps(summ['cases'], indent=1)); print(json.dumps({k: v for k, v in pins.items() if k not in ('W', 'E')}))
    print('W used', pins['W']['used_um'], 'E used', pins['E']['used_um'])


if __name__ == '__main__':
    main()
