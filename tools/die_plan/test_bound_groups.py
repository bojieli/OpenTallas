from copy import deepcopy
from types import SimpleNamespace as N
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bound_groups as G


def vehicle():
    items=[dict(inst='u_'+k+'0',module=k,reset_pin='rst_n') for k in ('exp','head','lrly','rcp','rsq')]
    cells=[N(module=x['module'],ports={'rst_n':[99]},dirs={'rst_n':'input'}) for x in items]
    hc=dict(inst='u_lane0',bound_group=dict(kind='exact_post_bind_group',reset_pin='rst_n',members=items))
    target=dict(pin='rst_n',tap=10)
    tree=dict(relays=[dict(q='rst_n_t3',depth=4),dict(q='rst_n_t10',depth=4)],tap_roles={3:'mission',10:'mission'})
    rel=lambda i:items[i]['inst']
    return cells,list(range(5)),rel,target,hc,tree,3


def test_explicit_group_reset_projects_every_exact_member_and_rejects_mutants():
    v=vehicle();assert G.reset_members(*v)==[(i,'rst_n') for i in range(5)]
    for mutation in ('missing','wrong_module','depth','start_role','duplicate','noninput'):
        a=list(deepcopy(v));a[2]=v[2]
        if mutation=='missing':a[1]=a[1][:-1]
        if mutation=='wrong_module':a[0][0].module='different'
        if mutation=='depth':a[5]['relays'][1]['depth']=5
        if mutation=='start_role':a[5]['tap_roles'][10]='bootstrap'
        if mutation=='duplicate':a[4]['bound_group']['members'][1]=a[4]['bound_group']['members'][0]
        if mutation=='noninput':a[0][0].dirs['rst_n']='output'
        with pytest.raises(G.BoundGroupError):G.reset_members(*a)


def test_cut_preserves_actual_scheduled_reset_and_committed_core_code():
    import qc_su_lane_cut as C
    from test_qc_su_lane_cut import fixture
    old=fixture();core,_,_=C.cut(old,0)
    source=old.replace('.rst_n(rst_n)','.rst_n(rst_n_t10)').replace('    wire [7:0] x_q;','    wire rst_n_t10;\n    wire [7:0] x_q;')
    new,frame,r=C.cut(source,0)
    assert G._code(core)==G._code(new)
    assert '.rst_n(rst_n_t10)' in frame and r['reset_source']=='rst_n_t10' and r['input_bits']==8
    bad=source.replace('.rst_n(rst_n_t10)','.rst_n(rst_n_t11)',1)
    with pytest.raises(ValueError,match='one exact delivered reset'):C.cut(bad,0)
