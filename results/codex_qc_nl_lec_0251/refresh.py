import pathlib,sys,json,pickle,collections
sys.path.insert(0,'/d');import lec
out=pathlib.Path('/d/refresh');out.mkdir(exist_ok=True)
L=pickle.loads(pathlib.Path('/d/old_model.pkl').read_bytes());log=[];removed=[]
for it in range(32):
 m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,out,1000,log,tag=f'joint{it}',single_cap=100)
 bad=[k for k,v in st.items() if v!='proved'];print('joint',it,collections.Counter(st.values()),flush=True)
 (out/f'joint{it}.json').write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log))
 if not bad:break
 removed+=bad;lec.drop_failed(L,bad)
else:raise RuntimeError('joint not converged')
(out/'removed.json').write_text(json.dumps(removed,indent=1));(out/'model.pkl').write_bytes(pickle.dumps(L))
m,k=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='compare',single_cap=200)
(out/'compare.json').write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log));print('COMPARE',collections.Counter(st.values()),flush=True)
(out/'hyp.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in L.hyp.items()]));print('done',flush=True)
