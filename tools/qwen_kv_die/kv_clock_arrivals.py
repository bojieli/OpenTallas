#!/usr/bin/env python3
"""KVPLAN3 0230 (Q-KV / DIE-CLOCK 2026-10-17: 'use kv_rt3 clock.odb + arrivals_tt.tsv as the interim real clock, so the KV
die STA no longer runs on ideal clocks'): rewrite a KV die run's compensated-ideal clock Tcl (RUN/libs/clocks_<c>.tcl:
every core clock pin P of 'stream' / 'stream__early' gets set_clock_latency -source -R(P), plus a 90 / 150-ps skew
budget in the stream uncertainty) into a MEASURED-ARRIVAL clock Tcl:

  * pin latency L(P) = A(P) - A0, A = the DIE-CLOCK measured propagated arrival at P (arrivals_tt.tsv: col 2 = TT late,
    col 3 = FF early; the tree was trimmed to phi - R, so R is already compensated physically: no -R, DIE-CLOCK
    METHOD.md step 3), A0 = the median arrival of the matched stream pins (a common offset; it cancels within a clock);
  * a pin whose instance is not in the arrival file (the arrivals were measured on another floorplan: relays, forks, taps
    are new) takes the LOCAL clock phase of the nearest matched instance on THIS run's placement, phi_n = A(n) + R(n),
    minus its own R: L(P) = phi_n - R(P) - A0 (R(P) from the original Tcl's compensation);
  * the stream uncertainty keeps only the setup margin (60 ps) -- the skew is now explicit -- and the hold margin.
Corner: tt / ss use col 2, ff uses col 3.  Writes OUT and OUT.json (match statistics, worst nearest distance).

    kv_clock_arrivals.py --run RUN --arrivals ARR_TSV --corner tt --out RUN/libs/clocks_rt3_tt.tcl
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

LAT = re.compile(r'^set_clock_latency -source -clock \[get_clocks (stream|stream__early)\] (-?[\d.]+) \[get_pins \{([^}]+)\}\]$')
UNC = re.compile(r'^set_clock_uncertainty -setup ([\d.]+) -from \[get_clocks (stream|stream__early)\] -to \[get_clocks (stream|stream__early)\]$')
SETUP_MARGIN = 60.0


def def_origins(path):
    units, out, comp = 1000.0, {}, False
    for ln in open(path):
        s = ln.strip()
        if s.startswith('UNITS DISTANCE MICRONS'):
            units = float(s.split()[3])
        elif s.startswith('COMPONENTS'):
            comp = True
        elif s.startswith('END COMPONENTS'):
            break
        elif comp and s.startswith('-'):
            name = s.split()[1]
            m = re.search(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', s)
            if m:
                out[name.replace('\\', '')] = (int(m.group(1)) / units, int(m.group(2)) / units)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--arrivals', required=True)
    ap.add_argument('--corner', required=True, choices=('tt', 'ff', 'ss'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--def', dest='def_', help='placed DEF (default RUN/case_kv/floorplan_placed.def)')
    a = ap.parse_args(argv)
    run = Path(a.run)
    src = run / 'libs' / f'clocks_{a.corner}.tcl'
    col = 2 if a.corner == 'ff' else 1
    arr = {}
    for ln in open(a.arrivals):
        t = ln.rstrip('\n').split('\t')
        if len(t) >= 3:
            arr[t[0]] = float(t[col])
    lines = src.read_text().split('\n')
    pins = {}                                  # pin -> (clock, R)
    for ln in lines:
        m = LAT.match(ln)
        if m:
            pins[m.group(3)] = (m.group(1), -float(m.group(2)))
    inst = lambda p: p.rsplit('/', 1)[0]      # noqa: E731
    matched = {p: arr[p] for p in pins if p in arr}
    if not matched:
        raise SystemExit('no stream pin of this run is in the arrival file')
    a0 = statistics.median(matched.values())
    dp_ = Path(a.def_) if a.def_ else run / 'case_kv' / 'floorplan_placed.def'
    if dp_.exists():
        pos = def_origins(dp_)
    else:
        # before the chain's real case: the planned origins of case_kv/place.tcl (ot_mts::place [... findInst N] x y O)
        pos = {}
        for ln in open(run / 'case_kv' / 'place.tcl'):
            m_ = re.search(r'findInst (\S+)\]\s+(-?[\d.]+)\s+(-?[\d.]+)', ln)
            if m_:
                pos[m_.group(1)] = (float(m_.group(2)), float(m_.group(3)))
        stat_src = 'place.tcl'
    # nearest matched instance on this run's placement: bucket grid
    G = 200.0
    grid = {}
    phi_inst = {}
    for p, A in matched.items():
        i = inst(p)
        if i in pos:
            phi_inst.setdefault(i, []).append(A + pins[p][1])
    for i, v in phi_inst.items():
        phi_inst[i] = statistics.median(v)
        x, y = pos[i]
        grid.setdefault((int(x // G), int(y // G)), []).append(i)

    def nearest(i):
        x, y = pos[i]
        gx, gy = int(x // G), int(y // G)
        for r in range(0, 200):
            best = None
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    for j in grid.get((gx + dx, gy + dy), ()):
                        d = abs(pos[j][0] - x) + abs(pos[j][1] - y)
                        if best is None or d < best[0]:
                            best = (d, j)
            if best is not None and best[0] <= (r + 1) * G:
                return best
        return None
    out, stat = [], dict(pins=len(pins), matched=len(matched), nearest=0, unplaced=0, worst_nearest_um=0.0, a0_ps=round(a0, 3),
                         corner=a.corner, column=col + 1, arrivals=str(a.arrivals), source=str(src))
    newlat = {}
    for p, (ck, R) in pins.items():
        if p in matched:
            newlat[p] = matched[p] - a0
            continue
        i = inst(p)
        if i not in pos:
            stat['unplaced'] += 1
            newlat[p] = -R              # no placement: keep the compensated ideal latency
            continue
        nb = nearest(i)
        if nb is None:
            stat['unplaced'] += 1
            newlat[p] = -R
            continue
        stat['nearest'] += 1
        stat['worst_nearest_um'] = max(stat['worst_nearest_um'], round(nb[0], 1))
        newlat[p] = phi_inst[nb[1]] - R - a0
    for ln in lines:
        m = LAT.match(ln)
        if m:
            out.append(f'set_clock_latency -source -clock [get_clocks {m.group(1)}] {newlat[m.group(3)]:.3f} [get_pins {{{m.group(3)}}}]')
            continue
        u = UNC.match(ln)
        if u:
            out.append(f'# KVPLAN3 0230: measured arrivals (kv_rt3) carry the skew; setup keeps the {SETUP_MARGIN:.0f}-ps margin only')
            out.append(f'set_clock_uncertainty -setup {SETUP_MARGIN:.6f} -from [get_clocks {u.group(2)}] -to [get_clocks {u.group(3)}]')
            continue
        out.append(ln)
    out.insert(0, f'# KVPLAN3 0230 kv_clock_arrivals.py: {stat}')
    Path(a.out).write_text('\n'.join(out))
    v = list(newlat.values())
    stat.update(latency_min_ps=round(min(v), 1), latency_max_ps=round(max(v), 1))
    Path(a.out + '.json').write_text(json.dumps(stat, indent=1) + '\n')
    print(json.dumps(stat))


if __name__ == '__main__':
    sys.exit(main())
