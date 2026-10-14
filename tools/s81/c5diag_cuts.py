#!/usr/bin/env python3
"""c5 diagnosis (2026-10-13): CUT CHECK of the S81 die, the Qwen method (bits crossing a cut line against the routing
tracks available on it; owner rule: demand / supply <= 0.55-0.60), on the MEASURED c5 (v13) and c3 (v11) die GRT runs.

  step 1 (container)  tools/s81/c5diag_cut_dump.py         -> gcell_<L>_{cap,use}.f32, gcell.json, nets.tsv
  step 2 (host)       c5diag_cuts.py guides WORK GUIDE     -> guse_<L>.npy  net tracks per gcell EDGE from route.guide
  step 3 (host)       c5diag_cuts.py hot    WORK           -> 3-D overflow per 480 um window and layer (hot regions)
  step 4 (host)       c5diag_cuts.py cuts   WORK CUTS.json OUT.json   -> per cut: demand, used, supply, ratio, families
  step 5 (host)       c5diag_cuts.py scan   WORK CUTS.json OUT.json   -> sweeps of a cut segment along a channel
  step 6              c5diag_cuts.py report WORK_C5 WORK_C3 cuts.json tables.md

Accounting (stated once, used everywhere):
  SUPPLY of a cut = sum over the gcell edges the cut line crosses, per eligible layer of the crossing direction
    (a vertical line x = X is crossed by horizontal wires: M4, M6, M8; a horizontal line y = Y by M5, M7, M9; M3 and
    below are not die routing layers), of GRT's own free capacity of that edge:
        supply(edge) = cap(edge) - blockage(edge),   blockage = use_odb(edge) - guide_tracks(edge)
    i.e. what global route had after ITS reductions: the run's layer adjustment (c5: 30 % on M4/M5, 14.6 % on M6-M9),
    macro OBS (tile-internal layers), PG shapes and pre-routes present in the routed database.  Nothing is assumed:
    the reduction is read back from the checkpoint.  'supply_m4_m7' is the same without M8/M9 (the contract reserves
    M8/M9 for die power / global nets; the routed database carries NO M8/M9 PG shapes, see CUTS.md).
  USED = guide tracks on those edges (the wires c5's global route actually put across the line, detours included).
  DEMAND = nets of the PLACED netlist with terminals on BOTH sides of the line (pin-shape centres).  Every pin of the
    generated abstracts is DIRECTION INOUT, so driver and sink cannot be told apart from the database: 'end_a/end_b'
    are the two ends in database order, not source and destination.  For a cut SEGMENT the nets are attributed by the extent of their terminals along the line:
        captive  = terminal extent entirely inside the segment (must cross here unless it detours around the segment)
        share    = each crossing net spread uniformly over its terminal extent, the part inside the segment (estimate)
  RATIO = demand share / supply, flagged > 0.55 (WATCH), > 0.60 (OVER), > 1 (INFEASIBLE).
  PINCH = the worst 480 um and ~200 um window along the segment of demand / supply and of used / supply.
  'drop' in a cut definition = arithmetic what-if: the same cut without the bus families matching the regex.
A net is one bit.  Wide/NDR nets count as one track (GRT's guides do not carry the width).
"""
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

BUS1 = re.compile(r'_d\d+(_.*)?$|_g\d+(_.*)?$|_y\d+$')      # relay / station segment suffix
BUS2 = re.compile(r'_\d+_\d+(?=_|$)')                     # bit-range slice
LAYERS = ['M4', 'M5', 'M6', 'M7', 'M8', 'M9']
HL, VL = ['M4', 'M6', 'M8'], ['M5', 'M7', 'M9']


def grid(work):
    g = json.loads((Path(work) / 'gcell.json').read_text())
    step = g['GRIDX'][1] - g['GRIDX'][0]
    assert all(b - a == step for a, b in zip(g['GRIDX'][:-1], g['GRIDX'][1:])), 'non-uniform gcell grid'
    assert g['GRIDY'][1] - g['GRIDY'][0] == step and g['GRIDX'][0] == 0 and g['GRIDY'][0] == 0
    return g, step, g['nx'], g['ny']


