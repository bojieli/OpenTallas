#!/usr/bin/env python3
"""H-DIE-R8 10-17: MEASURED die neighbour-skew gate (OWNER 10-16 neighbour-relative clocking; coordinator 0dg (2)).

Input: the die_clock_check.py report JSON of a die trial (die STA propagated-clock arrivals dumped in the trial's OpenROAD
session by tools/die_clock_check.tcl, OT_DCC_OUT=/work/out/die_clock_dump.tsv; optionally --ff-dump for the FF corner).
Judged pairs: every COMMUNICATING tile pair of the die netlist (tiles = hard blocks incl. relay stations, sharing a data
net) whose nearest clock entries are within --near-um (default 405 um, the measured reach) and hang on ONE die clock root
(same PLL domain).  Measured skew = |STA arrival A - STA arrival B| at the two entry pins (TT); FF when the report carries
it.  Pairs on different roots (serial:stream 3:4 seam, async hbm) are listed, not judged; entries not reached by the die
tree (forwarded-clock F1 relay clk_in chained from the previous station's clk_out) are unmatched and listed by count.
PASS iff every judged pair is <= --budget-ps (default 80).

    neighbour_skew_gate.py REPORT.json [--near-um 405] [--budget-ps 80] [--out GATE.json]
    neighbour_skew_gate.py --run CASE_OUT_DIR   (runs die_clock_check.py report on CASE_OUT_DIR/die_clock_dump.tsv first)
Exit 0 PASS, 1 FAIL, 2 no measured data.
"""
import argparse, json, os, statistics, subprocess, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def stats(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    return dict(n=len(v), median=round(statistics.median(v), 1), p90=round(v[int(0.9 * (len(v) - 1))], 1), max=round(v[-1], 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('report', nargs='?')
    ap.add_argument('--run', help='case out dir holding die_clock_dump.tsv (+ die_clock_dump_ff.tsv if present)')
    ap.add_argument('--near-um', type=float, default=405.0)
    ap.add_argument('--budget-ps', type=float, default=80.0)
    ap.add_argument('--out')
    ap.add_argument('--top', type=int, default=25)
    a = ap.parse_args()
    rep = a.report
    if a.run:
        rep = os.path.join(a.run, 'die_clock_check.json')
        cmd = [sys.executable, os.path.join(HERE, '..', 'die_clock_check.py'), 'report', os.path.join(a.run, 'die_clock_dump.tsv'),
               '--out', rep, '--top', '5']
        ff = os.path.join(a.run, 'die_clock_dump_ff.tsv')
        if os.path.exists(ff):
            cmd += ['--ff-dump', ff, '--budget-ps', str(a.budget_ps)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    r = json.load(open(rep))
    tiles = {t['entry']: t for t in r.get('tiles', [])}
    roots = {t['entry']: t['root'] for t in r.get('tiles', [])}
    ffmap = {}
    nb = r.get('neighbour_check') or {}
    judged, cross_root, no_sta, far = [], Counter(), 0, 0
    for p in r.get('pairs', []):
        ea, eb = p.get('entry_a'), p.get('entry_b')
        d = p.get('entry_distance_um')
        if d is None or d > a.near_um:
            far += 1
            continue
        if roots.get(ea) != roots.get(eb):
            cross_root['|'.join(sorted((str(roots.get(ea)), str(roots.get(eb)))))] += 1
            continue
        sk = p.get('sta_skew_ps')
        if sk is None:
            no_sta += 1
            continue
        judged.append(dict(a=p['a'], b=p['b'], entry_a=ea, entry_b=eb, dist_um=d, skew_tt_ps=sk,
                           noncommon_tt_ps=p.get('sta_ps'), region_a=p.get('region_a'), region_b=p.get('region_b'),
                           root=roots.get(ea), lca=p.get('lca')))
    over = [j for j in judged if j['skew_tt_ps'] > a.budget_ps]
    by_root = defaultdict(list)
    for j in judged:
        by_root[j['root']].append(j['skew_tt_ps'])
    intra = [j['skew_tt_ps'] for j in judged if j['region_a'] == j['region_b']]
    inter = [j['skew_tt_ps'] for j in judged if j['region_a'] != j['region_b']]
    verdict = 'NO_DATA' if not judged else ('PASS' if not over else 'FAIL')
    out = dict(schema='opentallas.hbm.neighbour_skew_gate.v1', report=os.path.abspath(rep), near_um=a.near_um,
               budget_ps=a.budget_ps, corner='TT pin arrival (die STA propagated clock); FF via die_clock_check --ff-dump when present',
               verdict=verdict, judged_pairs=len(judged), over_budget=len(over), skew_tt_ps=stats([j['skew_tt_ps'] for j in judged]),
               by_root={k: stats(v) for k, v in by_root.items()}, intra_region=stats(intra), inter_region=stats(inter),
               ff_neighbour_check=(nb.get('summary') if isinstance(nb, dict) else None),
               not_judged=dict(far_pairs=far, cross_root=dict(cross_root), no_sta=no_sta,
                               unmatched_entries=len(r.get('unmatched_pairs', []))),
               worst=sorted(judged, key=lambda j: -j['skew_tt_ps'])[:a.top])
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)
    print(f"NEIGHBOUR_SKEW_GATE {verdict} judged={len(judged)} over={len(over)} budget={a.budget_ps} near={a.near_um} "
          f"skew_tt={json.dumps(out['skew_tt_ps'])} intra={json.dumps(out['intra_region'])} inter={json.dumps(out['inter_region'])}")
    for j in out['worst'][:10]:
        print(f"  {j['skew_tt_ps']:8.1f} ps  {j['dist_um']:6.0f} um  {j['a']} <-> {j['b']}  [{j['region_a']}|{j['region_b']}]")
    sys.exit({'PASS': 0, 'FAIL': 1}.get(verdict, 2))


if __name__ == '__main__':
    main()
