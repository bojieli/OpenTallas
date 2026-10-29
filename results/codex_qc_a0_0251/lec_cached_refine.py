import collections,json,pickle,re,sys
from pathlib import Path
kit=Path(sys.argv[1]);sys.path.insert(0,str(kit));import lec
src=kit/sys.argv[2];out=kit/sys.argv[3];out.mkdir(exist_ok=False);L=pickle.loads((src/'model.pkl').read_bytes());log=[]
m,kind=L.build(with_compare=True,with_hyp=True);st=json.loads((src/'compare.json').read_text());idx={n:i for i,n in enumerate(m.onames)};keys=set()
for n,v in st.items():
 if v!='proved':keys.update(kind[i][1] for i in m.cone_inputs(m.outs[idx[n]]) if kind[i][0]=='gold_only')
proposals=[];unhandled=[]
for k in sorted(keys):
 pat=re.sub(r'(g_off|[qc]_p)\[\d+\]',r'\1[GROUP]',k)
 cs=[c for c in L.matched if re.sub(r'(g_off|[qc]_p)\[\d+\]',r'\1[GROUP]',c)==pat]
 if len(cs)==1:L.hyp['gold',k]=('eq','gold',cs[0],0);proposals.append([k,cs[0]])
 else:unhandled.append(k)
(out/'proposed.json').write_text(json.dumps(proposals,indent=1));(out/'unhandled.json').write_text(json.dumps(unhandled,indent=1));print('PROPOSED',len(proposals),'UNHANDLED',len(unhandled),unhandled[:15],flush=True)
for it in range(16):
 m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,out,1000,log,tag='joint'+str(it),single_cap=200);print('JOINT',it,collections.Counter(st.values()),flush=True)
 (out/('joint'+str(it)+'.json')).write_text(json.dumps(st));bad=[k for k,v in st.items() if v!='proved']
 if not bad:break
 lec.drop_failed(L,bad)
(out/'model.pkl').write_bytes(pickle.dumps(L));(out/'native_profile.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())],indent=1))
m,kind=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='compare',single_cap=200);print('COMPARE',collections.Counter(st.values()),flush=True)
(out/'compare.json').write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log));_,missing,constants=lec.kept_registers(L,kit/'lec_profile/gold.keep');print('KEPT',len(missing),len(constants),flush=True)
raise SystemExit(0 if all(v=='proved' for v in st.values()) and not missing and not constants else 1)
