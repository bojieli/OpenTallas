from pathlib import Path
import subprocess,json,re,hashlib
ROOT=Path(__file__).resolve().parents[3];B=Path(__file__).parent

def run(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def views(refs):
 out={}
 for ref in refs:
  commit=run('rev-parse',ref+'^{commit}').decode().strip()
  for p in run('ls-tree','-r','--name-only',commit,'physical/ref_tile/').decode().splitlines():
   m=re.match(r'(physical/ref_tile/[^/]+/views/([^/]+))/\2\.lef$',p)
   if m and m[2] not in out:out[m[2]]=dict(commit=commit,directory=m[1])
 return out
used=json.loads((B/'inputs/mu6_main_bind.json').read_text())['masters'];results=[]
for scenario,refs in [('frozen_waiter_source_then_oldmain',['1b7b9d5d772008559e1b2467bc12de0fc067e2bd','c0768b96a8f6c54fa061c73e8cd1e0e982bc9e05']),('hypothetical_currentmain_first_NO_ADMISSION',['6586b0856','1b7b9d5d772008559e1b2467bc12de0fc067e2bd','c0768b96a8f6c54fa061c73e8cd1e0e982bc9e05'])]:
 selected=views(refs);rows=[]
 for master,info in used.items():
  if master.endswith('_ASAP7_75t_R'):continue
  row=dict(master=master,instances=info['instances'],bound_parameter_sets=info['param_sets'],admission='UNQUALIFIED_NO_ROOT_TYPED_EVIDENCE')
  if master not in selected:row['representation']='STANDIN'
  else:
   sel=selected[master];row.update(representation='LEF_DISCOVERY_ONLY',selection=sel,artifacts={})
   for suffix in ['.lef','_tt.lib','_ff.lib','_ss.lib','/abstract.json']:
    p=sel['directory']+('/abstract.json' if suffix=='/abstract.json' else '/'+master+suffix)
    proc=subprocess.run(['git','-C',str(ROOT),'show',sel['commit']+':'+p],capture_output=True)
    row['artifacts'][p]=dict(exists=proc.returncode==0,sha256=hashlib.sha256(proc.stdout).hexdigest() if proc.returncode==0 else None)
   if master=='dsdv_gunit_l5':row['explicit_known_hold']='Original ro3 nativePG4558 +621nonclock failures; canonical reimport is not eligibility'
   if 'capt' in master or 'capc' in master:row['explicit_known_hold']='CAP actual selected source/clock/age contract must be independently reviewed; CLOSED alone insufficient'
   if 'bksel' in master or 'bk_sel' in master or 'topk' in master:row['explicit_known_hold']='TOPK actual selected source/manualgrid/phase/SCC/boot/native eligibility still owed'
  rows.append(row)
 results.append(dict(scenario=scenario,refs=refs,scope='discovery reproduction only; CTRL record not yet selected and landing table overrides not applied; no actual GEN/admission',masters=rows))
(B/'discovery_NO_ADMISSION.json').write_text(json.dumps(results,indent=2)+'\n')
for s in results:
 print(s['scenario'],[(r['master'],r.get('selection',{}).get('directory'),r['representation']) for r in s['masters'] if 'gunit' in r['master'] or 'capt' in r['master'] or 'bksel' in r['master']])
