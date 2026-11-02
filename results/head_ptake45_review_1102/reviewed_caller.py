"""Bounded HEAD p_take correspondence and 45 raw residual comparisons.
No output masking, reset override, accepted hints or full sender proof.
"""
from pathlib import Path
import hashlib, copy, json
w=Path('/out')
parent=(w/'residual469_parent.py').read_text()
assert hashlib.sha256(parent.encode()).hexdigest()=='4cae3cf30756a3f857bae2b6e5f102c43f8898477770025f470502ffa32d2ee9'
exec(compile(parent.split("residuals = old['failing'] + old['unproven_points']")[0], 'exact_469_context', 'exec'), globals())
p=w/'P_TAKE18_SOURCE.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='5b07b1f3edb1afd6816f3690f8a31b1fe605cfc6bf39b5a9397236fbf981cdb0'
source=json.loads(p.read_text())
la_path=w/'LA_REPLICA_RESULT.json'
assert hashlib.sha256(la_path.read_bytes()).hexdigest()=='0e78156ba3b28c7c66ca387e41f2fb9e76b5af1817679c4e00054f03239ab55c'
la=json.loads(la_path.read_text())
assert la['new_relations_all_proved'] and la['all_auxiliary_proved'] and la['prior_preserved']
assert la['matched_residual_counts']=={'proved':238,'differs':18}
original_augmented=copy.deepcopy(L.hyp); original_cons=copy.deepcopy(L.cons)
assert len(prior)==12732 and len(L.matched)==58437 and old['reset_contract']['used']==64
proposal=[]
for lane in ['a','b']:
 root=f'ff:u_dut.u_core.u_l{lane}.u_ln.u.u_ep.'
 proposal.append(['both',root+'ok_f',['eq','gold',root+'g_fcopy.u_k_ok_f3.q',0]])
assert all((sd,k) not in original_augmented for sd,k,h in proposal)
la_proposal=[['both','ff:u_dut.u_core.u_la.u_ln.u.u_ep.'+f'rep_ra[{i}]',['eq','gold','ff:u_dut.u_core.u_la.u_ln.u.u_ep.u_k_rep_o.q',0]] for i in range(2)]
assert all((sd,k) not in original_augmented for sd,k,h in la_proposal)
for row,lane in zip(proposal,source['lanes']):
 c=lane['source_correspondence_to_qualify']
 assert row==[c['left_side'],c['left'],['eq',c['right_side'],c['right'],c['xor']]] and c['existing_target_tuple'] is None
points18=[k for k,v in la['statuses'].items() if v=='differs']
assert len(points18)==18 and set(points18)==set(source['source_expected18_points'])
points27=[r['point'] for r in old['failing'] if r.get('cone_unmatched')==['gold_x']]
assert len(points27)==27 and len(set(points27))==27
points=points18+points27
assert len(set(points))==45
out=dict(status='IN_PROGRESS_UNTRUSTED_P_TAKE45',prior_count=12732,matched=58437,reset_cycles=64,original_verdict_unchanged=True,source_credit=False,accepted_hints=False,output_mask_added=False,new_reset_relations=False,controls=[])
def save(): (w/'P_TAKE45_RESULT.json').write_text(json.dumps(out,indent=1)+'\n')
def base_both(row):
    sd,k,h=row
    assert sd=='both' and h[0]=='eq' and h[1]=='gold'
    vals=[]
    for side in ['gold','gate']:
        a,_=rv(side,k);b,_=rv(side,h[2])
        vals.append(dict(side=side,key=k,partner=h[2],a=a,b=b,xor=h[3],
                         covered=a is not None and b is not None and a==(b^h[3])))
    return vals

# Measure native BASE on all four new side-pairs before any new predicate enters L.hyp.
out['native_BASE64']=[v for row in proposal for v in base_both(row)]
out['LA_native_BASE64_rechecked']=[v for row in la_proposal for v in base_both(row)]
assert len(out['native_BASE64'])==4 and all(x['covered'] for x in out['native_BASE64'])
assert all(x['covered'] for x in out['LA_native_BASE64_rechecked'])
for row in proposal:
 wrong=copy.deepcopy(row);wrong[2][3]=1
 checks=base_both(wrong)
 assert all(x['a'] is not None and x['b'] is not None and not x['covered'] for x in checks)
 out['controls'].append(dict(kind='wrong_polarity_BASE64',key=row[1],rejected=True,checks=checks))
