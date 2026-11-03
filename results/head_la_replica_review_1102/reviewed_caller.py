"""LA-only missing replica invariants: native BASE64/STEP plus 256 comparisons.

No LB reverse alias, new reset relation, accepted hint, output mask or full EQ.
"""
from pathlib import Path
import hashlib
import copy
import json

w=Path('/out')
parent=(w/'residual469_parent.py').read_text()
assert hashlib.sha256(parent.encode()).hexdigest()== '4cae3cf30756a3f857bae2b6e5f102c43f8898477770025f470502ffa32d2ee9'
exec(compile(parent.split("residuals = old['failing'] + old['unproven_points']")[0], 'exact_469_context', 'exec'), globals())
candidate_path=w/'REPLICA_CANDIDATE.json'
assert hashlib.sha256(candidate_path.read_bytes()).hexdigest()=='190ce73f74694a6780859166c84021419bd98fbce3b826290f0861194ba55fa3'
candidate=json.loads(candidate_path.read_text())
proposal=candidate['new_candidate_mappings']
root='ff:u_dut.u_core.u_la.u_ln.u.u_ep.'
assert proposal==[['both',root+f'rep_ra[{i}]',['eq','gold',root+'u_k_rep_o.q',0]] for i in range(2)]
old_augmented=copy.deepcopy(L.hyp);old_cons=copy.deepcopy(L.cons)
assert all((sd,k) not in old_augmented for sd,k,h in proposal)
assert len(prior)==12732 and len(L.matched)==58437 and old['reset_contract']['used']==64
out=dict(status='IN_PROGRESS_UNTRUSTED_LA_ONLY',original_verdict_unchanged=True,
         original_counts=old['counts'],source_credit=False,accepted_hints=False,
         prior_count=12732,matched=58437,reset_cycles=64,new_reset_relations=False,controls=[])
def save():
    (w/'LA_REPLICA_RESULT.json').write_text(json.dumps(out,indent=1)+'\n')
def base_both(row):
    sd,k,h=row
    assert sd=='both' and h[0]=='eq' and h[1]=='gold'
    vals=[]
    for side in ['gold','gate']:
        a,_=rv(side,k);b,_=rv(side,h[2])
        vals.append(dict(side=side,key=k,partner=h[2],a=a,b=b,xor=h[3],
                         covered=a is not None and b is not None and a==(b^h[3])))
    return vals
out['native_BASE64']=[v for row in proposal for v in base_both(row)]
assert len(out['native_BASE64'])==4 and all(x['covered'] for x in out['native_BASE64'])
wrong=copy.deepcopy(proposal[0]);wrong[2][3]=1
control=base_both(wrong)
assert all(x['a'] is not None and x['b'] is not None and not x['covered'] for x in control)
out['controls'].append(dict(kind='wrong_polarity_BASE64',rejected=True,checks=control));save()
# A one-cycle older unreset partner must never silently become the same-age
# source. Its BASE is measured; current-state equality is only a trial mutant.
wrong=copy.deepcopy(candidate['negative_controls'][1]['proposal'])
assert wrong[1]==root+'rep_ra[0]' and wrong[2][2]==root+'g_arep[0].a_rep_c'
control=base_both(wrong)
L.hyp=copy.deepcopy(old_augmented);L.cons=copy.deepcopy(old_cons)
L.hyp[(wrong[0],wrong[1])]=tuple(wrong[2])
trial=copy.deepcopy(L.hyp)
nm,_=L.build(with_compare=False,with_hyp=True)
assert L.hyp==trial and L.cons==old_cons and all(L.hyp.get(k)==h for k,h in prior.items())
negative_names={'hyp:both:'+wrong[1],'hyp:bothg:'+wrong[1]}
selected=[(n,o) for n,o in zip(nm.onames,nm.outs) if n in negative_names]
assert {n for n,_ in selected}==negative_names
nm.onames=[n for n,_ in selected];nm.outs=[o for _,o in selected]
np,ns=prove_exact(nm,'wrong_older_partner_STEP')
out['controls'].append(dict(kind='wrong_older_partner',base=control,statuses=ns,
                            rejected=any(s=='differs' for s in ns.values()),unknown=any(s not in ('proved','differs') for s in ns.values())))
save()
if np:
    out['status']='REFUSED_NONDISCRIMINATING_OLDER_PARTNER_CONTROL';save();raise SystemExit(2)
# Trial positive predicates add only the two missing LA tuples. Preserve all
# original12732 and independently proven70/hunt tuples literally through build.
L.hyp=copy.deepcopy(old_augmented);L.cons=copy.deepcopy(old_cons)
for sd,k,h in proposal:L.hyp[(sd,k)]=tuple(h)
positive=copy.deepcopy(L.hyp)
I.validate_native_bijection(L,fields,L.hyp)
I.validate_native_bijection(L,fields,L.hyp,initial_image=dict(native_constants=constants,correlations=image_relations))
pm,_=L.build(with_compare=True,with_hyp=True)
assert L.hyp==positive and L.cons==old_cons
assert all(L.hyp.get(k)==h for k,h in old_augmented.items())
matched_points=[row['point'] for row in old['failing'] if not row.get('cone_unmatched_keys')]
assert len(matched_points)==256 and len(set(matched_points))==256
names=set(matched_points)|{'hyp:'+sd+':'+k for sd,k in huntkeys}|{'cons:'+sd+':'+ks[0] for sd,ks,_ in L.cons}
names|={f'hyp:{side}:{k}' for sd,k,h in proposal for side in ['both','bothg']}
selected=[(n,o) for n,o in zip(pm.onames,pm.outs) if n in names]
assert {n for n,_ in selected}==names
pm.onames=[n for n,_ in selected];pm.outs=[o for _,o in selected]
for sd,k,h in keep:
    pm.onames.append('keep_next:'+sd+':'+k)
    pm.outs.append(pm.XOR(L.dlit[sd,k],L.dlit[h[1],h[2]]^h[3]))
for f in fields:
    pm.onames.append('typed_next:'+f['gold'])
    pm.outs.append(pm.XOR(L.dlit['gate',f['gate']],L.dlit['gold',f['gold']]^f['proposed_xor']))
assert len(pm.onames)==342 and len(set(pm.onames))==342
passed,stats=prove_exact(pm,'LA_two_replica_STEP_and_256_matched_residuals')
out.update(status='LA_REPLICA_BOUNDED_DIAGNOSTIC_COMPLETE',statuses=stats,
           matched_residual_counts={s:sum(stats[k]==s for k in matched_points) for s in set(stats.values())},
           auxiliary_statuses={k:v for k,v in stats.items() if k not in matched_points},
           prior_preserved=all(L.hyp.get(k)==h for k,h in prior.items()),full_proof=False)
out['new_relations_all_proved']=all(stats[f'hyp:{side}:{k}']=='proved' for sd,k,h in proposal for side in ['both','bothg'])
out['all_auxiliary_proved']=all(v=='proved' for v in out['auxiliary_statuses'].values())
save();print(out['status'],out['matched_residual_counts'],flush=True)
