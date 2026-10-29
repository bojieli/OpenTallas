# HBM-CORES-KITS-13 rest_target5: rest_target4 kept set (32 gold hyps: 28 const + 4 gold-gold eq, found by Houdini over
# sequential-trace candidates) re-proved by ONE clean joint induction here, then base cases: the engine reset-state
# fixpoint (noreset_sound) + the engine universal raw-D base (raw_constant_bases: D==c with ALL state/inputs/RTL X
# free) + the engine exact finite-prefix base (raw_prefix_bases: unrolled STEPS edges from entirely free state, fresh
# inputs each edge, no reset/hyp/X mask).  Square facts (m_yy = qmul(yi,yi)): power = 2*a_power is even ->
# s1_power[0]=0 -> shc odd -> s2_sh[0]=1 and m_round odd bits 0 (s2_mr[odd]=0); sign a^a = 0.  No waiver/assumption.
import pathlib,sys,json,collections,os
os.environ.setdefault("OT_LEC_RESET_CYCLES","64")
STEPS=int(os.environ.get("K13_STEPS","4"))
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));import lec_engine as lec
src=pathlib.Path(os.environ["K13_INPUT"]);out=pathlib.Path(os.environ["K13_OUT"]);out.mkdir(exist_ok=True);log=[]
L=lec.Lec(lec.read_aig(src/"gold.aig"),lec.read_map(src/"gold.map"),lec.read_aig(src/"gate.aig"),lec.read_map(src/"gate.map"))
lec.normalize_gold_elements(L,lec.slang_elements(src/"gold.aliases.json"),log)
for f in (lec.json_alias_keys,lec.slang_element_keys,lec.alias_arrays):f(L,log,work=src)
for f in (lec.relayout,lec.renamed,lec.replica_proposals,lec.merged_proposals,lec.register_alias_proposals,lec.fsm_proposals):f(L,log)
L.hyp.clear();dropped=[]
for sd,k,h in json.loads((src/"hyp.json").read_text()):
 valid=(k in L.gp and k in L.tp) if sd=="both" else k in (L.gp if sd=="gold" else L.tp)
 if h[0]=="eq":valid=valid and h[2] in (L.gp if h[1]=="gold" else L.tp)
 if valid:L.hyp[sd,k]=tuple(h)
 else:dropped.append([sd,k,h])
print("normalized stale",len(dropped),"base hyps",len(L.hyp),flush=True)
lec.noreset_classify(L)
cand={(a,b):tuple(h) for a,b,h in json.loads((HERE/"kept4.json").read_text())}
for x,h in cand.items():L.hyp[x]=h
m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,out,1000,log,tag="joint",single_cap=200)
print("joint",collections.Counter(st.values()),flush=True)
assert all(v=="proved" for v in st.values()),"joint induction not clean"
held0=lec.noreset_sound(L);miss0=[x for x in L.hyp if L.hyp[x][0]=="const" and x not in held0]
print("reset-fixpoint base-missing",len(miss0),flush=True)
lec.raw_constant_bases(L,out,1000,log)
held1=lec.noreset_sound(L);miss1=[x for x in L.hyp if L.hyp[x][0]=="const" and x not in held1]
print("after universal raw-D base-missing",len(miss1),flush=True)
cands=[(s,k,L.hyp[(sd,k)][1]) for (sd,k) in miss1 for s in (("gold","gate") if sd=="both" else (sd,))]
lec.raw_prefix_bases(L,cands,STEPS,out,1000,log)
held=lec.noreset_sound(L);miss=[x for x in L.hyp if L.hyp[x][0]=="const" and x not in held]
print("after raw prefix",STEPS,"base-missing",len(miss),miss[:20],flush=True)
mine=[x for x in cand if cand[x][0]=="const"]
print("k13 const hyps base:",{x[1].split("u_rsq.")[-1]:held.get(x) for x in mine},flush=True)
pe=getattr(L,"raw_prefix_edges",{});print("raw prefix proved",len(pe),flush=True)
lost=[x for x in miss]
while True:
 held=lec.noreset_sound(L);bad=[x for x in L.hyp if L.hyp[x][0]=="const" and x not in held]
 if not bad:break
 for x in bad:L.hyp.pop(x,None)
print("dropped (no base)",len(lost),flush=True)
m,_=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag="compare",single_cap=200)
(out/"compare.json").write_text(json.dumps(st));(out/"proof.log").write_text("\n".join(log))
(out/"hyps_final.json").write_text(json.dumps([[a,b,list(h)] for (a,b),h in L.hyp.items()]))
print("compare",collections.Counter(st.values()),flush=True)
print("nonproved",[p for p,v in st.items() if v!="proved"][:40],flush=True)
assert not lost, "hypotheses without proved initial base"
assert all(v=="proved" for v in st.values()), "compare failed"
print("REST_TARGET5_DONE",flush=True)
