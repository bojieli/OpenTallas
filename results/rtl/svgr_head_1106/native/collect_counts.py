from pathlib import Path
import re,json,hashlib
root=Path(__file__).resolve().parent
cases=[]
for name in ['ordinary','stalled','stalled_reset']:
 text=(root/f'{name}.log').read_text()
 ring=re.search(r'HEAD_RING_PASS checks=(\d+) accepted_words=(\d+) resets=(\d+) extra_edges=(\d+)',text)
 assert ring
 checks,words,resets,edges=map(int,ring.groups()); assert edges==0
 mutants=[dict(pc=int(a),mut=int(b),caught=bool(int(c)),accepted_checks=int(d)) for a,b,c,d in re.findall(r'HEAD_MUTANT PC=(\d+) MUT=(\d+) caught=(\d+) accepted_checks=(\d+)',text)]
 assert len(mutants)==12
 if name!='ordinary':assert all(x['caught'] for x in mutants)
 assert sum(x['accepted_checks'] for x in mutants if x['mut']==9)==words
 epochs=text.split('RESET_REPLAY_BEGIN')
 for epoch in epochs:
  assert len(re.findall(r'^R ',epoch,re.M))==81
  assert len(re.findall(r'^G ',epoch,re.M))==29
  assert len(re.findall(r'^D ',epoch,re.M))==1
  assert re.search(r'DONE cycles=12764 results=81 gos=29 runs=1',epoch)
 cases.append(dict(name=name,edge_checks=checks,accepted_words=words,warm_resets=resets,extra_edges=edges,epochs=len(epochs),mutants=mutants,log_sha256=hashlib.sha256(text.encode()).hexdigest()))
summary=json.loads((root/'summary.json').read_text());assert summary['verdict']=='PASS'
assert all(x['ops']==20 and x['ops_pass']==20 and x['go_slots_exact'] and x['verdict']=='PASS' for x in summary['cases'])
out=dict(verdict='PASS',audit='Recomputed directly from retained logs; no simulation rerun',cases=cases,total_edge_checks=sum(x['edge_checks'] for x in cases),total_accepted_words=sum(x['accepted_words'] for x in cases),total_epochs=sum(x['epochs'] for x in cases),extra_edges=0)
(root/'counts.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='cases'},indent=2))
