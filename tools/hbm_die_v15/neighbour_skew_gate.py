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

HBM-LANDING 10-18 (CLOCK-AUDIT: the d4g gate was TT only): every judged pair is ALSO judged at FF, and the verdict is
PASS only if TT AND FF are <= budget (--require-ff: no FF data = NO_FF, exit 2).  FF arrivals come from
  * die_clock_dump_ff.tsv (a separate FF-corner session dump: its arr_min column), or
  * --ff-from-min: the TT dump's arr_min column.  Valid for die_case_v16 sessions (define_corners tt ff; OpenSTA's pin
    property arrival_min_rise is the minimum over BOTH corners' min path APs = the FF arrival; arrival_max_rise = TT).
Pairs with a LANDED end (hbfd_land*/hbfd_lh* lane tiles, LANDING-CONTRACT L1-L5) are not skew-judged: the forwarded
lane -> ring crossing is checked by the die STA landing window (MCP -setup E -hold D-1, one E per link, TT and FF);
the landing's read side sits on the sink root and is judged with the sink like any tile pair.
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
    ap.add_argument('--ff-from-min', action='store_true', help='FF arrival = the TT dump arr_min column (dual-corner session)')
    ap.add_argument('--require-ff', action='store_true', help='no FF arrivals -> verdict NO_FF (exit 2)')
    ap.add_argument('--region-map', help='passed to die_clock_check.py report (tools/die_clock build spec)')
    ap.add_argument('--landed-re', default=r'^hbfd_(land|lh)', help='tile masters whose pairs are landing-window judged')
    a = ap.parse_args()
    rep = a.report
    if a.run:
        rep = os.path.join(a.run, 'die_clock_check.json')
        cmd = [sys.executable, os.path.join(HERE, '..', 'die_clock_check.py'), 'report', os.path.join(a.run, 'die_clock_dump.tsv'),
               '--out', rep, '--top', '5']
        ff = os.path.join(a.run, 'die_clock_dump_ff.tsv')
        if os.path.exists(ff):
            cmd += ['--ff-dump', ff, '--budget-ps', str(a.budget_ps)]
        elif a.ff_from_min:
            cmd += ['--ff-dump', os.path.join(a.run, 'die_clock_dump.tsv'), '--budget-ps', str(a.budget_ps)]
        if a.region_map:
            cmd += ['--region-map', a.region_map]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    r = json.load(open(rep))
    tiles = {t['entry']: t for t in r.get('tiles', [])}
    roots = {t['entry']: t['root'] for t in r.get('tiles', [])}
    ffmap = {}
    nb = r.get('neighbour_check') or {}
    import re as _re
    landed_re = _re.compile(a.landed_re)
    ffarr = {}
    if a.run and os.path.exists(os.path.join(a.run, 'die_clock_dump_ff.tsv')):
        for ln in open(os.path.join(a.run, 'die_clock_dump_ff.tsv')):
            f = ln.rstrip('\n').split('\t')
            if f and f[0] == 'T' and len(f) >= 8 and f[7] not in ('-', ''):
                ffarr[f[1]] = float(f[7])
        ff_src = 'die_clock_dump_ff.tsv arr_min'
    elif a.ff_from_min:
        ffarr = {t['entry']: t['sta_min_ps'] for t in r.get('tiles', []) if t.get('sta_min_ps') is not None}
        ff_src = 'TT dump arr_min (dual-corner tt+ff session = FF)'
        rat = sorted(t['sta_min_ps'] / t['sta_max_ps'] for t in r.get('tiles', [])
                     if t.get('sta_min_ps') is not None and t.get('sta_max_ps') and t['sta_max_ps'] > 50)
        if rat and rat[len(rat) // 2] > 0.97:   # FF insertion is ~0.75-0.85 x TT on ASAP7: min == max means a 1-corner session
            ff_src += f' -- SUSPECT: median arr_min/arr_max {rat[len(rat) // 2]:.3f} (single-corner dump?)'
    else:
        ff_src = None
    landed = 0
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
        if landed_re.match(str((tiles.get(ea) or {}).get('master', ''))) or landed_re.match(str((tiles.get(eb) or {}).get('master', ''))):
            landed += 1
            continue
        sk = p.get('sta_skew_ps')
        if sk is None:
            no_sta += 1
            continue
        skf = round(abs(ffarr[ea] - ffarr[eb]), 1) if (ea in ffarr and eb in ffarr) else None
        judged.append(dict(a=p['a'], b=p['b'], entry_a=ea, entry_b=eb, dist_um=d, skew_tt_ps=sk, skew_ff_ps=skf,
                           noncommon_tt_ps=p.get('sta_ps'), region_a=p.get('region_a'), region_b=p.get('region_b'),
                           root=roots.get(ea), lca=p.get('lca')))
    over = [j for j in judged if j['skew_tt_ps'] > a.budget_ps]
    over_ff = [j for j in judged if j['skew_ff_ps'] is not None and j['skew_ff_ps'] > a.budget_ps]
    ff_missing = sum(1 for j in judged if j['skew_ff_ps'] is None)
    by_root = defaultdict(list)
    for j in judged:
        by_root[j['root']].append(j['skew_tt_ps'])
    intra = [j['skew_tt_ps'] for j in judged if j['region_a'] == j['region_b']]
    inter = [j['skew_tt_ps'] for j in judged if j['region_a'] != j['region_b']]
    verdict = 'NO_DATA' if not judged else ('PASS' if not over and not over_ff else 'FAIL')
    if verdict == 'PASS' and a.require_ff and (ff_src is None or ff_missing or 'SUSPECT' in ff_src):
        verdict = 'NO_FF'
    out = dict(schema='opentallas.hbm.neighbour_skew_gate.v1', report=os.path.abspath(rep), near_um=a.near_um,
               budget_ps=a.budget_ps, corner='TT and FF pin arrivals (die STA propagated clock); verdict needs both <= budget',
               ff_source=ff_src, verdict=verdict, judged_pairs=len(judged), over_budget=len(over), over_budget_ff=len(over_ff),
               ff_missing_pairs=ff_missing, landed_pairs_not_skew_judged=landed,
               skew_tt_ps=stats([j['skew_tt_ps'] for j in judged]), skew_ff_ps=stats([j['skew_ff_ps'] for j in judged]),
               by_root={k: stats(v) for k, v in by_root.items()}, intra_region=stats(intra), inter_region=stats(inter),
               ff_neighbour_check=(nb.get('summary') if isinstance(nb, dict) else None),
               not_judged=dict(far_pairs=far, cross_root=dict(cross_root), no_sta=no_sta,
                               unmatched_entries=len(r.get('unmatched_pairs', []))),
               worst=sorted(judged, key=lambda j: -max(j['skew_tt_ps'], j['skew_ff_ps'] or 0))[:a.top])
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)
    print(f"NEIGHBOUR_SKEW_GATE {verdict} judged={len(judged)} over_tt={len(over)} over_ff={len(over_ff)} landed={landed} "
          f"budget={a.budget_ps} near={a.near_um} skew_tt={json.dumps(out['skew_tt_ps'])} skew_ff={json.dumps(out['skew_ff_ps'])} intra={json.dumps(out['intra_region'])} inter={json.dumps(out['inter_region'])}")
    for j in out['worst'][:10]:
        print(f"  {j['skew_tt_ps']:8.1f} / {j['skew_ff_ps']} ps TT/FF  {j['dist_um']:6.0f} um  {j['a']} <-> {j['b']}  [{j['region_a']}|{j['region_b']}]")
    sys.exit({'PASS': 0, 'FAIL': 1}.get(verdict, 2))


if __name__ == '__main__':
    main()
