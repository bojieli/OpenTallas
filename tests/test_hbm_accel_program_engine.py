"""Actual callback client protocol tests; no CPU model or old HDL gate reruns."""
import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from hbm_accel_program_backend import module
SMEngine20=module(Path(__file__).resolve().parents[1]/
    "results/rtl/hbm_accel_ha5_20261003/backend_join/sm_engine20_original.py",
    "tools.gpu_sys.ds_hbm_sm_engine20")
SMEngine20=module(Path(__file__).resolve().parents[1]/
    "results/rtl/hbm_accel_ha5_20261003/backend_join/sm_engine20_guarded.py",
    "ha5_sm_engine_guarded_test_pinned").SMEngine20Guarded
from hbm_accel_program_engine import RTLColumnEngine,decode_completion,program_adapter,slot6_overlap


class BoundaryPins:
    """Callback boundary fixture only; it does not claim RTL execution."""
    def __init__(self,wrong_generation=False):
        self.cycle=0;self.inputs={};self.active={};self.acks=[];self.offers=[]
        self.loads=[];self.wrong_generation=wrong_generation
    def snapshot(self):
        dies=[]
        for i in range(2):
            active=self.active.get(i)
            valid=active is not None and self.cycle>=active['due']
            raw=0
            if active:
                gen=active['generation']^(1 if self.wrong_generation else 0)
                raw=(active['job']<<77)|(gen<<73)|(9<<41)|(2<<37)|(active['pos']<<17)
            dies.append(dict(db_rdy=active is None and (self.cycle<2 or i==0 or self.cycle>=4),
                             cpl_v=valid,cpl_data=raw))
        return dict(rst_sm_n=1,sys_fault=0,cycle=self.cycle,dies=dies)
    def drive_die(self,index,**ports):self.inputs[index]=dict(ports)
    def tick(self):
        snap=self.snapshot()
        for i in range(2):
            p=self.inputs[i];d=snap['dies'][i]
            if p['cmd_we']:self.loads.append((i,p['cmd_addr'],p['cmd_wdata']))
            if p['db_v']:
                self.offers.append((self.cycle,i,p['db_token'],p['db_pos'],p['db_job'],p['db_generation']))
                if d['db_rdy']:
                    self.active[i]=dict(job=p['db_job'],generation=p['db_generation'],pos=p['db_pos'],due=self.cycle+3+i)
            if p['cpl_rdy'] and d['cpl_v']:
                self.acks.append((self.cycle,i));del self.active[i]
        self.cycle+=1


def engine(pins):
    return RTLColumnEngine(pins,{'layer':20},lambda c:[('layer',c['toks'][0],c['pos'])],
                           ndie=2,nsm=2,position_extent=1048576,
                           source_sha256='source-pin',enable=True,sm_engine_factory=SMEngine20)


def command():
    return dict(op='VLAYER',idx=20,ncol=1,pos=1048575,toks=[128799],job=0x12345678,generation=9)


def test_default_off_returns_exact_existing_engine():
    original=object()
    assert program_adapter(original) is original
    with pytest.raises(ValueError,match='explicit enable'):
        RTLColumnEngine(None,{},None,ndie=2,nsm=2,position_extent=32,source_sha256='pin')


def test_actual_callback_client_holds_token17_pos20_job_generation_through_backpressure():
    pins=BoundaryPins();eng=engine(pins)
    assert eng.run(command())==([],[])
    assert len(pins.loads)==4 and len(pins.acks)==2
    assert eng.launches==1 and eng.receipts[0]['pos']==1048575
    assert eng.receipts[0]['elapsed_edges']==pins.cycle
    assert all(o[2:]==(128799,1048575,0x12345678,9) for o in pins.offers)
    assert not pins.active
    assert all(p['cpl_rdy']==0 and p['db_v']==0 for p in pins.inputs.values())


def test_wrong_completion_generation_is_never_acked_or_freed():
    pins=BoundaryPins(wrong_generation=True);eng=engine(pins)
    with pytest.raises(RuntimeError,match='identity/status'):
        eng.run(command())
    assert pins.acks==[] and pins.active
    assert eng.launches==0 and eng.failed
    assert all(p['cpl_rdy']==0 and p['db_v']==0 for p in pins.inputs.values())
    with pytest.raises(RuntimeError,match='retains failed'):
        eng.run(command())


@pytest.mark.parametrize('field,value',[('job',None),('generation',16),('pos',1048576),('toks',[131072])])
def test_refuses_narrowing_before_any_callback_mutation(field,value):
    pins=BoundaryPins();eng=engine(pins);cmd=command();cmd[field]=value
    with pytest.raises(ValueError):eng.run(cmd)
    assert pins.inputs=={} and pins.cycle==0


def test_reduced_source_extent_does_not_inherit_pos20_capacity():
    pins=BoundaryPins();eng=engine(pins);eng.position_extent=32
    with pytest.raises(ValueError,match='source launch'):eng.run(command())
    assert pins.inputs=={}
    assert eng._valid_position('layer',31)
    assert not eng._valid_position('layer',32)
    eng.swapin_positions=(0,20,63)
    assert eng._valid_position('swapin',63)
    assert not eng._valid_position('swapin',32)


def test_cpl109_layout_matches_source_cluster_concatenation():
    raw=(0x12345678<<77)|(15<<73)|(123<<41)|(2<<37)|(1048575<<17)|128799
    assert decode_completion(raw)==dict(job=0x12345678,generation=15,cycles=123,status=2,pos=1048575,token=128799)
    with pytest.raises(ValueError):decode_completion(1<<109)


def test_slot6_measurement_requires_actual_source_intervals_and_keeps_gain_unset():
    identity=dict(epoch=1,layer=20,rank=0,sm=0,column=0,job=13,generation=2,source_sha256='pin')
    times=[('routed_fetch_request',1000),('shared_sm_issue',2000),('shared_sm_complete',7000),('routed_sm_first_line',5000)]
    events=[dict(identity,kind=k,time_ps=t) for k,t in times]
    row=slot6_overlap(events)[0]
    assert row['shared_sm_time_ns']==5 and row['overlap_ns']==3 and row['system_gain_ns'] is None
    with pytest.raises(ValueError,match='incomplete'):slot6_overlap(events[:-1])
    with pytest.raises(ValueError,match='ambiguous'):slot6_overlap(events+events[:1])


def test_source_native_fragment_retains_command_count_and_fits_real_allocator():
    root=Path(__file__).resolve().parents[1]
    record=json.loads((root/'results/rtl/hbm_accel_ha5_20261003/engine_join/native_compile_r2.json').read_text())
    assert len(record['cases'])==8
    for case in record['cases']:
        a,b=case['original'],case['shared_first']
        assert a['words']==b['words']
        assert a['tensor_commands']==b['tensor_commands']==2*(case['ke']+1)
        assert b['register_peak']<=b['register_capacity']
        for phase in ('prefix_begin','down_begin'):
            assert [x['slot'] for x in case['boundaries'] if x['phase']==phase]==[case['ke'],*range(case['ke'])]
        assert all(x['linked_pc']==record['entries'][f"moe_ke{case['ke']}"]+x['word_offset'] for x in case['boundaries'])
    tree=ast.parse((root/'results/rtl/hbm_accel_ha5_20261003/engine_join/native_moe_transformed_r2.py').read_text())
    fn=tree.body[0]
    loops=[n for n in fn.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='e']
    assert len(loops)==2 and all(ast.unparse(n.iter)=='(ke, *range(ke))' for n in loops)
    last=fn.body[-2]
    assert ast.unparse(last)=='y = lib.add(y, shared_y)'
