import pathlib,json,collections,sys
import lec_fsm as lec
lec.PROVE_JOBS=8
p=pathlib.Path('eng_e1r');o=pathlib.Path('eng_hyp');o.mkdir(exist_ok=True)
L=lec.Lec(lec.read_aig(p/'gold.aig'),lec.read_map(p/'gold.map'),lec.read_aig(p/'gate.aig'),lec.read_map(p/'gate.map'))
lec.renamed(L,[])
for sd,k,h in json.load(open('codex-eng-hyp-0719.json')):
 side=L.gp if sd in ('gold','both') else L.tp
 if k not in side or (sd=='both' and k not in L.tp):continue
 if h[0]=='eq' and h[2] not in (L.gp if h[1]=='gold' else L.tp):continue
 if h[0]=='cube' and any(x not in (L.gp if h[1]=='gold' else L.tp) for x in h[2]):continue
 L.hyp[(sd,k)]=tuple(h)
L.cons=[tuple(c) for c in json.load(open('codex-eng-cons-0719.json'))]
log=[]
print('loaded_hypotheses',len(L.hyp),'state_constraints',len(L.cons),flush=True)
for rnd in range(len(L.hyp)+1):
 m,kind=L.build(with_compare=True,with_hyp=True)
 st=lec.prove(m,o,1000,log,tag='r'+str(rnd))
 bad=[n for n,v in st.items() if v!='proved' and (n.startswith('hyp:') or n.startswith('cons:'))]
 print('round',rnd,'hyp',len(L.hyp),'bad',len(bad),'counts',dict(collections.Counter(st.values())),flush=True)
 if not bad:break
 lec.drop_failed(L,bad)
else:raise RuntimeError('hypothesis refinement did not converge')
fail={n:v for n,v in st.items() if v!='proved'}
json.dump([[sd,k,list(h)] for (sd,k),h in L.hyp.items()],open(o/'hyp_final.json','w'))
json.dump(L.cons,open(o/'cons.json','w'));json.dump(fail,open(o/'remaining.json','w'),indent=1)
(o/'log.txt').write_text('\n'.join(log));print('FINAL',json.dumps(collections.Counter(st.values())),flush=True)
