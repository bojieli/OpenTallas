"""PATH-S81-PD: FALLBACK-S81-2 landed-crossing report on the routed region trees (regions adapter of
fallback_land_report_head.py).  usage: land_report_regions.py RUN_DIR LANDED_CROSSINGS REGIONS OUT.json
Entry arrival of a partition = its partition clock taps t_<part>__clk_t* (core taps c* excluded: their early-by-
insertion offset is a die-STA annotation the ctree does not model).  Per landed crossing:
  d_mean = mean(dst taps) - mean(src taps);  d_worst = max over (src tap, dst tap) of |a_dst - a_src|.
Also: region-root arrival spread (N lines of the region-root cells), and for every region the worst related
(port-connected, same region) partition pair."""
import json, sys, collections, statistics as st
from pathlib import Path
run = Path(sys.argv[1]); LC = json.load(open(sys.argv[2])); RG = json.load(open(sys.argv[3]))
tree = json.load(open(run / 'clk' / 'tree.json'))
reg = RG['part_region']
roots = {str(n['id']): n['region_root'] for n in tree['nodes'].values() if 'region_root' in n}
out = {}
for C in ('TT', 'FF'):
    tap = collections.defaultdict(list); node = {}
    for ln in (run / f'out_{C}' / f'arr_{C}.txt').read_text().splitlines():
        x = ln.split()
        if not x: continue
        if x[0] == 'T':
            name = x[1][2:]; part, _, t = name.rpartition('__clk_')
            if t.startswith('t'): tap[part].append(float(x[2]))
        elif x[0] == 'N':
            node[x[1]] = float(x[2])
    rows = []
    for r in LC['ports']:
        s, d = r['src'], r['dst']
        if not tap[s] or not tap[d]: rows.append(dict(port=r['port'], missing=True)); continue
        dm = st.mean(tap[d]) - st.mean(tap[s])
        dw = max(max(tap[d]) - min(tap[s]), max(tap[s]) - min(tap[d]))
        rows.append(dict(port=r['port'], src=s, dst=d, d_mean=dm, d_worst=dw))
    ok = [x for x in rows if not x.get('missing')]
    rootarr = {tag: node.get(tree['node_buf'][i]) for i, tag in roots.items()}
    ra = [v for v in rootarr.values() if v is not None]
    # related intra-region pairs: port-connected partitions in the same region (from landed table regions + plan ports unknown here:
    # use all partition pairs inside each region -> conservative)
    byreg = collections.defaultdict(list)
    for p, t in reg.items():
        if tap[p]: byreg[t].append(p)
    worst_reg = {}
    for t, ps in byreg.items():
        lo = min(min(tap[p]) for p in ps); hi = max(max(tap[p]) for p in ps)
        worst_reg[t] = dict(parts=len(ps), spread_ps=round(hi - lo, 2))
    phy = {k: v for k, v in worst_reg.items() if k.startswith('hard_')}
    out[C] = dict(crossings=len(rows), missing=len(rows) - len(ok),
                  max_abs_d_mean=round(max(abs(x['d_mean']) for x in ok), 2),
                  max_d_worst=round(max(x['d_worst'] for x in ok), 2),
                  over_budget_mean=sum(abs(x['d_mean']) > 416.5 for x in ok),
                  over_budget_worst=sum(x['d_worst'] > 416.5 for x in ok),
                  worst5=sorted(ok, key=lambda x: -x['d_worst'])[:5],
                  insertion_ps=[round(min(min(v) for v in tap.values() if v), 1), round(max(max(v) for v in tap.values() if v), 1)],
                  region_root_arrival=dict(n=len(ra), min=round(min(ra), 1), max=round(max(ra), 1), spread=round(max(ra) - min(ra), 1)),
                  region_spread_max=max(worst_reg.items(), key=lambda kv: kv[1]['spread_ps']),
                  phy_region=phy)
    d = {k: v for k, v in out[C].items() if k != 'worst5'}
    print(C, json.dumps(d))
    for x in out[C]['worst5']: print('   ', C, json.dumps({k: (round(v, 1) if isinstance(v, float) else v) for k, v in x.items()}))
# drift
json.dump(out, open(sys.argv[4], 'w'), indent=1)
