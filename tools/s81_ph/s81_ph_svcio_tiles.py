#!/usr/bin/env python3
"""CLAUDE S81-PH svc IO hub r3: pin plans of the 4 IO tiles (dsfd_svcio_q / _od / _ad / _x), each sitting at its own
svc slab N-face pin group (exact slab pin x), quadrant side on the S face; updates physical/s81_ph_views/svc/composition.json
(u_io -> the 4 tiles)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s81_ph_coll_tiles import Plan, ROOT, r4, P   # noqa: E402

SW, SH, H = 8500.032, 1576.776, 129.6
G = 0.432                                   # x0 grid (lcm of the 0.048 track and 0.054 site pitches)
W_OD, BAD_Y, FI_Y = 216.0, 64.812, 58.044      # od tile width, bad pin (E face) / fi pin (W face) y in their tiles
FS_WH = (17.256, 30.216)                    # dsfd_stnh_512x1 (physical/s81_die_views/views/dsfd_stnh_512x1)


def main():
    slab = json.loads((ROOT / 'physical/s81_ph_views/ports_ph/layer/dsfd_svc/ports.json').read_text())['ports']

    def north(pl, x0, names):
        for sp, tp in names:
            pl.dirs[tp] = ('output' if sp != 'q' else 'input', slab[sp]['bits'])
            for nm, ly, a, b, c, d in slab[sp]['pins']:
                pl.put(tp, int(nm.split('[')[1][:-1]), 'N', 'M5', (a + c) / 2 - x0)

    def clk(pl, x):
        pl.bus('ck', 1, 'input', 'N', 'M5', x); pl.bus('rst', 1, 'input', 'N', 'M5', x + 1.92)

    tiles = []
    # q tile: q pins 8121.7 .. 8146.4
    x0 = round(8121.0 / G) * G; W = 270.0
    pl = Plan('dsfd_svcio_q', W, H); north(pl, x0, [('q', 'q')]); clk(pl, 60.0)
    pl.bus('q_q', 2060, 'output', 'S', 'M5', 10.0)
    pl.emit('svc IO hub r3: q pin register -> 4 replicas -> q_q (S face, one 515-b group per quadrant)'); tiles.append((pl.m, x0, W))
    # ad tile: ad 8068.5 .. 8117.7, af 8119.7 -> tile ends before the q tile
    W = 269.568; x0 = round((8121.0 - W) / G) * G
    pl = Plan('dsfd_svcio_ad', W, H); north(pl, x0, [('ad', 'ad'), ('af', 'af')]); clk(pl, 20.0)
    pl.bus('fault', 1, 'output', 'N', 'M5', 30.0)
    # r3b route (e87322073-b): GRT-0116 with 2,570 S-face pins on every M5 track -> a0 on every 2nd S track,
    # a1 on the W face (M4, every 2nd track)
    x = pl.bus('a0_v', 4, 'input', 'S', 'M5', 4.8); x = pl.bus('a0_d', 2048, 'input', 'S', 'M5', x, step=2)
    x = pl.bus('a0_r', 4, 'output', 'S', 'M5', x)
    y = pl.bus('a1_v', 1, 'input', 'W', 'M4', 6.0); y = pl.bus('a1_d', 512, 'input', 'W', 'M4', y, step=2)
    y = pl.bus('a1_r', 1, 'output', 'W', 'M4', y)
    pl.bus('fi', 1, 'input', 'W', 'M4', y + 2.4)
    assert x < W - 1, x
    pl.emit('svc IO hub r3: a0 frame-atomic merge + a1 skid -> ad / af; fault (sticky; od tile fault in on fi)'); tiles.append((pl.m, x0, W))
    # x tile: xd 7425.8 .. 7450.5, xf 7452.5
    W = 108.0; x0 = round(7400.0 / G) * G
    pl = Plan('dsfd_svcio_x', W, H); north(pl, x0, [('xd', 'xd'), ('xf', 'xf')]); clk(pl, 80.0)
    x = pl.bus('x_v', 1, 'input', 'S', 'M5', 4.8); x = pl.bus('x_d', 512, 'input', 'S', 'M5', x, step=1)
    pl.bus('x_r', 1, 'output', 'S', 'M5', x)
    pl.emit('svc IO hub r3: x skid -> xd / xf'); tiles.append((pl.m, x0, W))
    # od tile: od 7070.7 .. 7095.4, of 7097.4
    W = 216.0; x0 = round(6990.0 / G) * G
    pl = Plan('dsfd_svcio_od', W, H); north(pl, x0, [('od', 'od'), ('of', 'of')]); clk(pl, 150.0)
    x = pl.bus('od_v', 4, 'input', 'S', 'M5', 4.8); x = pl.bus('od_d', 2048, 'input', 'S', 'M5', x, step=1)
    pl.bus('od_r', 4, 'output', 'S', 'M5', x)
    pl.bus('bad', 1, 'output', 'E', 'M4', H / 2)
    pl.emit('svc IO hub r3: od frame-atomic merge -> od / of; bad (sticky) to the ad tile fi'); tiles.append((pl.m, x0, W))
    f = ROOT / 'physical/s81_ph_views/svc/composition.json'
    comp = json.loads(f.read_text())
    comp['instances'] = [i for i in comp['instances'] if i['inst'] != 'u_io'] + \
        [dict(inst=f'u_io.u_{m.split("_")[-1]}', master=m, xy=[r4(x0), r4(SH - H)], orient='R0') for m, x0, W in tiles]
    # s81-die-2 2026-10-08 (RQ-2, reviewer APPROVED 22:30): the od bad -> ad fi hop crosses the x tile (~645 um); one
    # common-clock fault station u_io.u_fs (ot_s81ph_svc_io_t FSTN 1; die view dsfd_stnh_512x1, 1 bit used) at its
    # midpoint, just below the hub row.  fault +1 cycle (status only).
    at = {m: (x0, W) for m, x0, W in tiles}
    bad = (at['dsfd_svcio_od'][0] + W_OD, SH - H + BAD_Y)
    fi = (at['dsfd_svcio_ad'][0], SH - H + FI_Y)
    fx = r4(round(((bad[0] + fi[0]) / 2 - FS_WH[0] / 2) / G) * G)
    fy = r4(SH - H - FS_WH[1] - 4.32)
    fc = (fx + FS_WH[0] / 2, fy + FS_WH[1] / 2)
    comp['instances'].append(dict(inst='u_io.u_fs', master='dsfd_stnh_512x1', xy=[fx, fy], orient='R0'))
    md = lambda a, b: r4(abs(a[0] - b[0]) + abs(a[1] - b[1]))
    comp['io_hub_fault'] = dict(station='u_io.u_fs', bad_to_station_um=md(bad, fc), station_to_fi_um=md(fc, fi),
                                direct_um=md(bad, fi), cycles_added=1, scope='fault status only')
    comp['io_hub'] = ('r3: four tiles at their pin groups (rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io_tiles.sv, composition '
                      'ot_s81ph_svc_io_t FSTN 1); u_io.u_od.bad -> u_io.u_fs (fault station) -> u_io.u_ad.fi (die nets, flops '
                      'at every end); svc fault = u_io.u_ad.fault')
    f.write_text(json.dumps(comp, indent=1) + '\n')
    print([(m, r4(x0), W) for m, x0, W in tiles])


if __name__ == '__main__':
    main()
