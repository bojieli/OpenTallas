#!/usr/bin/env python3
"""Check current-main source/recipe alignment and immutable qualification identities."""
from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent;repo=p.parents[2];res=repo/'results/rtl/bksel_pipe_select_1131';sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
orig=(p/'source/original.sv').read_bytes();assert (repo/'rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv').read_bytes()==orig
recipes=json.loads((p/'recipes.json').read_text());assert set(recipes)=={'dsdv_bksel_c_pipe_ab_r1','dsdv_bksel_c_pipe_ab_r2'}
cut=json.loads((res/'cut/receipt.json').read_text());assert cut['status']=='PASS' and sum(x['checks'] for x in cut['results'])==524304
for f,h in cut['source_sha256'].items():assert sha(p/f)==h,f
assert all(x['errors']==0 and x['masks']==65536 and x['mutant_errors']>0 for x in cut['results'])
for v in ['r1','r2']:
 r=recipes['dsdv_bksel_c_pipe_ab_'+v];t=orig.decode()
 for patch in r['rtl_patches']:
  assert patch['file']=='rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv'
  for old,new in patch['edits']:assert t.count(old)==1;t=t.replace(old,new)
 assert t.encode()==(p/'source'/('ab_'+v+'.sv')).read_bytes()
 b=res/(v+'_correspondence_lemmas');lem=json.loads((b/'lemma_receipt.json').read_text());assert lem['verdict']=='PASS' and len(lem['results'])==5
 assert all(x['verdict']=='PASS' and x['base64_asserted_reset']['equal'] and all(z=='proved' for z in x['induction'].values()) for x in lem['results'])
 assert (repo/r['lec_hints']).read_bytes()==(b/'proven_hints.json').read_bytes()
 e=res/(v+'_official_eq');d=json.loads((e/'lec.json').read_text());i=json.loads((e/'source_identity.json').read_text());assert d['verdict']=='EQUIVALENT' and d['counts']['proved']==d['counts']['compare_points'] and d['counts']['differs']==d['counts']['undecided']==0
 assert 'official_lec_exit=0 ' in (e/'official_lec.status').read_text();assert sha(e/'lec.json')==i['receipt_sha256'];assert sha(p/'source'/('ab_'+v+'.sv'))==i['inputs_sha256']['rtl/ot_s81ph_sel_pipeline.sv']
 assert d['hints']['given']==d['hints']['applied']==5 and d['hints']['skipped']==d['hints']['dropped']['n']==0
 print(v,'SOURCE_RECIPE_AND_OWN_PROOF_IDENTITIES_PASS',d['counts']['compare_points'])
assert json.loads((res/'r1_correspondence_lemmas/basis_identity.json').read_text())['sha256']['gate.aig'] != json.loads((res/'r2_correspondence_lemmas/basis_identity.json').read_text())['sha256']['gate.aig']
print('CURRENT_MAIN_ALIGNMENT_PASS; defaults/physical views unchanged')
