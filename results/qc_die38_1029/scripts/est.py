import json,collections,bisect,sys
D=sys.argv[1]
W=json.load(open(D+'/fixed_wires.json'))
pg=json.load(open(D+'/pg_rects.json'))
straps=sorted((r[3],r[5]) for r in pg if r[1]=='M8'); lo=[a for a,b in straps]
def bad(y,sp=.32,h=.04):
    j=bisect.bisect_right(lo,y+sp+h)-1
    return any(y+h>a-sp and y-h<b+sp for a,b in straps[max(0,j-1):j+2])
C=collections.Counter(); d=[]
for w in W:
    ty=w['trunk_tap'][1]
    for ld,bx,by in w['branches']:
        if not ld.startswith('port:provider'):continue
        if w['horiz']:
            r=abs(by-ty); d.append(r)
            C['h']+=1; C['h_on_trunk']+= r<1e-6; C['h_r<=2.5']+= r<=2.5; C['h_r<=8.64']+= r<=8.64; C['h_r<=0.8']+=r<=0.8
            C['h_pgbad']+=bad(by)
        else:
            C['v']+=1; C['v_pgbad']+=bad(by)
print(dict(C))
d.sort(); n=len(d); print('h riser quantiles', [round(d[int(q*(n-1))],3) for q in (0,.1,.25,.5,.75,.9,.99,1)])
top=json.load(open(D+'/diag_top.json'))
H={w['name']:w['horiz'] for w in W}
prov=json.load(open(D+'/provider_endpoints.json'))['rows']
pys=collections.defaultdict(list)
for r in prov:pys[r['net']].append(r['xy'])
T=collections.Counter(); S=collections.Counter()
for i,s,net,layer,x0,y0,x1,y1,ag,kd in top['hits']:
    if s!=2 or layer!='M8':continue
    cy=(y0+y1)/2
    isprov=any(abs(cy-py)<1.0 and abs((x0+x1)/2-px)<12 for px,py in pys.get(net,()))
    if not isprov:continue
    T[('H' if H.get(net) else 'V',ag[2],kd,'w=%.3f'%(x1-x0) if x1-x0<0.3 else 'seg')]+=1
for k,v in T.most_common(20):print(v,k)
