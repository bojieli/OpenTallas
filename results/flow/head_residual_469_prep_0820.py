"""Bounded follow-up on the exact original 469 HEAD residuals, never full EQ.

Reuses the actual immutable typed70 reset-image certificate only on the same
byte-pinned source/caller/readset. Rechecks current KEEP/hunt BASE and all 82
auxiliary next-state obligations jointly with the original 469 comparisons.
"""
from pathlib import Path
import hashlib
import json
import copy
import gc

w = Path('/out')
assert hashlib.sha256((w/'SOURCE_JOIN.json').read_bytes()).hexdigest() == '808db7759772766610f16ceae483d1cd8b6fd414f1501ea784789c4bf27af23f'
receipt = json.loads((w/'SOURCE_JOIN.json').read_text())
assert receipt['scope'] == 'EXACT_IMMUTABLE_TYPED70_SUBJECT_RESIDUAL_FOLLOWUP'
for rel, expected in receipt['files_sha256'].items():
    assert hashlib.sha256((w/rel).read_bytes()).hexdigest() == expected, rel
certificate = json.loads((w/'TYPED70_CERTIFICATE.json').read_text())
assert hashlib.sha256((w/'TYPED70_CERTIFICATE.json').read_bytes()).hexdigest() == 'b3d3939a2e3207765e35fec61621d3e016bacc4358f7636c8b6c0014660cf00e'
assert certificate['status'] == 'TYPED70_BOUNDED_DIAGNOSTIC_PASS'
assert certificate['prior_count'] == 12732 and certificate['matched_original'] == 58437
assert certificate['reset_contract']['used'] == 64
assert len(certificate['images']) == 4 and all(x['passed'] for x in certificate['images'])
assert len(certificate['controls']) == 4 and all(x['rejected'] for x in certificate['controls'])
assert len(certificate['joint_statuses']) == 98 and set(certificate['joint_statuses'].values()) == {'proved'}
caller = (w/'head_typed70_native.py').read_text()
assert hashlib.sha256(caller.encode()).hexdigest() == '4eb5de7a9bae505741c04c96fde10c811e28772f1dca515ff9bb7370ad359131'
# Same exact R4 layout/12732 prior reconstruction and typed70 caller guards.
# No reset image or negative-control solver repeats are needed for these same
# immutable graphs; those are evidence, not new transition constraints.
exec(compile(caller.split("for sd in ['gold','gate']:\n d,R=native_reset(sd);slots,cs=model(fields,sd)")[0], 'typed70_initialization', 'exec'), globals())
assert len(prior) == 12732 and len(L.matched) == 58437
result['images'] = certificate['images']
start = caller.index('# Initial-only facts never enter transition assumptions.')
end = caller.index('# Malformed-state controls refuse;')
exec(compile(caller[start:end], 'typed70_current_reset_prior_compatibility', 'exec'), globals())
start = caller.index('# Joint next-state proof retains original prior')
end = caller.index('points=[x[\'point\']')
exec(compile(caller[start:end], 'typed70_current_base_and_joint_context', 'exec'), globals())
# Bind the reused reset-image certificate to the very same compiled full-AIG
# graph/context, not merely a mutable list of file labels. AIG.write retains
# every AND node: this checks the actual original graph and all assumptions,
# including nodes outside the selected 98 outputs. No solver is repeated.
base_names, base_outs = list(m.onames), list(m.outs)
old16 = [x['point'] for x in old['unproven_points'] if any('.u_s.ld#t[' in k for k in x.get('cone_unmatched_keys', []))]
assert len(old16) == 16
old_names = set(old16) | {'hyp:'+sd+':'+key for sd,key in huntkeys} | {'cons:'+sd+':'+keys[0] for sd,keys,_ in L.cons}
old_selected = [(n,o) for n,o in zip(base_names,base_outs) if n in old_names]
m.onames = [n for n,_ in old_selected]
m.outs = [o for _,o in old_selected]
for sd,k,h in keep:
    m.onames.append('keep_next:'+sd+':'+k)
    m.outs.append(m.XOR(L.dlit[sd,k], L.dlit[h[1],h[2]] ^ h[3]))
for f in fields:
    m.onames.append('typed_next:'+f['gold'])
    m.outs.append(m.XOR(L.dlit['gate',f['gate']], L.dlit['gold',f['gold']] ^ f['proposed_xor']))
assert len(m.onames) == 98
m.write(w/'reconstructed_typed70_joint98.aig')
assert hashlib.sha256((w/'reconstructed_typed70_joint98.aig').read_bytes()).hexdigest() == '7071c26da3036a1e4636bb14fd9b4f80dc3644df73d7813cec094ab5e14e8f31', 'immutable typed70 native proof graph/context differs'
m.onames, m.outs = base_names, base_outs
residuals = old['failing'] + old['unproven_points']
points = [row['point'] for row in residuals]
assert len(points) == 469 and len(set(points)) == 469
names = set(points) | {'hyp:'+sd+':'+key for sd,key in huntkeys} | {'cons:'+sd+':'+keys[0] for sd,keys,_ in L.cons}
selected = [(n,o) for n,o in zip(m.onames,m.outs) if n in names]
assert {n for n,_ in selected} == names
m.onames = [n for n,_ in selected]
m.outs = [o for _,o in selected]
for sd,k,h in keep:
    m.onames.append('keep_next:'+sd+':'+k)
    m.outs.append(m.XOR(L.dlit[sd,k], L.dlit[h[1],h[2]] ^ h[3]))
for f in fields:
    m.onames.append('typed_next:'+f['gold'])
    m.outs.append(m.XOR(L.dlit['gate',f['gate']], L.dlit['gold',f['gold']] ^ f['proposed_xor']))
assert len(m.onames) == 551 and len(set(m.onames)) == 551
passed, stats = prove_exact(m, 'original_469_plus_82_proved_relations')
assert all(k in L.hyp and L.hyp[k] == h for k,h in prior.items())
classification = []
for row in residuals:
    keys = row.get('cone_unmatched_keys', [])
    classification.append(dict(point=row['point'], native_status=stats[row['point']],
                               original_bucket='failing' if row in old['failing'] else 'unproven',
                               unmatched=keys, support_count=row.get('cone_support_count'),
                               matched_only=not keys))
aux = {k:v for k,v in stats.items() if k not in set(points)}
assert len(aux) == 82
output = dict(status='BOUNDED_469_RESIDUAL_CLASSIFICATION_COMPLETE', original_verdict_unchanged=True,
              original_counts=old['counts'], prior_count=12732, matched=58437, reset_cycles=64,
              typed70_certificate_reused=True, reset_only_facts_added_to_transition=False,
              typed70_native_full_aig_byte_identical=True,
              auxiliary_statuses=aux, residuals=classification,
              residual_counts={s:sum(row['native_status'] == s for row in classification) for s in set(stats.values())},
              auxiliary_all_proved=all(x == 'proved' for x in aux.values()),
              full_proof=False, accepted_hints=False, output_mask_added=False, source_credit=False)
(w/'RESIDUAL_RESULT.json').write_text(json.dumps(output, indent=1)+'\n')
print(output['status'], output['residual_counts'], flush=True)
