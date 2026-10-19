#!/usr/bin/env python3
"""Read-only causal verdict; refuses absent baseline or changed unrelated source."""
import argparse,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--mutant',required=True);p.add_argument('--out',required=True);a=p.parse_args()
b=pathlib.Path(a.baseline);u=pathlib.Path(a.mutant);o=pathlib.Path(a.out)
if o.exists():raise SystemExit('preserve existing control verdict')
x=json.loads((u/'mutant.json').read_text());bm=json.loads((b/'source_manifest.json').read_text());um=json.loads((u/'source_manifest.json').read_text())
bh={r['path']:r['sha256'] for r in bm['sources']};uh={r['path']:r['sha256']for r in um['sources']}
changed=[k for k in set(bh)|set(uh)if bh.get(k)!=uh.get(k)]
if changed!=[x['changed_source']]:raise SystemExit('unrelated source drift '+str(changed))
if bh[x['changed_source']]!=x['original_sha256'] or uh[x['changed_source']]!=x['mutated_sha256']:raise SystemExit('mutant source receipt mismatch')
case=x['case'];bl=b/f'case{case}.log';ul=u/f'case{case}.log'
bs=bl.read_text(errors='replace');us=ul.read_text(errors='replace')
baseline_pass='NATIVE_JOIN_PASS FUNCTIONAL_ONLY' in bs and '%Error' not in bs and 'Assertion failed' not in bs
named_fail=re.search(x['required_fail_regex'],us) is not None
mutant_pass='NATIVE_JOIN_PASS FUNCTIONAL_ONLY' in us
extra=True
if x['name']=='latest_pending':extra=re.search(r'CQ_STALL .*pending_phase=[123]',bs)is not None
if x['name']=='rank_masks':extra='REAL_RESULT_RETURN_STALL' in bs
caught=baseline_pass and named_fail and not mutant_pass and extra
verdict={'name':x['name'],'verdict':'CAUGHT'if caught else 'NOT_CAUGHT','baseline_application_pass':baseline_pass,'mutant_named_invariant_failed':named_fail,'mutant_application_pass':mutant_pass,'extra_witness_present':extra,'source_delta':changed,'baseline_log_sha256':hashlib.sha256(bl.read_bytes()).hexdigest(),'mutant_log_sha256':hashlib.sha256(ul.read_bytes()).hexdigest(),'required_regex':x['required_fail_regex'],'scope':'minimum native seam COMPONENT source control, no production/native/physical qualification'}
o.write_text(json.dumps(verdict,indent=2)+'\n');print(verdict['name'],verdict['verdict'])
raise SystemExit(0 if caught else 1)
