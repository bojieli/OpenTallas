# who.py JSON ax pos w0 w1 : bus segments crossing the cut in the window (bits, bus, endpoints)
import sys, json
d=json.load(open(sys.argv[1])); ax=sys.argv[2]; cp=float(sys.argv[3]); w0,w1=float(sys.argv[4]),float(sys.argv[5])
I={i['n']:i for i in d['insts']}
cen=lambda i:(i['x']+i['w']/2,i['y']+i['h']/2)
cl=lambda i,P:(min(max(P[0],i['x']),i['x']+i['w']),min(max(P[1],i['y']),i['y']+i['h']))
p0,p1,o0,o1=(0,2,1,3) if ax=='x' else (1,3,0,2)
for b,c,bits,eps in d['buses']:
    p=[I[e] for e in eps if e in I]
    if len(p)<2 or c=='clock_trunk': continue
    for a,q in (list(zip(p,p[1:])) if len(p)==2 else [(p[0],t) for t in p[1:]]):
        A,Q=cl(a,cen(q)),cl(q,cen(a)); S=(A[0],A[1],Q[0],Q[1])
        if min(S[p0],S[p1])<cp<max(S[p0],S[p1]):
            oc=S[o0]+(S[o1]-S[o0])*(cp-S[p0])/(S[p1]-S[p0])
            if w0<=oc<w1: print(bits,b,c,a['n'],[round(v) for v in A],q['n'],[round(v) for v in Q])
