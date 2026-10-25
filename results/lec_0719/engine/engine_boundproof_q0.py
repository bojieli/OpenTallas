import pathlib,json,collections,sys
import lec_crypto as lec
lec.PROVE_JOBS=8
p=pathlib.Path('eng_bound');o=pathlib.Path('eng_boundproof_q0');o.mkdir(exist_ok=True)
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
# Candidate follows the bounded inactive read and 16-byte row alignment;
# it is proved as part of the full induction set, never trusted.
L.hyp[("gold","ff:u_dut.u_lkp.u_e.q_off[0]")]=("const",0)
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

cp={n:v for n,v in st.items() if not n.startswith(("hyp:","cons:"))}
inv={n:v for n,v in st.items() if n.startswith(("hyp:","cons:"))}
rec={"schema":"opentallas.lec.seeded.v1","source":"c8496ae75 / main394765394378 lookup files; aq declaration-order fix included", "verdict":"EQUIVALENT" if not fail else "NOT EQUIVALENT" if "differs" in cp.values() else "UNPROVEN", "design_compare":dict(collections.Counter(cp.values())),"induction_obligations":dict(collections.Counter(inv.values())),"seeded_hypotheses":len(L.hyp),"remaining":fail}
json.dump(rec,open(o/'proof.json','w'),indent=1);print(json.dumps(rec),flush=True)
