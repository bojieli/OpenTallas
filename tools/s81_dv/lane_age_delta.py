#!/usr/bin/env python3
"""S81-DIEPLACE: price a candidate plan's relay-station changes for the compiler / landing calendar.

Per link: stations N (base -> candidate), compiler lane age delta = ceil(N'/2) - ceil(N/2) half-cycle-pair edges at the
SAME landing K (landed age = ceil(N/2) + K + 1, dv_bind), relay bit-stages, and whether the land plan's die-STA E was
measured on a different N (stale -> the landing pilot must re-derive E/K on the candidate; never reuse silently).
Writes a compiler-facing table; it is a PRICE, not a timing result."""
import argparse, collections, hashlib, json, math
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True); ap.add_argument('--cand', required=True)
    ap.add_argument('--land-plan', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    B, C = json.load(open(a.base)), json.load(open(a.cand))
    lp = {r['link']: r for r in json.load(open(a.land_plan))['links']}
    bl = {l['i'].replace('-', '_'): l for l in B['links']}
    rows, by_cls = [], collections.Counter()
    for l in C['links']:
        nm = l['i'].replace('-', '_'); b = bl.get(nm)
        if b is None:
            rows.append(dict(link=nm, status='NEW_LINK', stations=l['s'])); continue
        if b['s'] == l['s']:
            continue
        r = lp.get(nm, {})
        da = math.ceil(l['s'] / 2) - math.ceil(b['s'] / 2)
        rows.append(dict(link=nm, cls=l['c'], bits=l['b'], stations_base=b['s'], stations_cand=l['s'],
                         compiler_age_delta_edges=da, relay_bit_stage_delta=(l['s'] - b['s']) * l['b'],
                         landed=bool(r), land_E_stale=bool(r), land_K_base=r.get('K'), bundle=r.get('bundle'),
                         len_um_base=b.get('L'), len_um_cand=l.get('L')))
        by_cls[l['c']] += 1
    bundles = sorted({r['bundle'] for r in rows if r.get('bundle')})
    tot = dict(changed_links=len(rows), stations_base=sum(l['s'] for l in B['links']), stations_cand=sum(l['s'] for l in C['links']),
               age_delta_hist=dict(collections.Counter(r.get('compiler_age_delta_edges') for r in rows)),
               max_age_delta=max((r.get('compiler_age_delta_edges', 0) for r in rows), default=0),
               bundles_to_reequalise=bundles, by_class=dict(by_cls))
    rec = dict(schema='opentallas.s81_dv.lane_age_delta.v1', scope='PRICE_FOR_COMPILER_NOT_TIMING',
               base=dict(path=a.base, sha256=hashlib.sha256(Path(a.base).read_bytes()).hexdigest()),
               cand=dict(path=a.cand, sha256=hashlib.sha256(Path(a.cand).read_bytes()).hexdigest()),
               land_plan=a.land_plan, rule='landed age = ceil(N/2) + K + 1; K re-derived by dv_land_pilot on the candidate die STA',
               totals=tot, rows=rows)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(tot, indent=1))


if __name__ == '__main__':
    main()
