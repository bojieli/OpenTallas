import json,sys,statistics as st
d=sys.argv[1]; corner=sys.argv[2] if len(sys.argv)>2 else 'TT'
P=json.load(open(d+'/place.json')); N=json.load(open(d+'/nets.json'))['nets']
A={}
for l in open(d+f'/tree_{corner}.txt'):
    t,n,amax,amin,sl=l.split(); 
    if t=='N': A[n]=float(amax)
segs=[]
for net in N:
    dv=net['drv']
    if dv not in A: continue
    for ld in net['loads']:
        if ld not in A or ld not in P or dv not in P: continue
        L=abs(P[ld]['x']-P[dv]['x'])+abs(P[ld]['y']-P[dv]['y'])
        if L<=200: continue
        segs.append((L,A[ld]-A[dv],P[dv]['kind'],P[ld]['kind']))
r=[1000*dl/L for L,dl,_,_ in segs]
print(corner,'segs',len(segs),'median ps/mm %.1f'%st.median(r),'aggregate %.1f'%(1000*sum(s[1] for s in segs)/sum(s[0] for s in segs)),
 'p10 %.1f p90 %.1f'%(st.quantiles(r,n=10)[0],st.quantiles(r,n=10)[-1]),'mean L um %.0f'%st.mean(s[0] for s in segs))
rr=[1000*dl/L for L,dl,a,b in segs if a=='rep' and b=='rep']
if rr: print(' rep->rep',len(rr),'median %.1f'%st.median(rr))
