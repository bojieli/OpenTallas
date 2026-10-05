"""Actual accepted256 placement and wide arithmetic refusal boundaries."""
import copy
import importlib.util
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w16_w19_address_prerequisite as W
import w16_measured_calibration as C


def test_sector_exclusive_end_and_units():
    assert W.descriptor(0,0,0,2,0,24)==(0,8)
    assert W.descriptor((1<<22)-2,0,0,2,0,24)==((1<<24)-8,1<<24)
    with pytest.raises(C.Refusal,match='sector aperture'):
        W.descriptor((1<<22)-1,0,0,2,0,24)


@pytest.mark.parametrize('values', [(1<<22,0,0,1,0,24),(0,65536,0,1,0,27),
                                    (0,0,65536,1,0,27),(0,0,0,65536,0,27),
                                    (0,0,0,1,384,27),(-1,0,0,1,0,27)])
def test_narrowing_wrap_and_field_overflow_refused(values):
    with pytest.raises(C.Refusal):W.descriptor(*values)


def test_last_expert_overflow_checked_without_modulo_credit():
    assert W.descriptor(0,12000,0,2,0,24)==(0,8)
    with pytest.raises(C.Refusal,match='aperture'):
        W.descriptor(0,12000,0,2,383,24)


def test_full_real_placement_matches_ledger_and_homes():
    program,floorplan=C.read(C.W19_PROGRAM),C.read(C.W19_FLOORPLAN)
    got=W.placement(program,floorplan)
    records,_=C.resident_records(program,floorplan)
    assert got['rank_stack_bytes']==[[n*256 for n in row] for row in records]
    assert sum(map(sum,got['rank_stack_bytes']))==778764812288
    assert max(map(max,got['rank_stack_bytes']))==2597703680
    assert got['address_checks']['24']['failed']>0
    assert got['address_checks']['27']['failed']==0
    import json
    assert json.loads(json.dumps(got))==got
    assert got['cfg_field_maxima']['cfg_lines']<65536
    assert got['cfg_field_maxima']['cfg_off']<65536
    assert got['cfg_field_maxima']['cfg_exp_lines']<65536
    assert got['highest_resident_address']['last_sector']==2597703680//32-1


def test_duplicate_or_missing_sm_home_refused():
    floor=C.read(C.W19_FLOORPLAN);floor['quadrants']['0'].remove(0)
    with pytest.raises(C.Refusal,match='incomplete'):
        W.placement(C.read(C.W19_PROGRAM),floor)


def test_missing_non_sm_reservation_never_qualifies():
    with pytest.raises(C.Refusal,match='reservations missing'):
        W.reservations_fit(256,{},1<<32)


def regions():
    return {k:dict(base_bytes=256*(i+1),bytes=256) for i,k in enumerate(
        ['constants','embedding','Engram','KV','index'])}


def test_explicit_non_sm_ranges_need_no_overlap_and_real_space():
    assert W.reservations_fit(256,regions(),1536)==1536
    r=regions();r['index']['base_bytes']=256
    with pytest.raises(C.Refusal,match='overlap'):
        W.reservations_fit(256,r,1<<32)
    with pytest.raises(C.Refusal,match='exceeds aperture'):
        W.reservations_fit(256,regions(),1535)


def test_record_stride_is_256_padding_not_compact136():
    op={'rows':[[0,1]]*96,'k':32,'fmt':'fp8'}
    assert W.payload_count(op,0,0)==8
    assert W.payload_count(op,0,1)==0
    e=dict(base=0,stride=16,offset=0,lines=16,experts=384)
    checks={24:dict(passed=0,failed=0,first_failure=None)}
    import hashlib
    maxima=dict(cfg_exp_lines=0,cfg_off=0,cfg_lines=0,cfg_base=0)
    W.audit_entry(e,checks,maxima,hashlib.sha256())
    assert checks[24]['passed']==2 and not checks[24]['failed']
    e['base']=1
    with pytest.raises(C.Refusal,match='alignment'):
        W.audit_entry(e,checks,maxima,hashlib.sha256())
