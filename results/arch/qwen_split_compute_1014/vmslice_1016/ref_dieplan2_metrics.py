import json,math,collections,sys
sys.path.insert(0,'/home/ubuntu/wt/q-dieplan2-1016/results/arch/qwen_tp8_1012')
def st(f):
    d=json.load(open(f)); I={i['n']:i for i in d['insts']}
    c=lambda n:(I[n]['x']+I[n]['w']/2,I[n]['y']+I[n]['h']/2)
    S=collections.defaultdict(lambda:[0,0]); bm=0
    for b,cl,bits,eps in d['buses']:
        if cl in ('clock_trunk','reset') or len(eps)<2: continue
        a=c(eps[0])
        for q in eps[1:]:
            p=c(q); L=abs(a[0]-p[0])+abs(a[1]-p[1]); s=max(0,math.ceil(L/500)-1)
            S[cl][0]+=s; S[cl][1]=max(S[cl][1],s); bm+=bits*L/1000
    W=max(i['x']+i['w'] for i in I.values()); H=max(i['y']+i['h'] for i in I.values())
    return dict(bitmm=round(bm), stages=sum(v[0] for v in S.values()), max_chain=max(v[1] for v in S.values()), die=[round(W+21.6,2),round(H+21.6,2)], mm2=round((W+21.6)*(H+21.6)/1e6,1), insts=len(I))
def cut(f, plan='M6', top=40):
    import cuts as C
    C.CAP_MODE='v3'; C.CLUSTER_PLAN=plan
    A=C.Net(f); fine=A.fine(top=top)
    return max(x['util'] for x in fine), sum(1 for x in fine if x['util']>0.6)
for f in sys.argv[1:]:
    r=st(f); w,n=cut(f); r.update(worst_cut=round(w,3), lines_over_060=n); print(f, json.dumps(r))
