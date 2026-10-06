#!/usr/bin/env python3
"""Per-view minimum IO arrival credit for the station hold model (coordinator decision 2026-10-06).

min delay of a ck-domain IO bit = launching flop clk->Q at FF (inputs only: the upstream station's pin-launch flop;
our own outputs already time their flop) + the minimum die wire to the connected pin.  Wire: the r16g die model
(tools/hbm_die_views.py model(), the floorplan of results/rtl/hbm_accel_die_floorplan_20261005) -- for every
instance of the view and every bus on one of its ck-domain IO ports, the Manhattan gap between the bounding box of
that port's pins and the bounding box of the connected port's pins on the other endpoint (instance outline when the
other master has no generator pin record); the minimum over instances/buses/ports, per direction.  Delay per um:
50 % of the measured FF wire delay per um (routed SPEF, 400 two-pin nets >= 60 um in M1_hfd_meso_r1 and
M1_hfd_gath_r10: 0.2249 / 0.2223 ps/um mean -> 0.112 ps/um).  clk->Q: DFFHQNx1 FF NLDM minimum 32.2 ps.

  stn_io_min.py --ports DIR --views physical/hbm_accel_die_views/stations > io_min_delay.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_die_views as V  # noqa: E402

PS_PER_UM = round(0.5 * (0.2249 + 0.2223) / 2, 4)
CLKQ_FF_PS = 32.2


def xf(rect, it, w, h):
    a, b, c, d = rect
    if it.orient in ('MY', 'R180'):
        a, c = w - c, w - a
    if it.orient in ('MX', 'R180'):
        b, d = h - d, h - b
    return (it.x + a, it.y + b, it.x + c, it.y + d)


def gap(r, s):
    dx = max(0.0, max(r[0], s[0]) - min(r[2], s[2]))
    dy = max(0.0, max(r[1], s[1]) - min(r[3], s[3]))
    return dx + dy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ports', required=True)
    ap.add_argument('--views', required=True)
    a = ap.parse_args()
    m, pw, M, real = V.model()
    by = {it.name: it for it in m['insts']}
    pr = {}

    def port_box(mst, port, it):
        if mst not in pr:
            f = Path(a.ports) / mst / 'ports.json'
            pr[mst] = json.loads(f.read_text()) if f.exists() else None
        rec = pr[mst]
        if not rec or port not in rec['ports']:
            return (it.x, it.y, it.x + it.w, it.y + it.h)
        ps = rec['ports'][port]['pins']
        bb = (min(p[2] for p in ps), min(p[3] for p in ps), max(p[4] for p in ps), max(p[5] for p in ps))
        return xf(bb, it, rec['w_um'], rec['h_um'])

    out = dict(method=__doc__.split('\n\n')[0], ps_per_um=PS_PER_UM, clkq_ff_ps=CLKQ_FF_PS, views={})
    for d in sorted(Path(a.views).glob('hfd_*')):
        mst = d.name
        mp = json.loads((d / 'map.json').read_text())
        inp = {k.split('[')[0] for k, v in mp['ins'].items() if v == 'ck'} - {'rst'}
        outp = {k.split('[')[0] for k, v in mp['map'].items() if v['dom'] == 'ck'}
        if not inp and not outp:
            continue
        best = {'in': None, 'out': None}
        for bid, cls, bits, eps in m['buses']:
            for inst, port in eps:
                if inst == 'TOP' or by[inst].master != mst or port not in inp | outp:
                    continue
                it = by[inst]
                mine = port_box(mst, port, it)
                for inst2, port2 in eps:
                    if inst2 in ('TOP', inst):
                        continue
                    it2 = by[inst2]
                    g = gap(mine, port_box(it2.master, port2, it2))
                    for k in (('in',) if port in inp else ()) + (('out',) if port in outp else ()):
                        if best[k] is None or g < best[k][0]:
                            best[k] = (round(g, 3), inst, port, inst2, port2)
        rec = {}
        for k, v in best.items():
            if v is None:
                continue
            ps = round(v[0] * PS_PER_UM + (CLKQ_FF_PS if k == 'in' else 0.0), 2)
            rec[k] = dict(min_wire_um=v[0], min_delay_ps=ps, via=dict(inst=v[1], port=v[2], to=v[3], to_port=v[4]))
        out['views'][mst] = rec
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