def guides(work, guide):
    """Rasterise route.guide: tracks per gcell edge and layer.  Edge of gcell (i, j): to (i+1, j) on a horizontal
    layer, to (i, j+1) on a vertical layer (GRT's convention for the stored usage).  Overlapping boxes of ONE net on
    one layer count once."""
    g, step, nx, ny = grid(work)
    N = nx * ny
    li = {ln: k for k, ln in enumerate(LAYERS)}
    horiz = {k: (ln in HL) for ln, k in li.items()}
    acc = np.zeros(6 * N, dtype=np.int32)
    buf, s, nets, t0 = [], set(), 0, time.time()

    def flush():
        nonlocal buf
        if buf:
            a = np.fromiter(buf, dtype=np.int64, count=len(buf))
            acc[:] += np.bincount(a, minlength=6 * N).astype(np.int32)
            buf = []
    with open(guide) as f:
        for line in f:
            c = line[0]
            if c == ')':
                buf.extend(s)
                s = set()
                nets += 1
                if len(buf) > 4_000_000:
                    flush()
                    print('OT_GUIDES nets', nets, round(time.time() - t0), 's', flush=True)
            elif c.isdigit():
                p = line.split()
                k = li.get(p[4])
                if k is None:
                    continue
                i0, j0, i1, j1 = int(p[0]) // step, int(p[1]) // step, (int(p[2]) - 1) // step, (int(p[3]) - 1) // step
                i1, j1 = min(i1, nx - 1), min(j1, ny - 1)
                base = k * N
                if horiz[k]:
                    if i1 > i0:
                        for j in range(j0, j1 + 1):
                            s.update(range(base + j * nx + i0, base + j * nx + i1))
                elif j1 > j0:
                    for i in range(i0, i1 + 1):
                        s.update(range(base + j0 * nx + i, base + j1 * nx + i, nx))
    flush()
    tot = {}
    for ln, k in li.items():
        a = acc[k * N:(k + 1) * N].reshape(ny, nx)
        np.save(Path(work) / f'guse_{ln}.npy', a.astype(np.int16))
        tot[ln] = int(a.sum())
    print('OT_GUIDES done nets', nets, 'edge-tracks', tot, 'total', sum(tot.values()), flush=True)
    (Path(work) / 'guides_total.json').write_text(json.dumps(dict(nets=nets, tracks=tot, total=sum(tot.values()))))


def load(work):
    g, step, nx, ny = grid(work)
    d = {}
    for ln in LAYERS:
        cap = np.fromfile(Path(work) / f'gcell_{ln}_cap.f32', dtype=np.float32).reshape(ny, nx).astype(np.float64)
        use = np.fromfile(Path(work) / f'gcell_{ln}_use.f32', dtype=np.float32).reshape(ny, nx).astype(np.float64)
        gu = np.load(Path(work) / f'guse_{ln}.npy').astype(np.int32)
        # GRT stores the usage as uint8: it WRAPS at 256 where net usage + reduction >= 256 (measured: use 6 next to
        # use 255 on M6 with 240 / 233 guide tracks and a reduction of 22).  The reduction is < 256, so it is
        # recovered exactly modulo 256.
        blk = np.mod(use - gu, 256.0)
        sup = np.maximum(cap - blk, 0.0)
        d[ln] = dict(cap=cap, use=use, gu=gu, blk=blk, sup=sup, ov=np.maximum(0, gu - sup))
    return g, step, nx, ny, d


