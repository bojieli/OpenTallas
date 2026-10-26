"""PLAN-ICG-MODEL: per-domain decomposition of measured routed clock trees (stages_/sinks_ TSV from icg_measure.tcl)."""
import csv, json, sys, statistics as st
from collections import defaultdict
def rows(p):
    return list(csv.DictReader(open(p), delimiter='\t'))
def f(v):
    return None if v in ('NA', '', None) else float(v)
out = {}
for core in sys.argv[2:]:
    for c in ('TT', 'FF'):
        S = rows(f'{sys.argv[1]}/{core}/out/stages_{c}.tsv'); K = rows(f'{sys.argv[1]}/{core}/out/sinks_{c}.tsv')
        st_by = {r['name']: r for r in S}
        icgs = [r for r in S if r['kind'] == 'icg']
        dom = defaultdict(list)
        for r in K:
            if f(r['arr']) is None: continue
            dom[r['icg']].append(r)
        # nested ICGs are sinks of their parent domain
        for g in icgs:
            dom[g['icg']].append(dict(pin=g['name'] + '/CLK', x_um=g['x_um'], y_um=g['y_um'], below_icg=g['below_icg'], arr=g['in_arr'], master=g['master'], nested=True))
        res = []
        for name, ss in dom.items():
            if name == 'ROOT':
                ref = 0.0; kind = 'root'; d_icg = None; slew = None; fo = None; icgxy = None
            else:
                g = st_by[name]; ref = f(g['out_arr']); kind = 'icg'; d_icg = ref - f(g['in_arr']); slew = f(g['in_slew']); fo = int(g['fanout']); icgxy = [f(g['x_um']), f(g['y_um'])]
            a = [f(s['arr']) - ref for s in ss]; lv = [int(s['below_icg']) for s in ss]
            xs = [f(s['x_um']) for s in ss]; ys = [f(s['y_um']) for s in ss]
            # buffers in this domain by level
            bl = defaultdict(list)
            for b in S:
                if b['kind'] != 'icg' and b['icg'] == name:
                    bl[int(b['below_icg']) + 1].append(b)
            lev = {k: dict(n=len(v), mean_stage_ps=st.mean(f(b['out_arr']) - (f(st_by[b['parent']]['out_arr']) if b['parent'] in st_by else 0.0) for b in v),
                           mean_cell_ps=st.mean(f(b['out_arr']) - f(b['in_arr']) for b in v), mean_fanout=st.mean(int(b['fanout']) for b in v),
                           masters=dict(sorted(((m, sum(1 for b in v if b['master'] == m)) for m in {b['master'] for b in v}), key=lambda t: -t[1])[:4]))
                   for k, v in sorted(bl.items())}
            res.append(dict(domain=name, kind=kind, n=len(ss), nested=sum(1 for s in ss if s.get('nested')),
                            levels=dict(sorted(((k, lv.count(k)) for k in set(lv)))), level_mean=st.mean(lv),
                            bbox_um=[min(xs), min(ys), max(xs), max(ys)], icg_xy=icgxy,
                            gclk_arr=ref, icg_delay_ps=d_icg, icg_in_slew_ps=slew, gclk_fanout=fo,
                            sub_mean=st.mean(a), sub_min=min(a), sub_max=max(a), abs_mean=st.mean(f(s['arr']) for s in ss),
                            per_level=lev))
        res.sort(key=lambda r: -r['n'])
        allarr = [f(r['arr']) for r in K if f(r['arr']) is not None]
        out.setdefault(core, {})[c] = dict(sinks=len(K), all_mean=st.mean(allarr), all_min=min(allarr), all_max=max(allarr), icgs=len(icgs), domains=res)
json.dump(out, open(sys.argv[1] + '/decomp.json', 'w'), indent=1)
for core, d in out.items():
    for c, v in d.items():
        print(core, c, 'sinks', v['sinks'], 'icgs', v['icgs'], 'all mean/min/max %.1f/%.1f/%.1f' % (v['all_mean'], v['all_min'], v['all_max']))
        for r in v['domains'][:12]:
            print('  %-40s n=%6d lv=%s icg=%s gclk=%.1f sub %.1f/%.1f/%.1f bbox=%s fo=%s' % (r['domain'][-40:], r['n'], r['levels'], None if r['icg_delay_ps'] is None else round(r['icg_delay_ps'], 1), r['gclk_arr'], r['sub_mean'], r['sub_min'], r['sub_max'], [round(x) for x in r['bbox_um']], r['gclk_fanout']))
