#!/usr/bin/env python3
"""Independently check DS operand-home identity and bounded-template coverage."""
import gzip,json,pathlib,subprocess,hashlib
commit='fd7220c1e55397dec90222e1f99a8bd95ae02e03'
inputs={}
def get(path):
    b=subprocess.check_output(['git','show',commit+':'+path]);inputs[path]=hashlib.sha256(b).hexdigest();return json.loads(gzip.decompress(b))
d=get('results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz')
r=get(d['residence_archive']);f=get('results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz')
refs=0;templates=set()
for op,forward in zip(d['instructions'],f['PC_dispatch']):
    assert op['pc']==forward['pc']
    for side in ('reads','writes'):
        for v in op[side]:
            for i in v['home_indices']:
                assert r['homes'][i]['version']==v['version'];refs+=1
    for rank in op['rank_bindings']:
        tids=([rank['template']] if 'template' in rank else [])+[x['template'] for x in rank.get('buffer_programs',[])]
        assert rank.get('empty_owned_extent') or tids
        for tid in tids:assert tid in d['templates'];templates.add(tid)
assert len(f['PC_dispatch'])==len(d['instructions'])==2213
out={'status':'PASS_INDEPENDENT_HOME_IDENTITY_CHECK','native_commit':commit,'input_sha256':inputs,'home_references_verified':refs,'distinct_referenced_templates':len(templates),'PCs_verified':len(d['instructions']),'no_RTL_or_job_execution':True}
pathlib.Path(__file__).with_name('binding_verification.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,sort_keys=True))
