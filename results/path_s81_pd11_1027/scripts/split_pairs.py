import json, sys, math
B='/srv/opentallas-scratch2/claude/path-s81-pd7-1026/pd9/me1'
S=json.load(open('/srv/opentallas-scratch2/claude/codex-s81-mc-1027/mc_TT.json')); P=json.load(open(B+'/place.json'))
rtj=json.load(open(S['routed'] if isinstance(S['routed'],str) and S['routed'].endswith('.json') else B+'/mesh_TT.json'))['stubs']
M=json.load(open(B+'/mesh.json'))
L=S['loads']; arr=S['arr']; gv=S['grad_vec_ps']; ns=len(arr)
XS, YS = 15972.92, 12376.935   # ckm_n0 site (root branch point)
xy={k:(P[k]['x'],P[k]['y']) for k in L if k in P}
gap=[rtj[k]['late']-arr[0][i] if k in rtj else 0.0 for i,k in enumerate(L)]
idx=[i for i,k in enumerate(L) if k in xy]
R=1000.0; cell={}
for i in idx:
    x,y=xy[L[i]]; cell.setdefault((int(x//R),int(y//R)),[]).append(i)
rows=[]
for i in idx:
    x,y=xy[L[i]]; gx,gy=int(x//R),int(y//R)
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            for j in cell.get((gx+dx,gy+dy),[]):
                if j<=i: continue
                xj,yj=xy[L[j]]; d=abs(x-xj)+abs(y-yj)
                if d>R: continue
                sx=(x-XS)*(xj-XS)<0; sy=(y-YS)*(yj-YS)<0
                ds=[arr[s][i]-arr[s][j] for s in range(ns)]
                mcv=ds[1:]; mu=sum(mcv)/len(mcv); sd=(sum((v-mu)**2 for v in mcv)/(len(mcv)-1))**.5
                mct=max(max(abs(v) for v in ds),abs(mu)+3*sd)
                g=math.hypot(gv[i][0]-gv[j][0],gv[i][1]-gv[j][1]); gp=abs(gap[i]-gap[j])
                rows.append((mct+gp+g,abs(ds[0]),mct-abs(ds[0]),gp,g,d,sx,sy,L[i],L[j],(round(x),round(y)),(round(xj),round(yj))))
def q(v,p): v=sorted(v); return round(v[min(len(v)-1,int(p*len(v)))],1) if v else None
for lab,f in (('x-split only',lambda r:r[6] and not r[7]),('y-split only',lambda r:r[7] and not r[6]),('both',lambda r:r[6] and r[7]),('neither',lambda r:not r[6] and not r[7])):
    rr=[r for r in rows if f(r)]
    print(lab,len(rr),'U p50/p99/max',q([r[0] for r in rr],.5),q([r[0] for r in rr],.99),round(max(r[0] for r in rr),1) if rr else None,
          '| nominal p50/max',q([r[1] for r in rr],.5),round(max(r[1] for r in rr),1) if rr else None,'| MCexcess p50/max',q([r[2] for r in rr],.5),round(max(r[2] for r in rr),1) if rr else None,
          '| grad p50/max',q([r[4] for r in rr],.5),round(max(r[4] for r in rr),1) if rr else None)
big=[r for r in rows if r[0]>120]
print('U>120:',len(big),'straddle x',sum(r[6] for r in big),'straddle y',sum(r[7] for r in big),'neither',sum(1 for r in big if not r[6] and not r[7]))
print('worst 10: U nominal MCexcess gap grad dist sx sy a b')
for r in sorted(rows,reverse=True)[:10]: print(' ',[round(v,1) if isinstance(v,float) else v for v in r])
# nearest drivers each side
tr={}
for l in open(B+'/tree_TT.txt'):
    f=l.split()
    if f and f[0]=='D': tr[f[1]]=float(f[2])
dv=[(v['site'][0],v['site'][1],v) for v in M['drivers'].values()]
for nm,ax,c in (('x-split',0,XS),('y-split',1,YS)):
    lo=min((c-p[ax],p) for p in dv if p[ax]<c); hi=min((p[ax]-c,p) for p in dv if p[ax]>c)
    print(nm,'nearest driver below/left',round(lo[0],1),'um at',lo[1][:2],'; above/right',round(hi[0],1),'um at',hi[1][:2])
    # per strap/row: mean distance of nearest drivers & arrival diff across the line
    near=[p for p in dv if abs(p[ax]-c)<600]
    a=[tr.get(p[2]['cells'][0]) for p in near if p[ax]<c]; b=[tr.get(p[2]['cells'][0]) for p in near if p[ax]>c]
    a=[v for v in a if v is not None]; b=[v for v in b if v is not None]
    print('  drivers within 600 um: side- n',len(a),'mean in-arr',round(sum(a)/len(a),1),'side+ n',len(b),'mean',round(sum(b)/len(b),1),'range-',round(min(a),1),round(max(a),1),'range+',round(min(b),1),round(max(b),1))
