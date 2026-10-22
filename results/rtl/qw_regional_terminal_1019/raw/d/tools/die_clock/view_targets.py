#!/usr/bin/env python3
"""DIE-CLOCK: per-master in-arc clock insertion R table (build.py --targets) from a die case's view list
(Claude DIE-CLOCK-HBM 2026-10-16).

  view_targets.py --case-manifest CASE/manifest.json --ref-root physical/ref_tile --out targets.json

For every master in the case manifest's 'views' map:
  * REAL (status starting ROUTED): R = the routed view's insertion.json <corner>.boundary.mean (the die clock delivery
    rule, as tools/s81/die_sta.py arcs_insertion), per clock pin from clock_measurements[pin] when that pin was measured.
    The insertion.json is looked up as <ref-root>/*/views/<master>/insertion.json; when several jobs carry the master the
    one whose <master>.lef sha256 equals the case's consumed_view_sha256 is taken, else the run fails (ambiguous).
  * SYNTH (status starting SYNTH): ideal-clock estimate, R = 0, labelled 'SYNTH_IDEAL_R0'.
  * REAL without an insertion.json: R = 0, labelled 'REAL_NO_INSERTION_JSON' (listed for the owner of that view).
Output: {"schema", "masters": {m: {"view", "source", "insertion_in_arcs_ps": [ss, ff, tt],
                                    "insertion_per_clock_pin_ps": {pin: [ss, ff, tt]}}}, "summary"}.
"""
import argparse
import glob
import hashlib
import json
import os
from pathlib import Path

CORNERS = ('ss', 'ff', 'tt')


def corner_means(d):
    """[ss, ff, tt] boundary means of one insertion record, or None if ss/ff are missing (tt falls back to their mean)."""
    if not d:
        return None
    v = {c: ((d.get(c) or {}).get('boundary') or {}) for c in CORNERS}
    if not (v['ss'].get('n') and v['ff'].get('n')):
        return None
    ss, ff = v['ss']['mean'], v['ff']['mean']
    tt = v['tt']['mean'] if v['tt'].get('n') else round((ss + ff) / 2, 1)
    return [ss, ff, tt]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pick(master, ref_root, want_sha):
    c = sorted(glob.glob(os.path.join(ref_root, '*', 'views', master, 'insertion.json')))
    if not c:
        return None, 'none'
    if want_sha:
        hit = [p for p in c if os.path.exists(os.path.join(os.path.dirname(p), f'{master}.lef'))
               and sha(os.path.join(os.path.dirname(p), f'{master}.lef')) == want_sha]
        if hit:
            return hit[0], 'lef_sha_match'
    if len(c) == 1:
        return c[0], 'only_candidate_lef_unmatched' if want_sha else 'only_candidate'
    raise SystemExit(f'{master}: {len(c)} insertion.json candidates and none matches the consumed LEF sha')


def convert(case, ref_root):
    views = case['views']
    shas = case.get('consumed_view_sha256', {})
    out, summ = {}, {}
    for m, status in sorted(views.items()):
        r = dict(view=status.split()[0], insertion_in_arcs_ps=[0.0, 0.0, 0.0])
        if status.startswith('SYNTH'):
            r['source'] = 'SYNTH_IDEAL_R0'
        else:
            p, how = pick(m, ref_root, shas.get(f'{m}.lef'))
            if not p:
                r['source'] = 'REAL_NO_INSERTION_JSON'
            else:
                j = json.loads(Path(p).read_text())
                top = corner_means(j)
                if top is None:
                    r['source'] = 'REAL_INSERTION_JSON_EMPTY'
                else:
                    r['source'] = f'insertion.json ({how})'
                    r['insertion_json'] = os.path.relpath(p, os.path.dirname(os.path.abspath(ref_root)))
                    r['insertion_in_arcs_ps'] = top
                    pp = {}
                    for pin, d in sorted((j.get('clock_measurements') or {}).items()):
                        v = corner_means(d)
                        if v:
                            pp[pin] = v
                    if pp:
                        r['insertion_per_clock_pin_ps'] = pp
        out[m] = r
        summ[r['source'].split(' ')[0]] = summ.get(r['source'].split(' ')[0], 0) + 1
    return dict(schema='opentallas.die_clock.targets.v1',
                rule='R = routed view insertion.json <corner>.boundary.mean (per clock pin when measured); SYNTH views '
                     'have ideal clocks: R = 0, labelled SYNTH_IDEAL_R0', masters=out, summary=summ)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--case-manifest', required=True)
    ap.add_argument('--ref-root', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    rec = convert(json.loads(Path(a.case_manifest).read_text()), a.ref_root)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['summary']))


if __name__ == '__main__':
    main()
