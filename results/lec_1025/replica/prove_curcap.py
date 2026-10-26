import sys,pathlib,json,re,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]/'tools/die_plan'))
import lec
p=pathlib.Path(sys.argv[1]);o=pathlib.Path(sys.argv[2]);o.mkdir(exist_ok=False)
L=lec.Lec(lec.read_aig(p/'gold.aig'),lec.read_map(p/'gold.map'),lec.read_aig(p/'gate.aig'),lec.read_map(p/'gate.map'))
# Explicit production reset/counter replica invariant. All proposed relations are proved on BOTH designs.
lec.renamed(L,[])
L.hyp={(sd,k):tuple(h) for sd,k,h in json.loads((p/'hyp.json').read_text())}
lec.replica_proposals(L,[])
log=[];t=time.time()
for rnd in range(50):
 m,kind=L.build(with_compare=True,with_hyp=True)
 keep=[i for i,n in enumerate(m.onames) if n.startswith('hyp:') or '.u_xq.g_cur[' in n]
 m.outs=[m.outs[i] for i in keep];m.onames=[m.onames[i] for i in keep]
 st=lec.prove(m,o,1000,log,tag='production_curcap_'+str(rnd))
 bad=[n for n,v in st.items() if v!='proved' and n.startswith('hyp:')]
 if not bad:break
 for n in bad:
  _,sd,k=n.split(':',2)
  if sd=='bothg':sd='both'
  L.hyp.pop((sd,k),None)
r=dict(schema='opentallas.lec_curcap_cone.v1',proposals=len(L.hyp),counts={v:list(st.values()).count(v) for v in set(st.values())},seconds=time.time()-t,failures={k:v for k,v in st.items() if v!='proved'})
(o/'result.json').write_text(json.dumps(r,indent=1)+'\n');(o/'lec.log').write_text('\n'.join(log));print(json.dumps(r),flush=True)
