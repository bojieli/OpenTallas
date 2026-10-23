"""Open the W-column service corridor at the dvs_W5 west face; GEN remains authority.

dvw_st_wi (tt_ctlm -> dvs_W5, 1,088 b) failed P2R in r20 (and is next in r23/r24):
end sites 60 / free 3 / reached 0 at P1 (1814, 11506).  Its landing-sized frame is
bits/6 + 4 = 185.8 um wide; the corridor between io_collective's E face (x 1563.8)
and dvs_W5's W face (x 1814.4) is 250.6 um.  Every W5 west-face wide bus
(cmd/hr/st/dd/dr/ss/ag, 26-28 frames each, plus the ar/rd/cc io_collective words)
lands in the face band y 11083..12143 inside that corridor, so a st_wi frame can
share no corridor row with any other frame and its terminal neighbourhood is
saturated.

Geometry fix: the collective block group (io_collective + its zero-cycle UCIe PHY
io_ucie + the two SerDes PHYs below it) moves south by DY into the free W-column
band (y 0..5096 was empty), rigidly, so every intra-group lane keeps its length
(UCIe lanes must stay at zero cycles).  The W5 face band then faces an open
W column (x 777.8..1814.4 beside io_ucie, 0..1814.4 above it) instead of a
250.6-um slot.  io_serdes (SerDes0, above) stays: its lane to io_collective
grows by DY (LX0 is compiled into the collective calendar, priced cycles).
The source-pinned native origin plan is translated by the same DY (a multiple of
43.2 um keeps every site / track snap).
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

GROUP = ('io_collective', 'io_ucie', 'io_serdes_1', 'io_serdes_2')
SEEDS = {'io_collective': (0.0, 9969.492), 'io_ucie': (0.0, 14244.108),
         'io_serdes_1': (0.0, 7541.436), 'io_serdes_2': (0.0, 5096.1), 'dvs_W5': (1814.4, 10756.8)}
DY = 3456.0              # 80 x 43.2
BOTTOM_UM = 172.8        # the W5 cluster column's bottom row edge
# st_wi landing-sized frame (relay_frame, FWD_LANES + LAND_SIZE, shape ns): w = up(bits/6 + 4, GX), h = BWP_H
ST_FRAME = (185.76, 60.48)
ST_P1 = (1814.4, 11506.0)
ST_DE = 337.0
W5_BAND = (11083.0, 12143.0)


def rect(i):
    return (i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h'])


def overlap(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def corridor(plan, y0, y1, x_face):
    """narrowest free x span west of x_face over y0..y1 (W-column instances only)."""
    west = [rect(i) for i in plan['insts'] if i['x'] < x_face - 1 and i['m'] != 'outline_marker'
            and i['y'] < y1 and i['y'] + i['h'] > y0 and i['w'] > 100]
    return round(x_face - max((r[2] for r in west), default=0.0), 3), sorted({i['n'] for i in plan['insts']
            if i['x'] < x_face - 1 and i['y'] < y1 and i['y'] + i['h'] > y0 and i['w'] > 100})


def st_end_sites(plan):
    """free st_wi frame corners (21.6 grid, source macros only) whose centre is within De (L1) of P1."""
    W, H = ST_FRAME
    rs = [rect(i) for i in plan['insts'] if i['m'] != 'outline_marker']
    n = free = 0
    x = 0.0
    while x + W <= ST_P1[0] + 1e-6:
        y = ST_P1[1] - ST_DE - H
        while y <= ST_P1[1] + ST_DE:
            c = (x + W / 2, y + H / 2)
            if abs(c[0] - ST_P1[0]) + abs(c[1] - ST_P1[1]) <= ST_DE:
                n += 1
                free += not any(overlap((x, y, x + W, y + H), r) for r in rs)
            y = round(y + 21.6, 6)
        x = round(x + 21.6, 6)
    return dict(candidates=n, free_of_macros=free)


def expand(plan, dy=DY):
    out = copy.deepcopy(plan)
    by = {i['n']: i for i in out['insts']}
    for n, xy in SEEDS.items():
        if n not in by or any(abs(by[n][k] - v) > .0011 for k, v in zip(('x', 'y'), xy)):
            raise ValueError('W-column IO seed geometry differs: ' + n)
    if abs(dy / 43.2 - round(dy / 43.2)) > 1e-9:
        raise ValueError('DY must stay on the 43.2-um lattice')
    moved = []
    for n in GROUP:
        i = by[n]
        before = [i['x'], i['y']]
        i['y'] = round(i['y'] - dy, 3)
        moved.append(dict(instance=n, before_xy=before, after_xy=[i['x'], i['y']]))
    if min(by[n]['y'] for n in GROUP) < BOTTOM_UM - 1e-3:
        raise ValueError('W-column IO group leaves the die bottom')
    mv = {n: rect(by[n]) for n in GROUP}
    for i in out['insts']:
        if i['n'] in GROUP or i['m'] == 'outline_marker':
            continue
        for n, r in mv.items():
            if overlap(r, rect(i)):
                raise ValueError(f'W-column IO move overlaps {n} with {i["n"]}')
    coll_top = by['io_collective']['y'] + by['io_collective']['h']
    if coll_top > W5_BAND[0] - 400.0:
        raise ValueError(f'io_collective top {coll_top} still within 400 um of the W5 face band')
    slot = out['slice_slot_plan']
    before_c = corridor(plan, *W5_BAND, SEEDS['dvs_W5'][0])
    after_c = corridor(out, *W5_BAND, SEEDS['dvs_W5'][0])
    out['wcol_io_south_channel'] = dict(
        schema='opentallas.qwen.wcol_io_south_channel.v1', dy_um=-dy, moved=moved,
        w5_face_band_um=list(W5_BAND),
        corridor_at_w5_band_um=dict(before=before_c[0], before_blocks=before_c[1], after=after_c[0], after_blocks=after_c[1]),
        st_wi_end_sites_macros_only=dict(before=st_end_sites(plan), after=st_end_sites(out), frame_um=list(ST_FRAME),
                                         P1=list(ST_P1), De=ST_DE),
        lane_effect='io_collective/io_ucie/io_serdes_1/io_serdes_2 rigid (UCIe 0-cycle lane kept); io_serdes (SerDes0) '
                    'lane to io_collective + dy (LX0 compiled into the collective calendar); W5<->io_collective ar/rd/cc '
                    'words and io_collective_cmd_free grow by ~dy (relay stages, schedule recompiled from this die)',
        planned_die_um=slot['die_um'], reticle_um=slot['reticle_um'],
        scope='source geometry only; preserve reservations and clock endpoints; actual GEN decides all placement and transport')
    return out


def shift_native(native, plan_before, dy=DY):
    out = copy.deepcopy(native)
    by = {i['n']: i for i in plan_before['insts']}
    for e in out['entries']:
        if e['instance'] in GROUP:
            b = e['before']
            if abs(b[1] - by[e['instance']]['y']) > .0011:
                raise ValueError('native origin seed differs: ' + e['instance'])
            e['before'] = [b[0], round(b[1] - dy, 3), b[2], b[3]]
            e['after_xy'] = [e['after_xy'][0], round(e['after_xy'][1] - dy, 3)]
            if e['after_xy'][1] < 0:
                raise ValueError('native origin below the die: ' + e['instance'])
            e['translated_by_um'] = [0.0, -dy]
    out['source'] = str(native.get('source')) + f' + wcol_io_south_channel dy -{dy} (43.2-um lattice: site/track snap kept)'
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('plan')
    p.add_argument('--native', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--native-out', required=True)
    p.add_argument('--dy', type=float, default=DY)
    a = p.parse_args()
    src, nat = Path(a.plan), Path(a.native)
    d, n = json.loads(src.read_text()), json.loads(nat.read_text())
    out = expand(d, a.dy)
    out['wcol_io_south_channel']['source_plan_sha256'] = hashlib.sha256(src.read_bytes()).hexdigest()
    nout = shift_native(n, d, a.dy)
    nout['source_native_plan_sha256'] = hashlib.sha256(nat.read_bytes()).hexdigest()
    Path(a.out).write_text(json.dumps(out, indent=2) + '\n')
    Path(a.native_out).write_text(json.dumps(nout, indent=2) + '\n')
    print(json.dumps(out['wcol_io_south_channel'], indent=1))


if __name__ == '__main__':
    main()
