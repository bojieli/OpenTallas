from pathlib import Path
import importlib.util,json,hashlib,random
p=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('LEC',p/'lec.py');le=importlib.util.module_from_spec(spec);spec.loader.exec_module(le)
L=le.Lec(le.read_aig(p/'gold.aig'),le.read_map(p/'gold.map'),le.read_aig(p/'gate.aig'),le.read_map(p/'gate.map'))
log=[]
le.normalize_gold_elements(L,le.slang_elements(p/'gold.aliases.json'),log)
le.json_alias_keys(L,log,work=p);le.slang_element_keys(L,log,work=p);le.alias_arrays(L,log,work=p)
packed=le.slang_packed_vectors(p/'gold.aliases.json');le.relayout(L,log,packed=packed);le.renamed(L,log,packed=packed)
le.fsm_proposals(L,log)
L.hyp={(sd,k):tuple(h) for sd,k,h in json.loads((p/'hyp.json').read_text())}
m,kind=L.build(with_compare=True,with_hyp=True);m.write(p/'reconstructed.aig')
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
exact=sha(p/'reconstructed.aig')==sha(p/'miter.aig')
if not exact:
 (p/'receipt.json').write_text(json.dumps({'exact_miter_reconstruction':False,'log':log},indent=2));raise SystemExit('reconstruction differs; no witness claimed')
a=le.read_aig(p/'miter_swept.aig');assert a['I']==m.ni and a['L']==0 and a['O']==len(m.onames)
r=random.Random(17);mask=(1<<256)-1;val=[0]+[r.getrandbits(256) for _ in range(a['I'])]
lit=lambda x:val[x>>1]^(mask if x&1 else 0)
for j in range(a['A']):val.append(lit(a['ands'][2*j])&lit(a['ands'][2*j+1]))
records=[]
for i,o in enumerate(a['outputs']):
 if o==0:continue
 bits=lit(o);assert bits;lane=(bits&-bits).bit_length()-1
 need=set();stack=[o>>1]
 while stack:
  v=stack.pop()
  if not v or v in need:continue
  need.add(v)
  if v>a['I']:
   j=v-a['I']-1;stack.extend([a['ands'][2*j]>>1,a['ands'][2*j+1]>>1])
 inputs={m.inames[v-1]:(val[v]>>lane)&1 for v in sorted(need) if v<=a['I']}
 records.append({'point':m.onames[i],'output_index':i,'lane':lane,'abstract_current_inputs':inputs})
(p/'receipt.json').write_text(json.dumps({'scope':'Exact failed official one-step miter witnesses. Reset-reachable trace not established; no functional equivalence or engine-fix claim.','exact_miter_reconstruction':True,'miter_sha256':sha(p/'miter.aig'),'swept_sha256':sha(p/'miter_swept.aig'),'witnesses':records,'reconstruction_log':log},indent=2)+'\n')
print('EXACT_MITER_WITNESSES',len(records))
