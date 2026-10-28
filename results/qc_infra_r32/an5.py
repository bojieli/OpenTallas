import json,collections,re,sys
d=json.load(open(sys.argv[1])); s=json.load(open(sys.argv[2])); pat=sys.argv[3]
by={n["edge"]:n for n in s["nets"]}
G=collections.defaultdict(list)
for nm,v in s['cell_sites'].items(): G[v['group']].append(v)
def pos(g):
    v=G[int(g[1:])]; return (round(sum(u['origin_um'][0]+u['w']/2 for u in v)/len(v),2), round(min(u['origin_um'][1] for u in v)+0.135,2), v[0]['kind'], v[0]['part'])
k=0
for x in d['rows']:
    n=by[x['edge']]
    if re.search(pat, x['edge']+' '+x['detail']):
        print(x['detail'],x['edge'],n['layer'],n['ndr'],pos(n['drv']),pos(n['load']),n['pin_to_pin_um']); k+=1
        if k>=int(sys.argv[4]): break
