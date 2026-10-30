#!/usr/bin/env python3
"""DIE-QC-38: classify the R7 prebuild top-access conflicts and the encoder census by shape source + endpoint kind."""
import json, pickle, sys, collections, bisect
D=sys.argv[1]
top=json.load(open(D+'/diag_top.json')); pk=pickle.load(open(D+'/diag_shapes.pkl','rb'))
shapes=pk['shapes']; n1,n2,n3=pk['n']; census=pk['census']
prov=json.load(open(D+'/provider_endpoints.json'))['rows']
pxs=collections.defaultdict(list)
for r in prov: pxs[r['net']].append(tuple(r['xy']))
ea=json.load(open(D+'/endpoint_access.json'))
nat=collections.defaultdict(list)
for k,v in ea.items(): nat[v['net']].append(tuple(v['entry_xy_um']))
src={1:'stair(cell stacks)',2:'port_access',3:'clock_cell_via'}
def kind_of(i,net,x0,y0,x1,y1):
    s=src[1 if i<n1 else 2 if i<n2 else 3]
    if s!='port_access':return s
    cx,cy=(x0+x1)/2,(y0+y1)/2
    if any(abs(cy-py)<.5 and min(abs(cx-px),abs(x0-px),abs(x1-px))<12 for px,py in pxs.get(net,())):return 'port:provider_M1'
    if any(abs(cy-py)<.5 for px,py in nat.get(net,())):return 'port:native_M7'
    return 'port:other(root/drop)'
C=collections.Counter(); ex={}
ys=collections.Counter()
for h in top['hits']:
    i,s,net,layer,x0,y0,x1,y1,ag,kd=h
    k=(kind_of(i,net,x0,y0,x1,y1),layer,str(ag[2]) if len(ag)>2 else '?',kd); C[k]+=1; ex.setdefault(k,h)
print('TOP total',len(top['hits']))
for k,v in C.most_common():print(' ',v,k)
# provider endpoints whose pin y is in an M8 PG-forbidden band (strap +- .32 + .04)
pg=json.load(open(D+'/pg_rects.json'))
straps=sorted((r[3],r[5]) for r in pg if r[1]=='M8')
lo=[a for a,b in straps]
def bad(y,sp=.32,h=.04):
    j=bisect.bisect_right(lo,y+sp+h)-1
    for a,b in straps[max(0,j-1):j+2]:
        if y+h>a-sp and y-h<b+sp:return True
    return False
nb=sum(bad(r['xy'][1]) for r in prov)
print('PROVIDER endpoints',len(prov),'pin y inside strap+-(0.32+0.04)',nb, 'min-spacing variant', sum(bad(r['xy'][1],sp=.08) for r in prov))
# census
cc=collections.Counter(); cex={}
for d in census['examples']:
    kind,layer,net,bnet,x0,y0,x1,y1,brect,a,b=d
    ka=kind_of(a,net,x0,y0,x1,y1); kb=kind_of(b,bnet,*brect)
    key=(kind,layer,tuple(sorted([ka,kb]))); cc[key]+=1; cex.setdefault(key,d)
print('CENSUS shorts',census['shorts'],'spacing',census['spacing'],'detail rows',len(census['examples']))
for k,v in cc.most_common():print(' ',v,k,json.dumps(cex[k])[:300])
json.dump(dict(top={str(k):v for k,v in C.items()},top_examples={str(k):v for k,v in ex.items()},census={str(k):v for k,v in cc.items()},census_examples={str(k):v for k,v in cex.items()},provider_in_band=nb),open(D+'/classify.json','w'),indent=1)
