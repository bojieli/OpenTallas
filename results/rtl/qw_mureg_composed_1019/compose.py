#!/usr/bin/env python3
"""Compose already committed receipts; runs no compiler or simulation."""
import hashlib,json,re,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
W=D.parents[2]
def git(*a):return subprocess.check_output(['git','-C',str(W),*a])
def get(c,p):return git('show',f'{c}:{p}')
def js(c,p):return json.loads(get(c,p))
def sha(b):return hashlib.sha256(b).hexdigest()
def store(c,p,d):
 b=get(c,p);o=D/d;o.parent.mkdir(parents=True,exist_ok=True);o.write_bytes(b)
 return {'commit':git('rev-parse',c).decode().strip(),'path':p,'receipt':d,'sha256':sha(b)}
B='results/rtl/mu_qwen_1018/merge_reg_0e6795834'
M=js('2a11b195b',B+'/manifest.json')
store('2a11b195b',B+'/manifest.json','original_manifest.json')
store('2a11b195b',B+'/launch.sh','original_launch.sh')
S=git('rev-parse','0e6795834').decode().strip()
rows=[]
for old in M['rows']:
 r=dict(old);n=r['leg'];r['source_commit']=S;r['source_tree']=git('rev-parse',S+'^{tree}').decode().strip()
 r['source_hash_scope']='Archived source commit; per-file fleet hash census not supplied for this leg'
 r['fixture']='Original frozen recipe; see original_launch.sh'
 r['receipts']=[]
 if n.startswith('sl_FACES_mut'):
  m=re.search(r'mut(\d+)',n)[1];p=f'results/rtl/mu_qwen_1018/faces_terminal_1019/FACES_mut{m}_nu4.out'
  q=store('cd660e13e',p,f'evidence/{n}.out');r['receipts'].append(q)
  text=(D/q['receipt']).read_text();assert f'FACES MUT={m}: FAIL 1' in text and '# exit 0' in text and S in text
  r.update(status='AS EXPECTED',actual=f'FACES MUT={m}: FAIL 1 at 162 ns; behavioral rc 1; outer rc 0',fixture='Original MU_NU=4 r3; prior SIGTERM143 rejected')
 else:
  for p in old['evidence']:
   r['receipts'].append(store('2a11b195b',B+'/'+p,'original/'+p))
 if n.startswith('coll_'):
  r['fixture']='Frozen dv2f14bi (non-release); source-bound failure retained'
  r['status']='STALE FIXTURE FAILURE' if n=='coll_mu_bi' else 'INVALID CAUSAL CONTROL'
  if n!='coll_mu_bi':r['actual']+='; same baseline all-die fault makes this an invalid causal witness'
 rows.append(r)
# Preserve independent actual-source verification for FACES and old collective.
for c,p,d in [
 ('2a11b195b',B+'/amix_FACES1_terminal/source_cache_profile.json','faces_source_cache_profile.json'),
 ('2a11b195b',B+'/coll_mu_bi_failure/comparison.json','old_collective_source_comparison.json'),
 ('e6b9c55f2','results/rtl/mu_qwen_current_1019/source_manifest.json','current_source_manifest.json')]:store(c,p,d)
replacements=[]
for case in ['mu_bi','mu_bi_mut_rank','mu_bi_mut_rlat','mu_bi_neg_overlap','mu_bi_dv2f14bi_diagnostic']:
 c='e6b9c55f2' if case=='mu_bi' else '5f5080c86'
 p='results/rtl/mu_qwen_current_1019/'+('out/record.json' if case=='mu_bi' else 'qw_mureg_negatives/out_'+case+'/record.json')
 receipt=store(c,p,'current/'+case+'.json');a=js(c,p)
 replacements.append({'case':case,'evidence':receipt,'source_sha256':a['source_sha256'],'helper_sha256':a.get('helper_sha256',{}),'executable_sha256':a.get('executable_sha256'),'cases':[{'name':x['name'],'passed':x.get('passed'),'result':x['result']} for x in a['cases']]})
store('5f5080c86','results/rtl/mu_qwen_current_1019/qw_mureg_negatives/README.md','current_classification.md')
assert len(rows)==44 and len({r['leg'] for r in rows})==44
counts={x:sum(r['status']==x for r in rows) for x in sorted({r['status'] for r in rows})}
assert counts=={'AS EXPECTED':40,'INVALID CAUSAL CONTROL':3,'STALE FIXTURE FAILURE':1}
# All replacement records retain full actual RTL/helper/executable hashes.
for r in replacements:
 assert r['source_sha256']
 assert all(x['passed'] for x in r['cases']) if r['case']=='mu_bi' else all(not x['passed'] for x in r['cases'])
manifest={'schema':'opentallas.qwen.mureg.classified.v1','original_source_commit':S,'original_counts':counts,'original_same_source_regression_pass':False,'collection_complete':True,'replacement_cohort':'SAFE hard faces + dv2f18dh2; e6b9c55f2 positive, 3ac055daa recipe + 5f5080c86 negative receipts','native_physical_qualified':False,'full_token_qualified':False,'rows':rows,'replacement_records':replacements}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
lines=['# Qwen MU 44-leg terminal classification','',
'All 44 original legs are terminal and classified: **40 valid expected results, one stale-fixture positive failure, three invalid causal negative controls**. The historical frozen `0e6795834` regression remains failed. Collection is complete; this is not a same-source 44/44 PASS.','',
'The separately corrected collective cohort passes its positive and all three causal controls. Positive receipts are `e6b9c55f2`; negative recipe `3ac055daa` and receipts `5f5080c86`. It uses SAFE hard faces and the release dv2f18dh2 lane table. The old dv2f14bi fixture also fails identically on current source, establishing stale-fixture classification. This does not isolate K-only causality.','',
'`manifest.json` carries the full original commit/tree hashes for every leg, SHA256 of every copied receipt, and the actual per-file RTL/helper/executable hashes embedded in the corrected collective records. The original launch stages a git-archive source subset. For historical legs without an independent fleet byte census, the source commit is a recorded launch pin, not a newly verified complete remote-input hash census. FACES includes the existing source/cache verification packet.','',
'FACES MUT11/12 were collected from the original completed r3 builds: actual behavior fails at 162 ns while outer wrappers return 0. SIGTERM143 and cases=0 were never used as witnesses. No builds, retries or simulations were launched for this composition.','',
'Excluded: OPSEG full2 steady-state rate; actual MU.TOK.QW integration; physical/native phase and timing qualification. `ctlm_rest` retains its historical lp_m4 observability waiver. Component fixtures do not prove complete single-user or multi-user tokens.','',
'## Original frozen-source legs','',f'Source `{S}`; all rows refer to this exact cohort, with fixture provenance in the last column.','',
'| Leg | Expected | Got | Classification | Fixture / receipt |','|---|---|---|---|---|']
for r in rows:
 actual=r['actual'].replace('|',' / ').replace('\n',' ')
 receipt=r['receipts'][0]['receipt'];lines.append(f"| {r['leg']} | {r['expect']} | {actual} | {r['status']} | {r['fixture']}; [receipt]({receipt}) |")
lines+=['','## Corrected collective cohort','','| Case | Actual result | Provenance |','|---|---|---|']
for r in replacements:
 s='; '.join(x['name']+': '+json.dumps(x['result'],sort_keys=True) for x in r['cases'])
 lines.append(f"| {r['case']} | {s} | [full source hashes and record]({r['evidence']['receipt']}) |")
(D/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(counts));print('44 unique terminal original legs, 5 separate current/diagnostic records; no simulation run')
