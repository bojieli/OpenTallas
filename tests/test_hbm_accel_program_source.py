"""Archived source enrollment checks; no fixture compile or numeric execution."""
import json
from pathlib import Path
import sys
import pytest
from tools.hbm_accel_program_backend import module
from tools.hbm_accel_program_source import enroll_loaded

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/gpu_sys'))
import v41_dspark as D
module(ROOT/'results/rtl/hbm_accel_ha5_20261003/backend_join/sm_engine20_original.py',
       'tools.gpu_sys.ds_hbm_sm_engine20')
GUARD=module(ROOT/'results/rtl/hbm_accel_ha5_20261003/backend_join/sm_engine20_guarded.py',
             'ha5_source_guard_test').SMEngine20Guarded


class LoadedPins:
    def __init__(self,source):self.source=source
    def snapshot(self):pytest.fail('enrollment sampled or advanced simulator')
    def drive_die(self,*args,**kwargs):pytest.fail('enrollment drove simulator')
    def tick(self):pytest.fail('enrollment advanced simulator')


def record():
    result=json.loads((ROOT/'results/rtl/hbm_accel_ha5_20261003/prepared_source_join/candidate_r2/result.json').read_text())
    return dict(schema='opentallas.ds_hbm.simulator20_source.v1',entries=result['baseline_entries'],
                position_extent=32,full_shape=False,noise=3559,artifacts=result['original_artifacts'])


def test_source_column_enrollment_keeps_owner_and_original_expand_globals(tmp_path):
    source=record();path=tmp_path/'source.json';path.write_text(json.dumps(source))
    pins=LoadedPins(source);old=D.NOISE
    engine=enroll_loaded(pins,path,D,enable=True,sm_engine_factory=GUARD)
    assert engine.pins is pins and engine.sm_engine.pins is pins
    assert D.NOISE is old and engine.expand.__code__ is D.expand.__code__
    assert engine.expand.__globals__['NOISE']==3559
    command=dict(op='VLAYER',idx=20,ncol=6,pos=4,toks=[0,1,2,3,4,5])
    launches=list(engine.expand(command))
    assert launches==[(kind,token,pos) for i in range(6) for kind,token,pos in
        [('swapin',i,20),('layer',i,4+i),('swapout',i,4+i)]]


def test_refuses_candidate_before_touching_unmodified_preloaded_source(tmp_path):
    source=record();path=tmp_path/'source.json';path.write_text(json.dumps(source))
    candidate=ROOT/'results/rtl/hbm_accel_ha5_20261003/prepared_source_join/candidate_r2/result.json'
    with pytest.raises(ValueError,match='not actually loaded'):
        enroll_loaded(LoadedPins(source),path,D,candidate=candidate,enable=True,sm_engine_factory=GUARD)


def test_missing_source_owner_and_default_off_refuse(tmp_path):
    source=record();path=tmp_path/'source.json';path.write_text(json.dumps(source))
    with pytest.raises(ValueError,match='explicit'):
        enroll_loaded(LoadedPins(source),path,D)
    with pytest.raises(ValueError,match='identity'):
        enroll_loaded(LoadedPins(dict(source,noise=0)),path,D,enable=True)
