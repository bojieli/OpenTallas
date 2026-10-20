#!/usr/bin/env python3
"""Finite source-function regression, not RTL timing or a die generator run."""
import ast,copy,gzip,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
f=json.loads((P/'fixture.json').read_text())
s=gzip.decompress((P/'frozen_generator.py.gz').read_bytes()).decode()
assert hashlib.sha256(s.encode()).hexdigest()==f['generator_sha256']
old="net.get((h0, 'ck'), net.get((h0, 'ck_s'), ln.get('src_ck')))"
new="net.get((h0, 'ck_s'), net.get((h0, 'ck'), ln.get('src_ck')))"
assert s.count(old)==1

def function(src):
    node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='_gen16_fwd_ck_names')
    ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'source_function','exec'),ns)
    return ns[node.name]

def model():
    buses={}
    for name,i in f['instances'].items():
        for pin,net in i['ports'].items():
            if pin in ('ck','ck_s'):
                assert net.startswith('n_'),(name,pin,net)
                buses.setdefault(net[2:],[]).append((name,pin))
    return dict(buses=[(n,'clock_trunk',1,e) for n,e in buses.items()],fwd_lanes=dict(lanes=copy.deepcopy(f['lanes'])))

def expected(row):
    name=(row['stations'] or [row['landing']])[0]
    p=f['instances'][name]['ports']
    # Actual master contract: FIRST landing writes with ck_s; other hop0 uses ck.
    pin='ck_s' if f['instances'][name]['master'].startswith('qfd_landh0_') else 'ck'
    return p[pin][2:],f['instances'][row['landing']]['ports']['ck'][2:]

orig=model();function(s)(orig)
prop=model();function(s.replace(old,new))(prop)
changed=[];original_bad=[];same_root_first=0;owner_mismatches=[]
for actual,proposal in zip(f['lanes'],prop['fwd_lanes']['lanes']):
    a,b=expected(actual)
    assert (proposal['src_ck'],proposal['dst_ck'])==(a,b),actual['bid']
    prior=next(x for x in orig['fwd_lanes']['lanes'] if x['bid']==actual['bid'])
    assert (prior['src_ck'],prior['dst_ck'])==(actual['src_ck'],actual['dst_ck']),('original reproduction',actual['bid'])
    if actual['src_ck']!=a: original_bad.append(actual['bid'])
    if proposal!=actual:
        assert {k for k in proposal if proposal[k]!=actual[k]}=={'src_ck'}
        changed.append(dict(bid=actual['bid'],old=actual['src_ck'],proposed=a,dst=b))
    if actual['n']==1 and actual['lane']!='reset' and a==b: same_root_first+=1
    if actual['lane']=='data':
        sp=f['instances'][actual['src']]['ports'];owner=sp.get('ck',sp.get('clk'))
        if owner is not None and owner[2:]!=a: owner_mismatches.append(actual['bid'])
assert not owner_mismatches,owner_mismatches
assert 'sf_tt_pw' in original_bad and 'dvw_sys_face_seq_dh' not in original_bad
# Minimal independent constructor fixtures exercise different ck/ck_s, multi-hop,
# same-root FIRST, reset single station, and absence of forwarded lanes.
unit=dict(buses=[('SOURCE','clock_trunk',1,[('first','ck_s'),('hop0','ck'),('rst','ck')]),('DEST','clock_trunk',1,[('first','ck'),('land','ck')])],fwd_lanes=dict(lanes=[dict(bid='FIRST',stations=[],landing='first'),dict(bid='MULTI',stations=['hop0'],landing='land'),dict(bid='RESET',stations=[],landing='rst')]))
u=copy.deepcopy(unit);function(s.replace(old,new))(u)
assert [(r['src_ck'],r['dst_ck']) for r in u['fwd_lanes']['lanes']]==[('SOURCE','DEST'),('SOURCE','DEST'),('SOURCE','SOURCE')]
v=copy.deepcopy(unit);function(s)(v)
assert v['fwd_lanes']['lanes'][0]['src_ck']=='DEST' # causal old-source mutant
function(s.replace(old,new))({})
report=dict(scope='FINITE_SOURCE_MODEL_ONLY',lanes=len(f['lanes']),source_and_destination_comparisons=2*len(f['lanes']),original_manifest_reproduced=True,original_source_mismatches=len(original_bad),changes=changed,unchanged_same_root_FIRST=same_root_first,actual_source_owner_clock_mismatches=owner_mismatches,synthetic_cases=4,old_priority_mutant='REJECTED: FIRST source is DEST',native_phase=None,observed_transport_ages=None,first_use=None)
(P/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=2))
# Current-main proposal is separately executable, because current main has no GEN16 helper.
ns={};exec((P/'current_main_helper.PROPOSAL.py').read_text(),ns);finalize=ns['_fwd_clock_manifest_finalize']
cm=model();finalize(cm)
for row in cm['fwd_lanes']['lanes']:
    assert (row['src_ck'],row['dst_ck'])==expected(row)
first=dict(bid='FIRST',stations=[],landing='first',lane='data')
multi=dict(bid='MULTI',stations=['hop0'],landing='land',lane='data')
rst=dict(bid='RESET',stations=[],landing='rst',lane='reset')
cases=dict(buses=unit['buses'],fwd_lanes=dict(lanes=[first,multi,rst]))
finalize(cases)
assert [(r['src_ck'],r['dst_ck']) for r in cases['fwd_lanes']['lanes']]==[('SOURCE','DEST'),('SOURCE','DEST'),('SOURCE','SOURCE')]
equal=dict(buses=[('SAME','clock_trunk',1,[('first','ck_s'),('first','ck')])],fwd_lanes=dict(lanes=[copy.deepcopy(first)]));finalize(equal)
assert equal['fwd_lanes']['lanes'][0]['src_ck']=='SAME'
for label,buses,marker in [
    ('missing_source',[('DEST','clock_trunk',1,[('first','ck')])],'missing clock: first.ck_s'),
    ('missing_destination',[('SOURCE','clock_trunk',1,[('first','ck_s')])],'missing clock: first.ck'),
    ('conflicting_source',[('S1','clock_trunk',1,[('first','ck_s')]),('S2','clock_trunk',1,[('first','ck_s')]),('D','clock_trunk',1,[('first','ck')])],'conflicting clock drivers'),
]:
    try: finalize(dict(buses=buses,fwd_lanes=dict(lanes=[copy.deepcopy(first)])))
    except ValueError as e: assert marker in str(e),(label,str(e))
    else: raise AssertionError(label+' falsely accepted')
finalize(dict(buses=[],fwd_lanes=dict(lanes=[])))
report.update(current_main_proposal_comparisons=308,current_main_constructor_cases=['FIRST_distinct','FIRST_equal','multi_hop0','single_reset','empty_lanes'],causal_refusals=['old_ck_first_mutant','missing_source','missing_destination','conflicting_source'])
(P/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('CURRENT_MAIN_PROPOSAL PASS: 308 clock comparisons; FIRST distinct/equal, multihop, reset, empty; missing source/destination and conflicting driver refused.')
