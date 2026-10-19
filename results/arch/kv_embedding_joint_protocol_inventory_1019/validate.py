#!/usr/bin/env python3
"""Bounded source/hash/arithmetic extraction checks; no engine or qualification."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_rows(root,rows,pathkey):
 for r in rows:
  f=root/r[pathkey];assert f.is_file(),str(f);assert sha(f)==r['sha256'],str(f)
 checks.append({'root':str(root.relative_to(P)),'source_hashes':len(rows),'PASS':True})
check_rows(P/'dependencies/seed',json.loads((P/'dependencies/seed/source_manifest.json').read_text())['files'],'path')
r=json.loads((P/'dependencies/controller/source_manifest.json').read_text())['files']
check_rows(P/'dependencies/controller/source/5f2',r,'path')
check_rows(P/'dependencies/installed',json.loads((P/'dependencies/installed/sources.json').read_text()),'copy')
# Qwen compressed matrix source declares uncompressed SHA; only validate raw frozen input rows here.
r=json.loads((P/'dependencies/qwen_contract/sources.json').read_text()); raw=[x for x in r if not x['compression']]
check_rows(P/'dependencies/qwen_contract',raw,'copy')
check_rows(P,json.loads((P/'EXTRA_SOURCES.json').read_text()),'snapshot')
m=json.loads((P/'MODEL_PROPOSAL.json').read_text());c=json.loads((P/'COST_LEDGER.json').read_text())
assert sum(r['bits'] for r in c['rows'])==31752==c['named_boundary_floor']
assert 4*81+124*108==13716
assert m['Nprep'] is None and m['Nexpect'] is None
assert m['production']['native_qualified'] is False
# Header identity fields preserve token/epoch/scale/code bits and occupy exactly27 reserved header bits.
fields=[(74,69),(68,56),(55,50),(49,48)];bits=[b for h,l in fields for b in range(l,h+1)]
assert len(bits)==len(set(bits))==27 and set(bits)==set(range(48,75))
# Native prerequisite was actually completed; no production qualification inferred.
n=json.loads((P/'dependencies/native_join/FINAL_RECEIPT.json').read_text());assert n['enabled_passing_cases']==20 and n['actual_DUT_causal_controls_caught']==16
out={'verdict':'SOURCE_EXTRACTION_CHECKS_PASS_IMPLEMENTATION_HOLD','checks':checks,'source_hash_count':sum(x['source_hashes'] for x in checks),'named_candidate_metadata_floor':31752,'engines_started':0,'production_dates':'NULL','qualification':False}
(P/'VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
