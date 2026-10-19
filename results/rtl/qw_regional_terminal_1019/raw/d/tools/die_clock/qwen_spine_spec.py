#!/usr/bin/env python3
"""GEN16 10-19: spine variant of a Qwen compute die clock spec (landed-regions standard, item 1 + item 3 check).

  qwen_spine_spec.py --spec D/spec.json --pairs D/landed_pairs_pre.json --out-spec D/spec_V.json --out-families
      D/families_V.json [--source clk_rx/pll_rK[0]] [--neighbours] [--budget 60]

Every region tree gets a regional clock entry (local_root = sink median; root buffer there); every region of the spine
period is fed by ONE buffered spine from --source (default: the stream root with the most sinks).  Families: all
spine members form ONE synchronous family (they share the spine source), so die_clock_check judges every communicating
cross-region pair at TT and FF (<= 80 ps); the spec records the unlanded (NEIGHBOUR/GAP) region pairs and their
connected components for spine_neighbour_report.py; every other region is its own family.
--neighbours also asks build.py to trim those pairs (neighbour_budget_ps); never a die-wide target."""
import argparse
import collections
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', required=True)
    ap.add_argument('--pairs', required=True)
    ap.add_argument('--out-spec', required=True)
    ap.add_argument('--out-families', required=True)
    ap.add_argument('--source')
    ap.add_argument('--period', type=float, default=833.333333)
    ap.add_argument('--neighbours', action='store_true')
    ap.add_argument('--budget', type=float, default=60.0)
    a = ap.parse_args()
    sp = json.load(open(a.spec))
    for t in sp['trees']:
        t['local_root'] = 'median'
    stream = [t for t in sp['trees'] if abs(t['period'] - a.period) < 1e-3]
    src = a.source or max(stream, key=lambda t: t.get('sinks', 0))['root']
    sp['clock_at_root_buffer'] = True          # non-spine regions (other periods) keep their ideal entry
    sp['spine'] = dict(source=src, period=a.period)
    sp['note'] = (sp.get('note', '') + ' GEN16 spine: regional entries (local root buffer at the sink median) fed by '
                  f'one buffered DME spine from {src}; clock defined at the spine source; families = components of the '
                  'unlanded cross-region root pairs (NEIGHBOUR check).')
    name = {t['root']: t['name'] for t in sp['trees']}
    lp = json.load(open(a.pairs))
    par = {t['root']: t['root'] for t in sp['trees']}

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    nb = set()
    for ra, rb in lp.get('gap_root_pairs', []):
        if ra in par and rb in par and ra != rb:
            par[f(ra)] = f(rb)
            nb.add(tuple(sorted((name[ra], name[rb]))))
    # one synchronous family = every spine member (their arrivals share the spine source: die_clock_check's root_of
    # walks up to it), so every communicating cross-region pair among them is judged; other periods stay singletons.
    # The NEIGHBOUR verdict is then read per region pair of the unlanded components (spine_neighbour_report).
    fam = collections.defaultdict(list)
    for t in sp['trees']:
        fam['spine' if t in stream else name[t['root']]].append(t['root'])
    fam['spine'] += [src, 'dc_spine_src']
    sp['neighbour_components'] = sorted(sorted(name[r] for r in par if f(r) == c) for c in {f(r) for r in par}
                                        if sum(1 for r in par if f(r) == c) > 1)
    sp['neighbour_pairs'] = sorted(map(list, nb))
    if a.neighbours:
        sp['neighbours'] = sorted(map(list, nb))
        sp['neighbour_budget_ps'] = a.budget
    json.dump(sp, open(a.out_spec, 'w'), indent=1)
    json.dump(fam, open(a.out_families, 'w'), indent=1)
    big = max(sp['neighbour_components'], key=len, default=[])
    print('QCLK_SPINE_SPEC source', src, 'stream trees', len(stream), 'families', len(fam), 'largest component', len(big),
          'neighbour pairs', len(nb), 'trim' if a.neighbours else 'judge only')


if __name__ == '__main__':
    main()
