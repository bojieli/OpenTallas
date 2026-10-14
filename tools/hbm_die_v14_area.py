#!/usr/bin/env python3
"""HBM die contract v14 area table (hbmdie 10-14): block areas of a die model (pickle from hbm_r25gq_windows.py
--dump-model or tools/hbm_die_v14 bind job) by kind and master, the free area on a 100-um grid, and the element rows
(real area against slot) carried from the v13 table (results/arch/hbm_die_feasibility_1014/area_v13_1014.json) with the
v14 changes (quadrant COLL, TKM inside the SW engine, SFU growth into the freed equator band, VM8 / hc_eng moves).

    python3 tools/hbm_die_v14_area.py MODEL.pkl --out results/arch/hbm_die_v14/area_v14
"""
import argparse, collections, json, pickle
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('model', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--v13', type=Path, default=ROOT / 'results/arch/hbm_die_feasibility_1014/area_v13_1014.json')
    a = ap.parse_args(argv)
    m = pickle.loads(a.model.read_bytes())
    I = m['insts']
    W, H = 32984.288, 25980.528
    kind_a, mst_a, mst_n = collections.Counter(), collections.Counter(), collections.Counter()
    nx, ny = int(np.ceil(W / 100)), int(np.ceil(H / 100))
    occ = np.zeros((nx, ny), bool)
    for n, (mst, k, x, y, w, h, o) in I.items():
        kind_a[k] += w * h / 1e6
        mst_a[mst] += w * h / 1e6
        mst_n[mst] += 1
        occ[int(x // 100):int(np.ceil((x + w) / 100)), int(y // 100):int(np.ceil((y + h) / 100))] = True
    free = (~occ).sum() * 0.01
    blocks = sum(v for k, v in kind_a.items() if k != 'waypoint')
    v13 = json.loads(a.v13.read_text())
    rows = []
    for r in v13['rows']:
        r = dict(r)
        if r['element'].startswith('SFU'):
            r['v14'] = ('slot grows +216 um into the equator band hb_hc_eng left (v14 hc_eng in the N spine band): '
                        '2,016.144 x 1,311.12 = 2.6434 mm2, usable 1.4531 + 0.4355 = 1.8886 >= real 1.6688 (13 % margin); '
                        'the corridor repair stays an optional SFU-owner improvement')
            r['fit_v14'] = 'FITS (slot change, SFU owner re-pins against the assigned file)'
        elif r['element'].startswith('SM ('):
            r['v14'] = ('UNCHANGED BLOCKER: 32 x 7.238 = 231.6 mm2 of closed SM leaves (no channels) vs 32 x 3.638 = 116.4 mm2 of '
                        'slots; the SM.MATVEC redesign (XP tiles eng_de 112.32 sq + aq / bfm / buf / 4 rd_ln / rdc / sps / xwm '
                        '= 0.127 mm2 a quadrant set) does not change it; SM rows are 1,131.84 tall with 1,209 / 562 um channels '
                        'between rows, so a 2x SM needs the SM owner\'s compacted native frame (FrontC alone 976.32 x 1,192.32 '
                        '> the 1,131.84 slot height)')
            r['fit_v14'] = 'BLOCKER (owner: SM compaction / VM-SM 2240)'
        elif r['element'].startswith('IDX'):
            r['v14'] = 'four corner bands kept (default): 2,965 x 4,374 each, leaf + macro density 73.6 %'
            r['fit_v14'] = r['fit']
        else:
            r['v14'] = 'unchanged'
            r['fit_v14'] = r['fit']
        rows.append(r)
    cq = {k: v for k, v in mst_a.items() if k.startswith('hfd_coll') or k == 'hfd_ckgen' or k.startswith('hfd_vm_')}
    new = [dict(element='quadrant COLL SW (hfd_coll_q3: engine band + 3 hcoll ports + 32-tile TKM)', n=mst_n['hfd_coll_q3'],
                mm2=round(mst_a['hfd_coll_q3'], 4)),
           dict(element='quadrant COLL SE / NW / NE (hfd_coll_q2: engine + 2 hcoll ports)', n=mst_n['hfd_coll_q2'],
                mm2=round(mst_a['hfd_coll_q2'], 4)),
           dict(element='die clock root (hfd_ckgen)', n=mst_n['hfd_ckgen'], mm2=round(mst_a['hfd_ckgen'], 4)),
           dict(element='freed: central hfd_coll 1,399.68 x 1,561.68 + hb_tkm slot 2,255.04 x 1,844.64', n=0,
                mm2=round(-(1399.68 * 1561.68 + 2255.04 * 1844.64) / 1e6, 4))]
    out = dict(schema='opentallas.hbm_die_area.v14', die_mm2=round(W * H / 1e6, 3), blocks_mm2=round(blocks, 3),
               waypoints_mm2=round(kind_a.get('waypoint', 0.0), 3), free_mm2_100um_grid=round(free, 3),
               by_kind={k: round(v, 3) for k, v in sorted(kind_a.items())}, coll_vm={k: round(v, 4) for k, v in cq.items()},
               v14_new=new, rows=rows, model=str(a.model))
    a.out.with_suffix('.json').write_text(json.dumps(out, indent=1) + '\n')
    L = ['# HBM die contract v14: area table (2026-10-14)', '',
         f"Die {W:,.3f} x {H:,.3f} um = {W * H / 1e6:.2f} mm2. v14 plan blocks {blocks:.2f} mm2 + relays "
         f"{kind_a.get('waypoint', 0.0):.2f} mm2; free (100-um grid) {free:.2f} mm2 = {100 * free / (W * H / 1e6):.1f} %.", '',
         '| v14 change | n | mm2 |', '|---|---:|---:|']
    L += [f"| {r['element']} | {r['n']} | {r['mm2']:.4f} |" for r in new]
    L += ['', '| element | n | slot mm2 | real mm2 | real / slot | v14 | status |', '|---|---:|---:|---:|---:|---|---|']
    L += [f"| {r['element']} | {r['n']} | {r['slot_mm2']:.4f} | {r['real_mm2']:.4f} | {r['ratio']:.3f} | {r['v14']} | {r['fit_v14']} |"
          for r in rows]
    L += ['', 'Sources: v13 real-area receipts (area_v13_1014.json); v14 blocks from the model named above.']
    a.out.with_suffix('.md').write_text('\n'.join(L) + '\n')
    print(json.dumps(dict(blocks=round(blocks, 2), free=round(free, 2), new=new)))


if __name__ == '__main__':
    main()
