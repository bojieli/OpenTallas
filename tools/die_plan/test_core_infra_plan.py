import copy
import pytest
import core_infra as CI
import core_infra_plan as CP
from test_core_infra import sample


def test_plan_legalization_freezes_legal_sites_before_build():
    s=sample();u=1000
    tech=dict(dbu=u,core=[0,0,864000,864000],
      rows=[dict(rect=[0,y,864000,y+270],site=54,orient='R0' if j%2==0 else 'MX')
            for j,y in enumerate(range(427680,436320,270))],
      masters={'BUFx16f_ASAP7_75t_R':[1188,270],'BUFx4_ASAP7_75t_R':[378,270]},
      obstacles=[dict(name='fixed_driver',kind='fixed',rect=[431000,432270,433000,432810])])
    a,report=CP.legalize_slice(s,tech)
    b,_=CP.legalize_slice(s,tech)
    assert a==b and report['cell_or_macro_overlaps']==0
    cells=CI.compile_slice(a)['cells']
    assert len(cells)==2 and all(c['origin_um'][0]*1000%54==pytest.approx(0) for c in cells)
    assert 'ot_ci_origin_assert' in CI.emit_tcl(a)
    mutant=copy.deepcopy(a);mutant['cell_placements']['mp_isl0_ck0']['master']='BUFx24_ASAP7_75t_R'
    with pytest.raises(CI.InfraError,match='master differs'):CI.compile_slice(mutant)


def test_predictor_detects_wire_load_imbalance_without_changing_plan():
    s=sample();s['core_tree']=dict(clock_port='clk',nodes=[
      dict(name='root',master='BUFx16f_ASAP7_75t_R',xy_um=[430,430],parent='port:clk'),
      dict(name='left',master='BUFx8_ASAP7_75t_R',xy_um=[200,430],parent='root'),
      dict(name='right',master='BUFx8_ASAP7_75t_R',xy_um=[660,430],parent='root')],
      leaves=[dict(node='left',sinks=['a/CLK','b/CLK']),dict(node='right',sinks=['c/CLK','d/CLK'])])
    lib=dict(delay=([10,100],[1,100],[[10,30],[20,40]]),trans=([10,100],[1,100],[[10,30],[20,40]]),cap=1.)
    libs={'TT':{n:lib for n in ('BUFx16f_ASAP7_75t_R','BUFx8_ASAP7_75t_R')}}
    pts={'a/CLK':[195,430],'b/CLK':[205,430],'c/CLK':[655,430],'d/CLK':[665,430]};caps={n:.5 for n in pts}
    saved=copy.deepcopy(s)
    balanced=CP.predict_tree(s,libs,pts,caps,.02,.1)
    assert balanced['corners']['TT']['window_ps']==pytest.approx(0)
    pts['d/CLK']=[800,430]
    imbalanced=CP.predict_tree(s,libs,pts,caps,.02,.1)
    assert imbalanced['corners']['TT']['window_ps']>1 and s==saved
