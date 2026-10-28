import json,collections,sys
s=json.load(open(sys.argv[1])); X,Y,R=float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4])
G=collections.defaultdict(list)
for nm,v in s['cell_sites'].items(): G[v['group']].append(v)
def pos(g):
    v=G[int(g[1:])]; return (round(sum(u['origin_um'][0]+u['w']/2 for u in v)/len(v),2), round(min(u['origin_um'][1] for u in v)+0.135,2))
for n in s['nets']:
    a,b=pos(n['drv']),pos(n['load'])
    xs=sorted([a[0],b[0]]); ys=sorted([a[1],b[1]])
    near=lambda p: abs(p[0]-X)<R and abs(p[1]-Y)<6
    passes = n['layer']=='M8' and xs[0]-1<X<xs[1]+1 and any(abs(y-Y)<6 for y in ys)
    if near(a) or near(b) or passes:
        print(n['edge'],n['layer'],n['ndr'],a,G[int(n['drv'][1:])][0]['kind'],'->',b,G[int(n['load'][1:])][0]['kind'])
