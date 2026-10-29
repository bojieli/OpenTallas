import pathlib,sys,json,pickle,collections,hashlib
sys.path.insert(0,'/d');import lec
p=pathlib.Path('/d');out=p/'control';out.mkdir(exist_ok=True);L=pickle.loads((p/'target/model.pkl').read_bytes());log=[]
summary={'actual_inputs':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'input').iterdir() if f.is_file()}}
kd,km,kc=lec.kept_registers(L,p/'input/gold.keep');summary['kept']={'declared':len(kd),'missing':km,'constant':kc,'unobservable_removed':getattr(L,'kept_unobservable',[])}
print('KEPT',len(kd),len(km),len(kc),flush=True)
if km:raise RuntimeError('kept missing')
summary['joint']=dict(collections.Counter(json.loads((p/'target/joint0.json').read_text()).values()));summary['compare']=dict(collections.Counter(json.loads((p/'target/compare.json').read_text()).values()))
rel=json.loads((p/'target/proposed.json').read_text())[0];sd,k,h=rel;hh=list(L.hyp[sd,k]);hh[3]^=1;L.hyp[sd,k]=tuple(hh)
m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,out,1000,log,tag='wrong_representative',single_cap=100);bad=[n for n,v in st.items() if v!='proved'];summary['wrong_representative']={'mutated_relation':[sd,k,hh],'counts':dict(collections.Counter(st.values())),'failing':bad};print('CONTROL',collections.Counter(st.values()),flush=True)
if not bad:raise RuntimeError('wrong mapping escaped')
summary['verdict']='EQUIVALENT';(out/'summary.json').write_text(json.dumps(summary,indent=1));(out/'proof.log').write_text('\n'.join(log))
