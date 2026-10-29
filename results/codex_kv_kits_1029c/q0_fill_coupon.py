"""Frozen proof diagnostic: identical original miter first, then untrusted fill-chain hints."""
import sys,json,importlib.util,hashlib
from pathlib import Path
from collections import Counter
kit,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True);d=kit/'lec'
sp=importlib.util.spec_from_file_location('lec',kit/'lec.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
L=m.Lec(m.read_aig(d/'gold.aig'),m.read_map(d/'gold.map'),m.read_aig(d/'gate.aig'),m.read_map(d/'gate.map'));L.kit_reset_ports=m.kit_reset_ports(kit)
import shutil
shutil.copy2(d/'gold.aliases.json',out/'gold.aliases.json')
log=[]
m.normalize_gold_elements(L,m.slang_elements(out/'gold.aliases.json'),log)
m.json_alias_keys(L,log,work=out);m.slang_element_keys(L,log,work=out);m.alias_arrays(L,log,work=out);m.relayout(L,log);m.renamed(L,log)
h=json.load(open(d/'hyp.json'));assert set(x[2][0] for x in h)<={'eq','const'}
L.hyp={(sd,k):tuple(v) for sd,k,v in h};a,k=L.build(with_compare=True,with_hyp=True);a.write(out/'reconstructed.aig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rec={'source_tool':sha(kit/'lec.py'),'original_miter':sha(d/'miter.aig'),'reconstructed_miter':sha(out/'reconstructed.aig')};print('RECONSTRUCT',rec,flush=True)
if rec['original_miter']!=rec['reconstructed_miter']:
 (out/'result.json').write_text(json.dumps(dict(rec,verdict='RECONSTRUCTION_MISMATCH'),indent=1));raise SystemExit(3)
bylit={v:k for k,v in L.gp.items()};hints=[];chains=[]
for key in sorted(L.gp):
 if not key.endswith('.sc_addr[11]'):continue
 chain=[];q=key;seen=set()
 while '.u_tag.' in q or q.endswith('.sc_addr[11]'):
  assert q not in seen;seen.add(q);chain.append(q);nxt=L.gc[q]
  assert nxt in bylit,('non-direct-D',q,nxt)
  q=bylit[nxt]
 assert L.hyp.get(('gold',q),L.hyp.get(('both',q)))==('const',0),(q,L.hyp.get(('gold',q)))
 chain.append(q)
 pred=None
 for node in reversed(chain):
  hints.append(['gold',node,['fill',0,pred]]);pred=node
 chains.append({'capture':key,'direct_D_chain':chain,'proved_constant_root':q})
(out/'chains.json').write_text(json.dumps(chains,indent=1));(out/'hints.json').write_text(json.dumps(hints,indent=1));print('DIRECT_FILL_CHAINS',[(x['capture'],len(x['direct_D_chain'])) for x in chains],flush=True)
log=[];r=m.apply_hints(L,hints,out,1000,log);print('HINT_REPORT',dict(given=r['given'],applied=r['applied'],dropped=len(r['dropped']),kept=r['kept'],fill_kept=len(r['fill'])),flush=True)
a,k=L.build(with_compare=True,with_hyp=True);s=m.prove(a,out,1000,log,tag='miter_fill');rec.update(verdict='PROOF_DIAGNOSTIC',counts=dict(Counter(s.values())),hints=r)
(out/'hyp.json').write_text(json.dumps([[sd,key,list(v)] for (sd,key),v in sorted(L.hyp.items())])+'\n');(out/'result.json').write_text(json.dumps(rec,indent=1)+'\n');(out/'diagnostic.log').write_text('\n'.join(log));print('RESULT_COUNTS',rec['counts'],flush=True)
