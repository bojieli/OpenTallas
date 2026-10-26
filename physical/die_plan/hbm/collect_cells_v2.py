#!/usr/bin/env python3
"""Collect cell-count and pin evidence for the HBM v2 planned hard cores (HBM-P3-TAPS, 2026-10-23).

Run ONCE by hand (needs ot-epyc5 scratch + the local closed archive table); its outputs are committed and are the
only inputs taps_cores_v2.py reads, so run_v2.sh stays reproducible offline:
  inputs/cells_evidence.json   per as-built master: cells, basis, macros, LEF outline, pin layer phases
  cores/pins/<master>.json     as-built boundary pins (core frame, R0) from the r18h5 die views (LEF PIN rect centre)

Sources, best first (the label goes into the plan):
  CLOSED  closed-archive ORFS run of that element (std cells = finish stdcell - tapcell, the run whose die area
          matches the r18h5 view outline; or_capacity_runs.csv from the 06:12 L1-cap study)
  YOSYS   Yosys mapped cell count (design-hierarchy total) of the r18g/r14/r15 view synthesis (.stat)
  SYNAREA r18h5 view synthesis std-cell area (views/synth/<m>/meta.json std_area_um2) / 0.110 um2 per Yosys cell
          (0.110 = the measured Yosys area/cell of pgslice_lg 0.110, hc_root 0.095, coll_q2 0.126, sm_group 0.121)
  P&R adds buffers/hold cells (typ. +10..30 %) on top of YOSYS/SYNAREA; cores are budgeted <= 350k Yosys cells.

usage: collect_cells_v2.py --views views.json --synth-meta syn_evidence.json --lefs <dir> --csv or_capacity_runs.csv
"""
import argparse, csv, json, os, re, sys

A_CELL = 0.110

# Yosys design-hierarchy splits read from the .stat files (path, module tree, cells incl. submodules).  These are the
# split proposals' evidence; hier.py prints them.
SPLITS = {
    'ot_hbm_su_static_pgslice_lg__exp': dict(
        stat='ot-epyc5:/srv/opentallas-scratch/claude/hbmc-r18g-1021/chainsM/syn/ot_hbm_su_static_pgslice_lg__pv0/'
             'ot_hbm_su_static_pgslice_lg__pv0.stat',
        total=5299195, glue=36980,
        parts=[('lane_exp', 15, 206175 + 3366), ('lane_exp_l', 1, 231376 + 3366), ('lane', 16, 73754 + 3366),
               ('side', 1, 412786), ('pretree', 1, 211003)],
        note='pv0..pv7 (SU0/SU1): 32 lanes (16 with v41x exp, 16 plain) + side (softplus 223k, rsqrt 81k, exp 79k) '
             '+ reduction pretree; each lane core carries its pinned VM bank (3,366 cells + 6 SRAM 128x256 = '
             '192/32), so the macros sit inside the lane cores; top-level glue 37k flattened in the partition'),
    'ot_hbm_su_static_pgslice_lg__plain': dict(
        stat='ot-epyc5:/srv/opentallas-scratch/claude/hbmc-r18g-1021/chainsM/syn/ot_hbm_su_static_pgslice_lg__pv8/'
             'ot_hbm_su_static_pgslice_lg__pv8.stat',
        total=2745129, glue=37126,
        parts=[('lane', 32, 73792 + 3366), ('pretree', 1, 212295)],
        note='pv8..pv15 (SU2/SU3): 32 plain lanes + reduction pretree; each lane core carries its pinned VM bank '
             '(3,366 cells + 6 SRAM 128x256); top-level glue 37k flattened'),
    'ot_hbm_hc_root_static': dict(
        stat='ot-epyc5:/srv/opentallas-scratch/claude/codex-hbm-r14-release-1021/chainB/syn/ot_hbm_hc_root_static/'
             'ot_hbm_hc_root_static.stat',
        total=1514498, glue=95748,
        parts=[('hc_tail', 2, 673210), ('hcp_sys1', 1, 56692)],
        note='2 x ot_hbm_hc_tail_unit_static 673k (each OVER the cap: the 10-23 L1 study lists hbm_hc_tail_child '
             '0.63-0.68M as never closed) -> each tail must split again (RTL: tail stage halves) '),
    'ot_hfd_coll_q2_hard_v8g': dict(
        stat='ot-epyc5:/srv/opentallas-scratch/claude/codex-hbm-r15-native32-bays-1021/chainB/repair01/syn/'
             'ot_hfd_coll_q2_hard_v8g/ot_hfd_coll_q2_hard_v8g.stat',
        total=465018, glue=0,
        parts=[('ring_ag', 1, 121663), ('reduce', 1, 120719), ('body', 1, 222636)],
        note='body 445 + ring_ag 122k + reduce_static 121k + 17 qso + rest'),
}


