import importlib.util,json
from pathlib import Path
import pytest
P=Path(__file__).resolve().parent/'cb16_dag.py'
spec=importlib.util.spec_from_file_location('dag',P);D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)

def test_an_interior_early_leg_delays_only_a_real_upstream_crossing():
    c='c16_E0_0';f0=c+'.u_fab.u_x_0_0';f1=c+'.u_fab.u_x_1_0';t0=c+'.u_t_0_0';t1=c+'.u_t_1_0'
    inp={f0:{'b_d':('hc0','out',2)},f1:{'b_d':('hc1','out',4)},t0:{'tap':(f0,'tap_d',0),'n_a':(t0,'t_out',0),'n_b':(t1,'t_out',0)},t1:{'tap':(f1,'tap_d',0)}}
    nodes,rels,roots=D.build(inp,{(f0,'b_d'):{'real0'},(f1,'b_d'):{'real1'}});phase,_=D.solve(nodes,rels)
    added=[(e['ids'],phase[e['dst']]-phase[e['src']]-e['off']) for e in rels]
    assert [(x,n) for x,n in added if n]==[(['real0'],2)]
    assert phase[t0+'.n_y']==4
    assert all(n==0 for ids,n in added if not ids)

def test_a_fixed_phase_contradiction_is_rejected():
    relations=[dict(src=D.ROOT,dst='a',off=0,ids=['launch']),dict(src='a',dst='b',off=1,ids=[]),dict(src='b',dst='a',off=0,ids=[])]
    with pytest.raises(ValueError,match='infeasible'):D.solve({D.ROOT,'a','b'},relations)

def test_payload_and_valid_with_different_added_ages_are_rejected(tmp_path):
    leaf='c16_E0_0.u_fab.u_x_0_0'
    (tmp_path/'bind_sinks.json').write_text(json.dumps({leaf+'.b_d[0]':['pin','hc.out[0]',2,False],leaf+'.b_d[1]':['pin','hc.out[1]',3,False]}))
    (tmp_path/'bus_groups.json').write_text(json.dumps({'die':'qwen_compute','landing':[{'sink':leaf,'members':[{'sink_port':'b_d','sink_bits':[[0,1]],'source':'hc.out','asbuilt_stages':0}]}]}))
    (tmp_path/'r8.json').write_text(json.dumps({'members':[]}))
    with pytest.raises(ValueError,match='incoherent'):D.load(tmp_path,tmp_path/'r8.json')
