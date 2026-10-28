import json,collections,re,sys
d=json.load(open(sys.argv[1])); s=json.load(open(sys.argv[2]))
by={n["edge"]:n for n in s["nets"]}
kind={v['group']:v['kind'] for v in s['cell_sites'].values()}
drv=collections.defaultdict(list)
for n in s['nets']: drv[n['drv']].append(n)
fail_edges={x['edge'] for x in d['rows']}
fail_drv=collections.Counter(by[x['edge']]['drv'] for x in d['rows'])
# failing driver = the net drv; also errors at load end (escape jog ckt_X) attribute to load cell
def comp(g):
    ps=drv[g]; return (kind[int(g[1:])], tuple(sorted(collections.Counter((p['layer'],p['ndr']) for p in ps).items())))
allc=collections.Counter(comp(g) for g in drv); fc=collections.Counter(comp(g) for g in fail_drv)
print('drivers total',len(drv),'failing',len(fail_drv))
for k,v in sorted(allc.items(),key=lambda kv:-fc.get(kv[0],0))[:30]: print(fc.get(k,0),'/',v,k)
