import sys,json,time
from pathlib import Path
tool=Path(__file__).resolve().parents[2]/"tools/die_plan"
sys.path.insert(0,str(tool if tool.is_dir() else Path(__file__).parent))
import lec
r=Path(sys.argv[1]);w=Path(sys.argv[2]);w.mkdir(exist_ok=True,parents=True)
log=[]; t=time.time()
L=lec.Lec(lec.read_aig(r/'gold.aig'),lec.read_map(r/'gold.map'),lec.read_aig(r/'gate.aig'),lec.read_map(r/'gate.map'))
elements=lec.slang_elements(r/'gold.aliases.json')
ren={k:lec.IDX.match(k)[1]+v for k,v in elements.items()
     if lec.IDX.match(k) and v.count('[')==1 and k in L.gp}
lec.normalize_gold_elements(L,elements,log)
skipped=[]
for sd,k,h in json.load(open(r/'hyp.json')):
    h=list(h)
    nk=ren.get(k,k) if sd in ('gold','both') else k
    points=L.gp if sd in ('gold','both') else L.tp
    if nk not in points and '#t' in nk and nk.replace('#t','') in points:
        nk=nk.replace('#t','')
    if nk not in points or (sd=='both' and nk not in L.tp):
        skipped.append((sd,k));continue
    if h[0]=='eq':
        if h[1]=='gold': h[2]=ren.get(h[2],h[2])
        target=L.gp if h[1]=='gold' else L.tp
        if h[2] not in target and '#t' in h[2] and h[2].replace('#t','') in target:
            h[2]=h[2].replace('#t','')
        if h[2] not in target:
            skipped.append((sd,k));continue
    elif h[0]!='const':
        skipped.append((sd,k));continue
    L.hyp[(sd,nk)]=tuple(h)
log.append('Skipped unavailable old normalized candidates: '+str(len(skipped)))
log.append('Prior seeds loaded as untrusted candidates: '+str(len(L.hyp)))
print(log[-1],flush=True)
n=0; iteration=0; cone_attempts=set()
while True:
    n+=lec.structural_constant_closure(L,log)
    n+=lec.structural_twin_closure(L,log)
    print('iteration',iteration,'structural added',n,flush=True)
    m,kind=L.build(with_compare=True,with_hyp=True)
    st=lec.prove(m,w,10000,log,tag='all'+str(iteration))
    bad={k:v for k,v in st.items() if v!='proved'}
    drop=[]
    for key in bad:
        if key.startswith('hyp:'):
            _,side,k=key.split(':',2)
            node=('both' if side=='bothg' else side,k)
            if node in L.hyp:drop.append(node)
    print('bad',len(bad),'rejected seed hypotheses',drop,flush=True)
    if not drop:
        proposed=0
        for key in bad:
            kinds=[kind[v] for v in m.cone_inputs(m.outs[m.onames.index(key)])]
            g=[k for sd,k in kinds if sd=='gold_only' and k.startswith('ff:')]
            tg=[k for sd,k in kinds if sd=='gate_only' and k.startswith('ff:')]
            if len(g)==len(tg)==1 and (g[0],tg[0]) not in cone_attempts:
                cone_attempts.add((g[0],tg[0]))
                L.hyp[('gate',tg[0])]=('eq','gold',g[0],0)
                proposed+=1
                print('Untrusted single-pair cone proposal',tg[0],g[0],flush=True)
        if not proposed:break
    for node in drop:L.hyp.pop(node,None)
    iteration+=1
bad_cones={key:[kind[v] for v in sorted(m.cone_inputs(m.outs[m.onames.index(key)]))] for key in bad}
(w/'bad_cones.json').write_text(json.dumps(bad_cones,indent=1))
(w/'replay.log').write_text('\n'.join(log))
(w/'hyp.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())]))
(w/'summary.json').write_text(json.dumps(dict(proved=len(st)-len(bad),total=len(st),bad=bad,added=n,elapsed=time.time()-t),indent=1))
(w/'replay.log').write_text('\n'.join(log))
(w/'hyp.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())]))
print(json.dumps(dict(proved=len(st)-len(bad),total=len(st),bad=bad,added=n,elapsed=time.time()-t)),flush=True)

raise SystemExit(1 if bad else 0)
