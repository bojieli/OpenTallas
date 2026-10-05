"""Historical source/default/corner joins must not promote failed physical cuts."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_physical_join as J

ROOT=Path(__file__).resolve().parents[1]


def test_real_spine_rejects_mismatched_context_and_tt():
    path=ROOT/'results/rtl/qwen_rom_w12_runtime/terminal_review_20261001/spine_s833b/00_physical.json'
    raw=path.read_bytes();record=json.loads(raw)
    result=J.join_record(record,dict(source_sha256_at_capture={},params=dict(die=[
        '-GG=6144','-GSMIN=7','-GTCUT=7','-GBD=41','-GNWS=5','-GTWS=38','-GORD=7','-GSCALE_LOCAL=0'])))
    assert all(result['historical_source_checks'].values())
    assert result['parameter_differences']['BD']==dict(physical=2,runtime=41)
    assert result['parameter_differences']['SCALE_LOCAL']==dict(physical=1,runtime=0)
    assert result['status']=='error' and not result['product_closure']
    assert any('cell corner is not SS' in r for r in result['blockers'])
    assert path.read_bytes()==raw


def test_logic_only_old_vehicle_does_not_establish_real_tile():
    path=ROOT/'results/physical_hdc/asap7/qwen_o4_w12/tile_logic_b12/physical.json'
    result=J.join_record(json.loads(path.read_text()),dict(source_sha256_at_capture={},params=dict(tile=[
        '-GGT=6144','-GCODE_BANKS=5','-GKV_LOCAL=0'])))
    assert result['top']=='ot_qwen_rom_tile_logic'
    assert result['parameter_differences']['GT']==dict(physical=5120,runtime=6144)
    assert result['parameter_differences']['CODE_BANKS']==dict(physical=12,runtime=5)
    assert not result['product_closure']


def test_unrecoverable_commit_and_unknown_parameter_fail_closed():
    record=dict(git=dict(commit='0000000'),status='pass',corner=dict(name='SS'),target_clock_period_ns=1/1.2,
        design=dict(top='ot_qwen_rom_tile',closed=True,clock_uncertainty_ns=.060,clock_uncertainty_hold_ns=.025,
            parameters=dict(UNKNOWN=1),sources=[dict(path='rtl/hdc/ot_qwen_rom_tile.sv',sha256='0'*64)]))
    r=J.join_record(record,dict(params={},source_sha256_at_capture={}))
    assert r['unknown_overrides']==['UNKNOWN'] and not all(r['historical_source_checks'].values())
    assert not r['product_closure']
