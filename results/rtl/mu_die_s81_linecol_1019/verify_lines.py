#!/usr/bin/env python3
"""MU-DIE-S81/LINECOL (10-19): independent line-collision check of compiled layer programmes (the TOK witness method:
dv_cut_replay.landed_words, >1 distinct beat on one (slice, ri_e / ri_w, landed edge)), single user AND the multi-user
superposition of one die copy (every user = the programme shifted by its mu_slots start - the copy's first start), plus
the reservation cost against a reference (pre-fix) programme.
  verify_lines.py --die-v DIE --new DIR_<L>... [--old DIR] [--mu-slots mu_slots.json] -> JSON on stdout"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/s81_dv'))
import dv_cut_replay as R


def slots(die, p):
    S = json.loads((p / 'schedule.json').read_text())
    T = {t['i']: t for t in json.loads((p / 'prog/ctl_templates.json').read_text())['templates']}
    words, _, _, _ = R.landed_words(S, T, die)
    at = defaultdict(set)
    for w in words:
        if w['port'] in ('ri_e', 'ri_w'):
            src = str(w['event'].get('derived_from', '')).split(' via ')[0]
            at[(w['inst'], w['port'], w['cycle_land'])].add(w['event']['tag'] + ('|gunit' if 'u_gunit' in src else ''))
    return S, at


def span(p, S):
    cal = json.loads((p / 'prog/calendar.json').read_text())
    end = max(j['layer_issue0'] + j['end_age'] for j in cal['job'])
    return dict(last_event=max(e['cycle'] for e in S['events']), calendar_end=end)


def ra_cmd(p):
    cal = json.loads((p / 'prog/calendar.json').read_text())
    return [j['layer_issue0'] + r['issue'] for j in cal['job'] for r in j['rows'] if 'softplus_sqrt' in r['what']]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--new', required=True)
    ap.add_argument('--old')
    ap.add_argument('--mu-slots')
    a = ap.parse_args()
    die = R.DieBuild(a.die_v)
    p = Path(a.new)
    S, at = slots(die, p)
    col = {k: sorted(v) for k, v in at.items() if len(v) > 1}
    out = dict(prog=str(p), line_slots=len(at), collisions=len(col), witness=[[list(k), v] for k, v in sorted(col.items())][:12],
               line_delay=(S.get('line_slots') or {}).get('line_delay'), span=span(p, S), ra_cmd=ra_cmd(p))
    if a.old:
        So, ato = slots(die, Path(a.old))
        out['old'] = dict(collisions=sum(1 for v in ato.values() if len(v) > 1), span=span(Path(a.old), So), ra_cmd=ra_cmd(Path(a.old)))
        out['cost_edges'] = {k: out['span'][k] - out['old']['span'][k] for k in out['span']}
    if a.mu_slots:
        mu = json.loads(Path(a.mu_slots).read_text())
        res = {}
        for cp in sorted({r['copy'] for r in mu['rows']}):
            rows = [r for r in mu['rows'] if r['copy'] == cp]
            s0 = min(r['start'] for r in rows)
            shifts = [int(r['start'] - s0) for r in rows]
            occ = defaultdict(set)
            for u, sh in enumerate(shifts):
                for (i, f, c), v in at.items():
                    occ[(i, f, c + sh)] |= {f'{t}@u{u}' for t in v}
            bad = {k: sorted(v) for k, v in occ.items() if len(v) > 1}
            res[cp] = dict(users=len(rows), min_shift_gap=min((b - a_ for a_, b in zip(shifts, shifts[1:])), default=None),
                           prog_span=out['span']['last_event'], collisions=len(bad),
                           witness=[[list(k), v] for k, v in sorted(bad.items())][:6])
        out['mu'] = res
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