def hot(work, win=50):
    """3-D overflow (sum over gcells of max(0, use - cap), GRT's own definition) per win x win gcell window, and the
    cross-checks of the accounting against grt.log."""
    g, step, nx, ny, d = load(work)
    um = step / g['dbu_per_um']
    chk = {ln: dict(cap=float(d[ln]['cap'].sum()), guide_tracks=int(d[ln]['gu'].sum()), supply=float(d[ln]['sup'].sum()),
                    overflow=float(d[ln]['ov'].sum()), wrapped_edges=int((d[ln]['use'] - d[ln]['gu'] < -0.5).sum()))
           for ln in LAYERS}
    print('OT_HOT check', json.dumps(chk))
    J, I = -(-ny // win), -(-nx // win)
    tot = np.zeros((J, I))
    per = {}
    for ln in LAYERS:
        a = np.zeros((J * win, I * win))
        a[:ny, :nx] = d[ln]['ov']
        per[ln] = a.reshape(J, win, I, win).sum(axis=(1, 3))
        if ln not in ('M4', 'M5'):        # GRT reports ~0 on M4/M5: guide tracks above capacity there are macro pin access
            tot += per[ln]
    rows = []
    for j, i in zip(*np.unravel_index(np.argsort(-tot, axis=None)[:60], tot.shape)):
        if tot[j, i] <= 0:
            break
        rows.append(dict(x=[round(i * win * um, 1), round((i + 1) * win * um, 1)],
                         y=[round(j * win * um, 1), round((j + 1) * win * um, 1)], overflow=int(tot[j, i]),
                         by_layer={ln: int(per[ln][j, i]) for ln in LAYERS if per[ln][j, i] > 0}))
    out = dict(window_um=win * um, total_overflow=int(tot.sum()), check=chk, windows=rows,
               col_overflow={str(round(i * win * um)): int(v) for i, v in enumerate(tot.sum(axis=0)) if v > 0},
               row_overflow={str(round(j * win * um)): int(v) for j, v in enumerate(tot.sum(axis=1)) if v > 0})
    (Path(work) / 'hot.json').write_text(json.dumps(out, indent=1))
    print('OT_HOT total M6-M9', out['total_overflow'])
    for r in rows[:40]:
        print('OT_HOT', [float(v) for v in r['x'] + r['y']], r['overflow'], r['by_layer'])
    print('OT_HOT cols', out['col_overflow'])
    print('OT_HOT rows', out['row_overflow'])


def read_nets(work):
    """nets.tsv -> arrays (um): driver xy, sink bbox, all-terminal bbox; family ids (name without the bit index)."""
    import re
    cache = Path(work) / 'nets_arr.npz'
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        return {k: z[k] for k in z.files}
    dx, dy, sx0, sx1, sy0, sy1, fam, ns, di, si = [], [], [], [], [], [], [], [], [], []
    fid, inst = {}, {}
    strip = re.compile(r'\[\d+\]')
    with open(Path(work) / 'nets.tsv') as f:
        for line in f:
            p = line.rstrip('\n').split('\t')
            if not p[10] or p[2] == '':
                continue
            xs, ys = [], []
            for t in p[10].split(';'):
                a, b = t.split(',')
                xs.append(int(a))
                ys.append(int(b))
            dx.append(int(p[5])); dy.append(int(p[6]))
            sx0.append(min(xs)); sx1.append(max(xs)); sy0.append(min(ys)); sy1.append(max(ys))
            fam.append(fid.setdefault(strip.sub('', p[0]), len(fid)))
            ns.append(len(xs))
            di.append(inst.setdefault(p[2], len(inst))); si.append(inst.setdefault(p[8], len(inst)))
    A = lambda v: np.array(v, dtype=np.float64) / 1000.0
    r = dict(dx=A(dx), dy=A(dy), sx0=A(sx0), sx1=A(sx1), sy0=A(sy0), sy1=A(sy1), fam=np.array(fam, dtype=np.int32),
             ns=np.array(ns, dtype=np.int32), di=np.array(di, dtype=np.int32), si=np.array(si, dtype=np.int32),
             fam_names=np.array(list(fid), dtype=object), inst_names=np.array(list(inst), dtype=object))
    np.savez(cache, **r)
    return r


def cuts(work, cutfile, outfile):
    g, step, nx, ny, d = load(work)
    um = step / g['dbu_per_um']
    N = read_nets(work)
    spec = json.loads(Path(cutfile).read_text())
    res = []
    for c in spec['cuts']:
        vert = c['axis'] == 'x'                  # vertical line x = at, spanning lo..hi in y
        at, lo, hi = c['at'], c['lo'], c['hi']
        k = int(round(at / um)) - 1               # edge between gcell k and k+1 (line snapped to the gcell boundary)
        a0, a1 = int(lo // um), min(int(-(-hi // um)), ny if vert else nx)
        lay = HL if vert else VL
        per = {}
        for ln in lay:
            e = d[ln]
            sl = (slice(a0, a1), k) if vert else (k, slice(a0, a1))
            per[ln] = dict(cap=float(e['cap'][sl].sum()), blocked=float(e['blk'][sl].sum()),
                           supply=float(e['sup'][sl].sum()), used=int(e['gu'][sl].sum()),
                           overflow=float(e['ov'][sl].sum()))
        if vert:
            dp, s0, s1 = N['dx'], N['sx0'], N['sx1']
            t0, t1 = np.minimum(N['dy'], N['sy0']), np.maximum(N['dy'], N['sy1'])
        else:
            dp, s0, s1 = N['dy'], N['sy0'], N['sy1']
            t0, t1 = np.minimum(N['dx'], N['sx0']), np.maximum(N['dx'], N['sx1'])
        xline = k * um + um                       # the snapped line
        fwd = (dp < xline) & (s1 > xline)         # driver low side, a sink high side
        rev = (dp > xline) & (s0 < xline)
        cross = fwd | rev
        ext = np.maximum(t1 - t0, um)             # terminal extent along the line, at least one gcell
        ov = np.clip(np.minimum(t1, hi) - np.maximum(t0, lo), 0, None)
        ov = np.where((t1 - t0) < um, ((t0 >= lo) & (t0 < hi)) * um, ov)
        share = np.where(cross, np.minimum(1.0, ov / ext), 0.0)
        captive = cross & (t0 >= lo) & (t1 <= hi)
        sup = sum(v['supply'] for v in per.values())
        sup47 = sum(v['supply'] for ln, v in per.items() if ln not in ('M8', 'M9'))
        used = sum(v['used'] for v in per.values())
        dem_c, dem_s = int(captive.sum()), float(share.sum())
        along_d = N['dy'] if vert else N['dx']               # coordinate along the line
        along_s = (N['sy0'] + N['sy1']) / 2 if vert else (N['sx0'] + N['sx1']) / 2
        jog = np.abs(along_d - along_s)                      # lateral offset between the two ends of the net
        drop = re.compile(c['drop']) if c.get('drop') else None
        wsum = np.bincount(N['fam'][cross], weights=share[cross], minlength=len(N['fam_names']))
        order = np.argsort(-wsum)
        fams, buses, dropped = [], defaultdict(lambda: [0.0, 0, None, None, 0.0]), 0.0
        for f in order:
            w = float(wsum[f])
            if w <= 0:
                break
            name = str(N['fam_names'][f])
            if drop is not None and drop.search(name):
                dropped += w
            bn = BUS2.sub('', BUS1.sub('', name))
            bb = buses[bn]
            bb[0] += w
            bb[1] += 1
            if len(fams) < 12 or bb[2] is None:
                m = cross & (N['fam'] == f) & (share > 0)
                i0 = int(np.argmax(m))
                rec = dict(family=name, bits_share=round(w, 1), bits_captive=int((captive & m).sum()),
                           end_a=str(N['inst_names'][N['di'][i0]]), end_b=str(N['inst_names'][N['si'][i0]]),
                           end_a_extent_um=[round(float(along_d[m].min()), 1), round(float(along_d[m].max()), 1)],
                           term_extent_um=[round(float(t0[m].min()), 1), round(float(t1[m].max()), 1)],
                           mean_jog_um=round(float(jog[m].mean()), 1))
                if bb[2] is None:
                    bb[2], bb[3], bb[4] = rec['end_a'], rec['end_b'], rec['mean_jog_um']
                if len(fams) < 12:
                    fams.append(rec)
        busl = [dict(bus=k, bits_share=round(v[0], 1), segments=v[1], end_a=v[2], end_b=v[3], mean_jog_um=v[4])
                for k, v in sorted(buses.items(), key=lambda kv: -kv[1][0])[:10]]
        # local pinch: per-gcell profiles of supply, guide use and demand (each crossing net spread over its extent)
        nb = a1 - a0
        prof_s, prof_u = np.zeros(nb), np.zeros(nb)
        for ln in lay:
            prof_s += (d[ln]['sup'][a0:a1, k] if vert else d[ln]['sup'][k, a0:a1])
            prof_u += (d[ln]['gu'][a0:a1, k] if vert else d[ln]['gu'][k, a0:a1])
        diff = np.zeros(nb + 2)
        cm = cross & (ov > 0)
        g0 = (t0[cm] / um).astype(int)
        g1 = np.maximum((t1[cm] / um).astype(int), g0 + 1)
        np.add.at(diff, np.clip(g0 - a0, 0, nb), 1.0 / (g1 - g0))
        np.add.at(diff, np.clip(g1 - a0, 0, nb), -1.0 / (g1 - g0))
        prof_d = np.cumsum(diff)[:nb]
        cs = lambda v: np.concatenate([[0], np.cumsum(v)])
        cd, cu, csu = cs(prof_d), cs(prof_u), cs(prof_s)
        pin = {}
        for W in (50, 21):
            W = min(nb, W)
            wd, wu, wsu = cd[W:] - cd[:-W], cu[W:] - cu[:-W], csu[W:] - csu[:-W]
            rr, ru = wd / np.maximum(wsu, 1.0), wu / np.maximum(wsu, 1.0)
            jd, ju = int(np.argmax(rr)), int(np.argmax(ru))
            pin[f'w{round(W * um)}'] = dict(
                window_um=round(W * um, 1),
                demand=dict(at_um=[round((a0 + jd) * um, 1), round((a0 + jd + W) * um, 1)], bits=round(float(wd[jd]), 1),
                            supply=round(float(wsu[jd]), 1), used=int(wu[jd]), ratio=round(float(rr[jd]), 3),
                            bits_per_um=round(float(wd[jd]) / (W * um), 2), tracks_per_um=round(float(wsu[jd]) / (W * um), 2)),
                used=dict(at_um=[round((a0 + ju) * um, 1), round((a0 + ju + W) * um, 1)], used=int(wu[ju]),
                          supply=round(float(wsu[ju]), 1), bits=round(float(wd[ju]), 1), ratio=round(float(ru[ju]), 3)))
        flag = lambda r: 'INFEASIBLE' if r > 1 else 'OVER' if r > 0.60 else 'WATCH' if r > 0.55 else 'ok'
        ovf = sum(v['overflow'] for ln, v in per.items() if ln not in ('M4', 'M5'))
        r = dict(name=c['name'], axis=c['axis'], at_um=round(xline, 1), lo_um=lo, hi_um=hi, why=c.get('why', ''),
                 length_um=hi - lo, layers=per, supply=round(sup, 1), supply_m4_m7=round(sup47, 1), used=used,
                 overflow_m6_m9=round(ovf, 1), demand_cross_total=int(cross.sum()), demand_captive=dem_c,
                 demand_share=round(dem_s, 1), ratio=round(dem_s / max(sup, 1), 3),
                 ratio_captive=round(dem_c / max(sup, 1), 3), ratio_used=round(used / max(sup, 1), 3),
                 ratio_m4_m7=round(dem_s / max(sup47, 1), 3), flag=flag(dem_s / max(sup, 1)),
                 flag_used=flag(used / max(sup, 1)), flag_m4_m7=flag(dem_s / max(sup47, 1)), pinch=pin, families=fams,
                 buses=busl)
        if drop is not None:
            r['whatif'] = dict(drop=c['drop'], note=c.get('drop_note', ''), bits_removed=round(dropped, 1),
                               demand_share=round(dem_s - dropped, 1), ratio=round((dem_s - dropped) / max(sup, 1), 3),
                               ratio_m4_m7=round((dem_s - dropped) / max(sup47, 1), 3))
        res.append(r)
        p5, p2 = pin['w480' if 'w480' in pin else sorted(pin)[0]], pin[sorted(pin, key=lambda q: int(q[1:]))[0]]
        print(f"OT_CUT {r['name']:24s} {r['axis']}={r['at_um']:8.1f} [{lo:7.0f},{hi:7.0f}] dem {r['demand_share']:7.0f} capt {dem_c:6d} "
              f"used {used:6d} sup {sup:7.0f} M4-7 {sup47:7.0f} r {r['ratio']:.3f} ru {r['ratio_used']:.3f} "
              f"r47 {r['ratio_m4_m7']:.3f} ovf {ovf:.0f} p480 {p5['demand']['ratio']:.2f}/{p5['used']['ratio']:.2f} "
              f"p200 {p2['demand']['ratio']:.2f}/{p2['used']['ratio']:.2f} {r['flag']}"
              + (f" whatif {r['whatif']['ratio']:.3f}" if drop is not None else ''), flush=True)
    Path(outfile).write_text(json.dumps(dict(work=str(work), gcell_um=um, cuts=res), indent=1) + '\n')


def scan(work, cutfile, outfile):
    """Sweep a cut segment across a channel ('scans' in the definition file: axis, lo, hi, at_from, at_to, step):
    demand share / supply at every position, so that the worst line of a channel is found and not chosen."""
    g, step, nx, ny, d = load(work)
    um = step / g['dbu_per_um']
    N = read_nets(work)
    res = []
    for c in json.loads(Path(cutfile).read_text())['scans']:
        vert = c['axis'] == 'x'
        lo, hi = c['lo'], c['hi']
        a0, a1 = int(lo // um), min(int(-(-hi // um)), ny if vert else nx)
        lay = HL if vert else VL
        if vert:
            dp, s0, s1 = N['dx'], N['sx0'], N['sx1']
            t0, t1 = np.minimum(N['dy'], N['sy0']), np.maximum(N['dy'], N['sy1'])
        else:
            dp, s0, s1 = N['dy'], N['sy0'], N['sy1']
            t0, t1 = np.minimum(N['dx'], N['sx0']), np.maximum(N['dx'], N['sx1'])
        pre = (t1 >= lo) & (t0 <= hi) & (np.maximum(dp, s1) >= c['at_from'] - um) & (np.minimum(dp, s0) <= c['at_to'] + um)
        dp, s0, s1, t0, t1 = dp[pre], s0[pre], s1[pre], t0[pre], t1[pre]
        ext = np.maximum(t1 - t0, um)
        ov = np.clip(np.minimum(t1, hi) - np.maximum(t0, lo), 0, None)
        ov = np.where((t1 - t0) < um, ((t0 >= lo) & (t0 < hi)) * um, ov)
        w = np.minimum(1.0, ov / ext)
        rows = []
        at = c['at_from']
        while at <= c['at_to'] + 1e-6:
            k = int(round(at / um)) - 1
            xl = (k + 1) * um
            cross = ((dp < xl) & (s1 > xl)) | ((dp > xl) & (s0 < xl))
            dem = float(w[cross].sum())
            sup = sum(float((d[ln]['sup'][a0:a1, k] if vert else d[ln]['sup'][k, a0:a1]).sum()) for ln in lay)
            used = sum(int((d[ln]['gu'][a0:a1, k] if vert else d[ln]['gu'][k, a0:a1]).sum()) for ln in lay)
            rows.append([round(xl, 1), round(dem, 1), round(sup, 1), used, round(dem / max(sup, 1), 3), round(used / max(sup, 1), 3)])
            at += c['step']
        worst = max(rows, key=lambda r: r[4])
        wu = max(rows, key=lambda r: r[5])
        r = dict(name=c['name'], axis=c['axis'], lo_um=lo, hi_um=hi, at_from=c['at_from'], at_to=c['at_to'], step=c['step'],
                 why=c.get('why', ''), positions=len(rows), over_055=sum(1 for q in rows if q[4] > 0.55),
                 over_060=sum(1 for q in rows if q[4] > 0.60), over_100=sum(1 for q in rows if q[4] > 1.0),
                 worst=dict(at_um=worst[0], demand_share=worst[1], supply=worst[2], used=worst[3], ratio=worst[4]),
                 worst_used=dict(at_um=wu[0], used=wu[3], supply=wu[2], ratio_used=wu[5]),
                 columns=['at_um', 'demand_share', 'supply', 'used', 'ratio', 'ratio_used'], rows=rows)
        res.append(r)
        print(f"OT_SCAN {r['name']:22s} n {len(rows):4d} >0.55 {r['over_055']:3d} >0.60 {r['over_060']:3d} >1 {r['over_100']:3d} "
              f"worst at {worst[0]:8.1f} dem {worst[1]:7.0f} sup {worst[2]:7.0f} used {worst[3]:6d} r {worst[4]:.3f}; "
              f"worst used at {wu[0]:8.1f} ru {wu[5]:.3f}", flush=True)
    Path(outfile).write_text(json.dumps(dict(work=str(work), scans=res)) + '\n')


def report(w5, w3, out_json, out_md):
    """Merge the c5 and c3 results into cuts.json and write the tables of CUTS.md (tables only)."""
    L = lambda w, f: json.loads((Path(w) / f).read_text())
    c5, c3 = L(w5, 'cuts_out.json')['cuts'], {c['name']: c for c in L(w3, 'cuts_out.json')['cuts']}
    s5, s3 = L(w5, 'scan_out.json')['scans'], {c['name']: c for c in L(w3, 'scan_out.json')['scans']}
    h5, h3 = L(w5, 'hot.json'), L(w3, 'hot.json')
    slim = lambda c: {k: (v[:6] if k in ('families', 'buses') else v) for k, v in c.items()}
    slim3 = lambda c: {k: (v[:4] if k == 'buses' else v) for k, v in c.items() if k not in ('families', 'why')}
    pk = lambda c: min(c['pinch'], key=lambda q: int(q[1:]))
    def fl(c):
        f = c['flag']
        p = c['pinch'][pk(c)]['demand']['ratio']
        return f if f != 'ok' else ('PINCH>1' if p > 1 else 'pinch>0.60' if p > 0.6 else 'ok')
    md = ['| cut | line | span um | demand bits (captive) | used by guides | supply M4-M9 (M4-M7) | ratio | used/supply | ratio M4-M7 | worst 480 um | worst ~200 um | flag | c3 same line |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in c5:
        if c['name'].startswith('c3n_'):
            continue
        o = c3.get(c['name'])
        p4 = c['pinch'][max(c['pinch'], key=lambda q: int(q[1:]))]['demand']['ratio']
        p2 = c['pinch'][pk(c)]['demand']['ratio']
        md.append(f"| {c['name']} | {c['axis']}={c['at_um']:,.1f} | {c['lo_um']:,.0f}..{c['hi_um']:,.0f} | {c['demand_share']:,.0f} ({c['demand_captive']:,}) | "
                  f"{c['used']:,} | {c['supply']:,.0f} ({c['supply_m4_m7']:,.0f}) | {c['ratio']:.3f} | {c['ratio_used']:.3f} | {c['ratio_m4_m7']:.3f} | "
                  f"{p4:.2f} | {p2:.2f} | {fl(c)} | {o['ratio']:.3f} |")
    md += ['', '| structure (c3 position = c5 position - 3,952.8 um N) | c5 ratio (worst ~200 um) | c3 ratio (worst ~200 um) |', '|---|---|---|']
    c5d = {c['name']: c for c in c5}
    for n, o in c3.items():
        if n.startswith('c3n_') and n[4:] in c5d:
            a = c5d[n[4:]]
            md.append(f"| {n[4:]} | {a['ratio']:.3f} ({a['pinch'][pk(a)]['demand']['ratio']:.2f}) | {o['ratio']:.3f} ({o['pinch'][pk(o)]['demand']['ratio']:.2f}) |")
    md += ['', '| sweep | span um | positions | > 0.55 | > 0.60 | > 1 | worst at | demand | supply | used | ratio | c3 worst (same sweep) | c3 worst (c3 position) |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in s5:
        if c['name'].startswith('c3n_'):
            continue
        w, o, on = c['worst'], s3[c['name']]['worst'], s3.get('c3n_' + c['name'])
        md.append(f"| {c['name']} | {c['lo_um']:,.0f}..{c['hi_um']:,.0f} | {c['positions']} | {c['over_055']} | {c['over_060']} | {c['over_100']} | "
                  f"{c['axis']}={w['at_um']:,.1f} | {w['demand_share']:,.0f} | {w['supply']:,.0f} | {w['used']:,} | {w['ratio']:.3f} | "
                  f"{o['ratio']:.3f} at {o['at_um']:,.1f} | " + (f"{on['worst']['ratio']:.3f} at {on['worst']['at_um']:,.1f} ({on['over_060']} > 0.60) |" if on else '- |'))
    md += ['', '| hot window (480 um) x | y | overflow M6-M9 | by layer |', '|---|---|---|---|']
    for r in h5['windows'][:16]:
        md.append(f"| {r['x'][0]:,.0f}..{r['x'][1]:,.0f} | {r['y'][0]:,.0f}..{r['y'][1]:,.0f} | {r['overflow']:,} | "
                  + ' '.join(f'{k} {v:,}' for k, v in r['by_layer'].items() if k not in ('M4', 'M5')) + ' |')
    Path(out_md).write_text('\n'.join(md) + '\n')
    drop_rows = lambda c: {k: v for k, v in c.items() if k != 'rows'}
    out = dict(schema='opentallas.s81.c5diag.cuts.v1', date='2026-10-13',
               method=__doc__.split('Accounting')[1],
               checks=dict(c5=dict(grt_log_total_overflow=1053305, reconstructed_overflow_m6_m9=h5['total_overflow'], per_layer=h5['check'],
                                   guide_tracks=L(w5, 'guides_total.json')),
                           c3=dict(reconstructed_overflow_m6_m9=h3['total_overflow'], per_layer=h3['check'],
                                   guide_tracks=L(w3, 'guides_total.json'))),
               hot_windows_c5=h5['windows'][:30], hot_windows_c3=h3['windows'][:20],
               col_overflow_c5=h5['col_overflow'], col_overflow_c3=h3['col_overflow'],
               cuts_c5=[slim(c) for c in c5 if not c['name'].startswith('c3n_')],
               cuts_c3=[slim3(c) for c in c3.values()],
               scans_c5=[c for c in s5 if not c['name'].startswith('c3n_')], scans_c3=[drop_rows(c) for c in s3.values()])
    Path(out_json).write_text(json.dumps(out) + '\n')
    print('OT_REPORT', len(out['cuts_c5']), 'c5 cuts', len(out['cuts_c3']), 'c3 cuts', len(s5), 'scans')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'guides':
        guides(sys.argv[2], sys.argv[3])
    elif cmd == 'hot':
        hot(sys.argv[2])
    elif cmd == 'cuts':
        cuts(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'scan':
        scan(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'report':
        report(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        sys.exit(__doc__)