# Wrong same-reset ok_d partner has a genuinely different NEXT function.
for row in proposal:
 wrong=copy.deepcopy(row);wrong[2][2]=row[1].rsplit('.',1)[0]+'.u_k_ok_o.q'
 checks=base_both(wrong)
 L.hyp=copy.deepcopy(original_augmented);L.cons=copy.deepcopy(original_cons)
 L.hyp[(wrong[0],wrong[1])]=tuple(wrong[2]); snapshot=copy.deepcopy(L.hyp)
 nm,_=L.build(with_compare=False,with_hyp=True)
 assert L.hyp==snapshot and L.cons==original_cons and all(L.hyp.get(k)==h for k,h in prior.items())
 names={'hyp:both:'+wrong[1],'hyp:bothg:'+wrong[1]}
 selected=[(n,o) for n,o in zip(nm.onames,nm.outs) if n in names]
 assert {n for n,_ in selected}==names
 nm.onames=[n for n,_ in selected];nm.outs=[o for _,o in selected]
 passed,stats=prove_exact(nm,'wrong_ok_d_'+('LA' if '.u_la.' in row[1] else 'LB'))
 out['controls'].append(dict(kind='wrong_function_NEXT',key=row[1],base=checks,statuses=stats,rejected=any(s=='differs' for s in stats.values()),unknown=any(s not in ('proved','differs') for s in stats.values())))
 save()
 if passed: out['status']='REFUSED_NONDISCRIMINATING_WRONG_FUNCTION';save();raise SystemExit(2)
# Reprove all prior auxiliary predicates and LA replica relations jointly with new p_take.
L.hyp=copy.deepcopy(original_augmented);L.cons=copy.deepcopy(original_cons)
for sd,k,h in la_proposal+proposal: L.hyp[(sd,k)]=tuple(h)
positive=copy.deepcopy(L.hyp)
I.validate_native_bijection(L,fields,L.hyp)
I.validate_native_bijection(L,fields,L.hyp,initial_image=dict(native_constants=constants,correlations=image_relations))
pm,_=L.build(with_compare=True,with_hyp=True)
assert L.hyp==positive and L.cons==original_cons and all(L.hyp.get(k)==h for k,h in original_augmented.items())
names=set(points)|{'hyp:'+sd+':'+k for sd,k in huntkeys}|{'cons:'+sd+':'+ks[0] for sd,ks,_ in L.cons}
names|={f'hyp:{side}:{k}' for sd,k,h in la_proposal+proposal for side in ['both','bothg']}
selected=[(n,o) for n,o in zip(pm.onames,pm.outs) if n in names]
assert {n for n,_ in selected}==names
pm.onames=[n for n,_ in selected];pm.outs=[o for _,o in selected]
for sd,k,h in keep:
 pm.onames.append('keep_next:'+sd+':'+k);pm.outs.append(pm.XOR(L.dlit[sd,k],L.dlit[h[1],h[2]]^h[3]))
for f in fields:
 pm.onames.append('typed_next:'+f['gold']);pm.outs.append(pm.XOR(L.dlit['gate',f['gate']],L.dlit['gold',f['gold']]^f['proposed_xor']))
assert len(pm.onames)==135 and len(set(pm.onames))==135
passed,stats=prove_exact(pm,'P_TAKE_two_lanes_and_45_raw_residuals')
aux={k:v for k,v in stats.items() if k not in points}
assert len(aux)==90
out.update(status='P_TAKE45_BOUNDED_DIAGNOSTIC_COMPLETE',statuses=stats,points18=points18,points27=points27,raw_residual_counts={s:sum(stats[k]==s for k in points) for s in set(stats.values())},auxiliary_statuses=aux,all_auxiliary_proved=all(s=='proved' for s in aux.values()),all_raw_targets_proved=all(stats[k]=='proved' for k in points),prior_preserved=all(L.hyp.get(k)==h for k,h in prior.items()),full_proof=False)
save();print(out['status'],out['raw_residual_counts'],flush=True)