def lef_pins(fn):
    size, pins, cur, use, got = None, [], None, None, False
    layer = None
    for l in open(fn):
        t = l.split()
        if not t:
            continue
        if t[0] == 'SIZE' and size is None:
            size = [float(t[1]), float(t[3])]
        elif t[0] == 'PIN':
            cur, use, got, layer = t[1], None, False, None
        elif t[0] == 'USE' and cur:
            use = t[1].rstrip(';')
        elif t[0] == 'LAYER' and cur:
            layer = t[1]
        elif t[0] == 'RECT' and cur and not got and use not in ('POWER', 'GROUND'):
            x0, y0, x1, y1 = map(float, t[1:5])
            pins.append(dict(name=cur, layer=layer, x=round((x0 + x1) / 2, 4), y=round((y0 + y1) / 2, 4),
                             clock=use == 'CLOCK'))
            got = True
        elif t[0] == 'END' and len(t) > 1 and t[1] == cur:
            cur = None
        elif t[0] == 'OBS':
            cur = None
    return size, pins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--views', required=True)
    ap.add_argument('--synth-meta', required=True)
    ap.add_argument('--lefs', required=True)
    ap.add_argument('--csv', required=True)
    ap.add_argument('--keep', help='file: masters whose pins_file the plan references (taps_cores_v2.py --list-pins)')
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()
    views = json.load(open(a.views))
    syn = json.load(open(a.synth_meta))
    runs = {}
    for r in csv.DictReader(open(a.csv)):
        runs.setdefault(r['el'], []).append(r)
    os.makedirs(os.path.join(a.out, 'cores', 'pins'), exist_ok=True)
    keep = set(open(a.keep).read().split()) if a.keep else set()
    ev = {}
    for fn in sorted(os.listdir(a.lefs)):
        m = fn[:-4]
        base = re.sub(r'__pv\d+$', '', m)
        size, pins = lef_pins(os.path.join(a.lefs, fn))
        v = views.get(m, {})
        s = syn.get(m, {})
        e = dict(base=base, view=v.get('kind'), lef_um=size, pins=len(pins),
                 clock_pins=sorted(p['name'] for p in pins if p['clock'])[:8],
                 macros={k: x[0] for k, x in (s.get('macros') or {}).items()},
                 std_area_um2=s.get('std_area_um2'), source=v.get('source'))
        cl = runs.get(base) or []
        if v.get('kind', '').startswith('ROUTED') and cl and size:
            area = size[0] * size[1]
            best = min(cl, key=lambda r: (abs(float(r['die_um2']) - area) / area, -int(r['std'])))
            if abs(float(best['die_um2']) - area) / area < 0.02:
                e.update(cells=int(best['std']), basis=f"CLOSED {best['run']} std cells (die {best['die_um2']} um2)")
            else:
                best = max(cl, key=lambda r: int(r['std']))
                e.update(cells=int(best['std']), basis=f"CLOSED {best['run']} std cells (largest closed run; "
                                                       f"outline differs from the r18h5 view)")
        if 'cells' not in e and s.get('cells') and s['cells'] > 100:
            e.update(cells=int(s['cells']), basis=f"YOSYS {s.get('stat')}")
        if 'cells' not in e and s.get('std_area_um2'):
            e.update(cells=int(round(s['std_area_um2'] / A_CELL)),
                     basis=f"SYNAREA EST r18h5 views/synth/{m}/meta.json std_area {s['std_area_um2']:.0f} um2 / "
                           f"{A_CELL} um2")
        if 'cells' not in e:
            e.update(cells=None, basis='NONE (no closed run, no synthesis area)')
        ev[m] = e
        if m in keep:
            json.dump([dict(name=p['name'], layer=p['layer'], x=p['x'], y=p['y']) for p in pins],
                      open(os.path.join(a.out, 'cores', 'pins', f'{m}.json'), 'w'), separators=(',', ':'))
    for k, sp in SPLITS.items():
        if k in ev:                                  # the measured hierarchy total beats an area estimate
            ev[k].update(cells=sp['total'], basis=f"YOSYS {sp['stat']}")
    json.dump(dict(a_cell_um2=A_CELL, splits=SPLITS, masters=ev),
              open(os.path.join(a.out, 'inputs', 'cells_evidence.json'), 'w'), indent=1, sort_keys=True)
    print('masters', len(ev), 'no cells', [m for m, e in ev.items() if e['cells'] is None])


if __name__ == '__main__':
    main()
