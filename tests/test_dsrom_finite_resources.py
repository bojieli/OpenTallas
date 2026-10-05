"""Shared fabric/bank costs, peer readiness and anti-optimism mutation tests."""
from fractions import Fraction
import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_finite_resources as R

def resource(scope='global',domain='streaming',ii=4):
    return {'scope':scope,'domain':domain,'ownership':'synthetic-owned-port','issue_interval_cycles':ii,
            'minimum_issue_cycles':ii,'source_receipts':['synthetic-test-only']}

def spec(provider='engine',unit=1,complete=12,prev=None,deps=(),claims=None):
    return {'binding':{'provider':provider,'resource_coverage_receipts':['synthetic-test-only'],
        'resource_claims':claims or [],'calendar':{'accept_cycles':1,'complete_cycles':complete,
            'issue_interval_cycles':1,'completion_dependencies':list(deps),'acceptance_dependencies':[]}},
        'period':Fraction(5,6),'previous':prev,'dependencies':list(deps),'unit':unit,'collective_input_bits':64 if unit==6 else 0}

def claim(order,bits=0,release='issue'):
    return {'resource':'port','order':order,'demand_bits':bits,'release':release}

def test_global_bank_conflict_not_per_rank_free_issue():
    s={'a.R0':spec(claims=[claim(0)]),'a.R1':spec(claims=[claim(1)])}
    out,receipts=R.price(s,{'port':resource()}, {})
    assert out['a.R1'][0]-out['a.R0'][0]==Fraction(10,3)
    assert len(receipts)==2
    out,_=R.price(s,{'port':resource(scope='rank')},{})
    assert out['a.R0'][0]==out['a.R1'][0]==0

def test_complete_release_and_independent_resource_domain():
    s={'a.R0':spec(claims=[claim(0,release='complete')]),'a.R1':spec(claims=[claim(1,release='complete')])}
    out,_=R.price(s,{'port':resource(domain='serial')},{})
    assert out['a.R1'][0]==10  # producer completes after12 streaming cycles, not4 serial II cycles
    s['a.R0']['binding']['resource_claims'][0]['release']='issue'
    out,_=R.price(s,{'port':resource(domain='serial')},{})
    assert out['a.R1'][0]==Fraction(40,9)

def collective_fixture():
    s={};gang={}
    for rank in range(4):
        p=f'p.R{rank}';c=f'c.R{rank}';d=f'd.R{rank}'
        s[p]=spec(provider='producer',complete=rank+1,claims=[{'resource':'local','order':0,'demand_bits':0,'release':'issue'}])
        s[c]=spec(provider='fabric',unit=6,complete=8,prev=p,deps=[p],claims=[claim(0,64)])
        s[d]=spec(provider='fabric',unit=6,complete=8,prev=c,claims=[claim(1,64)])
    gang={'C':[f'c.R{r}' for r in range(4)],'D':[f'd.R{r}' for r in range(4)]}
    resources={'port':dict(resource(ii=1),kind='collective_ingress',capacity_bits_per_cycle=64),
               'local':resource(scope='rank',ii=1)}
    return s,resources,gang

def test_simultaneous_peer_collectives_atomic_readiness_and_bandwidth():
    s,r,g=collective_fixture();out,receipts=R.price(s,r,g)
    assert {out[f'c.R{rank}'][0] for rank in range(4)}=={Fraction(10,3)}
    assert {out[f'd.R{rank}'][0] for rank in range(4)}=={Fraction(20,3)}
    ports=[x for x in receipts if x['resource']=='port']
    assert [x['total_demand_bits'] for x in ports]==[256,256]
    assert [x['reservation_hold_ns'] for x in ports]==[float(Fraction(10,3))]*2

def test_accept_dependency_does_not_wait_for_full_completion():
    s={'a.R0':spec(complete=12,claims=[claim(0)]),'b.R1':spec(claims=[{'resource':'other','order':0,'demand_bits':0,'release':'issue'}])}
    s['b.R1']['binding']['calendar']['acceptance_dependencies']=['a.R0']
    out,_=R.price(s,{'port':resource(ii=1),'other':resource(ii=1)},{})
    assert out['b.R1'][0]==Fraction(5,6)
    s['b.R1']['dependencies']=['a.R0']
    out,_=R.price(s,{'port':resource(ii=1),'other':resource(ii=1)},{})
    assert out['b.R1'][0]==10

@pytest.mark.parametrize('mutation',['no_shared_ingress','underprice_bits','underprice_completion','peer_cycle','missing_peer','II_floor','alias_order','missing_coverage'])
def test_shared_lower_cost_optimism_refused(mutation):
    s,r,g=collective_fixture()
    if mutation=='no_shared_ingress':r['port']['kind']='generic'
    elif mutation=='underprice_bits':s['c.R0']['binding']['resource_claims'][0]['demand_bits']=0
    elif mutation=='underprice_completion':s['c.R0']['binding']['calendar']['complete_cycles']=3
    elif mutation=='peer_cycle':s['c.R0']['binding']['calendar']['acceptance_dependencies']=['c.R1']
    elif mutation=='missing_peer':g['C'].pop()
    elif mutation=='II_floor':r['port']['minimum_issue_cycles']=2
    elif mutation=='alias_order':s['d.R0']['binding']['resource_claims'][0]['order']=0
    else:s['p.R0']['binding']['resource_coverage_receipts']=[]
    with pytest.raises(ValueError):R.price(s,r,g)

def test_actual_s58_assignment_not_an_automatic_repartition_sweep():
    import dsrom_full_product_binding as B
    a={'candidate_id':B.CANDIDATE,'TP':4,
       'ordered_grains':[{'id':str(i),'area_um2_by_rank':[1]*4,'tensor_assignment_receipts':['synthetic-only']} for i in range(58)],
       'owner_groups':[{'role':'layer','owners':[str(i)],'source_receipts':['synthetic-only']} for i in range(58)]}
    assert len(B.allocator_groups(a,2))==58
    a['owner_groups'].pop()
    with pytest.raises(ValueError,match='actual58'):B.allocator_groups(a,2)
