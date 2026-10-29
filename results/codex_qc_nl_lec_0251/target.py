import pathlib,sys,json,pickle,collections,re
sys.path.insert(0,'/d');import lec
p=pathlib.Path('/d');out=p/'target';out.mkdir(exist_ok=True);L=pickle.loads((p/'refresh/model.pkl').read_bytes());log=[]
m,kind=L.build(with_compare=True,with_hyp=True);st=json.loads((p/'refresh/compare.json').read_text());idx={n:i for i,n in enumerate(m.onames)};keys=set()
for n,v in st.items():
 if v!='proved':
  keys.update(kind[i][1] for i in m.cone_inputs(m.outs[idx[n]]) if kind[i][0]=='gold_only')
proposed=[]
for k in sorted(keys):
 pat=re.sub(r'(g_off|[qc]_p)\[\d+\]',r'\1[GROUP]',k)
 cs=[c for c in L.matched if re.sub(r'(g_off|[qc]_p)\[\d+\]',r'\1[GROUP]',c)==pat]
 if len(cs)==1:
  L.hyp['gold',k]=('eq','gold',cs[0],0);proposed.append(['gold',k,['eq','gold',cs[0],0]])
print('gold-only support',len(keys),'proposals',len(proposed),flush=True)
(out/'proposed.json').write_text(json.dumps(proposed,indent=1))
for it in range(32):
 m,_=L.build(with_compare=False,with_hyp=True);st=lec.prove(m,out,1000,log,tag=f'joint{it}',single_cap=100)
 bad=[k for k,v in st.items() if v!='proved'];print('joint',it,collections.Counter(st.values()),flush=True)
 (out/f'joint{it}.json').write_text(json.dumps(st))
 if not bad:break
 lec.drop_failed(L,bad)
else:raise RuntimeError('no convergence')
(out/'model.pkl').write_bytes(pickle.dumps(L));m,kind=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='compare',single_cap=100)
(out/'compare.json').write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log));print('COMPARE',collections.Counter(st.values()),flush=True)
