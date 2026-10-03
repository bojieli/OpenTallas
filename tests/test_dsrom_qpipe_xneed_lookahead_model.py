"""Model gate only: no HDL/numerical/timing qualification follows."""
import json
import shutil
from dataclasses import replace
import pytest
from tools.model_dsrom_qpipe_xneed_lookahead import (
    RECORD, State, baseline_next, candidate_next, facts_for, priority_table,
    exercise, build_model, verify_inputs,
)


def test_source_pins_and_record_replay():
    verify_inputs()
    assert build_model() == json.loads((RECORD/'model.json').read_text())


def test_original_clock_scope_and_no_adoption():
    model=build_model()
    assert model['observed_baseline']['fmax_mhz'] == pytest.approx(634.6712900997713)
    assert model['observed_baseline']['startpoint'].startswith('u_e.n_c[')
    assert not model['hardware_written'] and not model['compile_launched']
    assert not model['stage_or_die_records_regenerated']
    assert not model['latency']['historical_pricing_is_current_scenarioC']


def test_every_class_priority_mask():
    for mask in range(256):
        table=priority_table(mask,8)
        for c in range(8):
            expected=[i for i in range(c+1,8) if mask & (1<<i)]
            assert table[c] == (bool(expected), expected[0] if expected else 0)


def test_all_local_unit_priority_categories():
    # Other classes' unit counts are irrelevant to this transition once their
    # live mask is fixed. All 256 masks, all selected classes and all 0..8
    # counts/0..7 j are covered (zero included as a malformed-state witness).
    for mask in range(256):
        table=priority_table(mask,8)
        for c in range(8):
            for count in range(9):
                cur=(count,)*8
                for j in range(8):
                    s=State(1,2,3,c,j)
                    f=facts_for(s,mask,0,cur,7,0)
                    assert (f.has_next_class,f.next_class)==table[c]
                    assert candidate_next(s,f)==baseline_next(s,mask,0,cur,7)


def test_every_round_subblock_firstclass_and_final_boundary():
    for q in range(8):
        for b in range(8):
            for qlast in range(8):
                for first_next in range(8):
                    s=State(1,q,b,7,7,7)
                    cur=(8,)*8
                    nxt=1<<first_next
                    f=facts_for(s,128,nxt,cur,qlast,7)
                    assert candidate_next(s,f)==baseline_next(s,128,nxt,cur,qlast)


def test_consecutive_full_geometry_max_positions_and_stalls():
    units=(64,63,56,40,32,16,8,1)
    enabled=(True,)*8
    trace,edges=exercise(units,enabled,7,7)
    assert len(trace)==sum(units)*8*8
    assert edges==len(trace)
    assert [t[0] for t in trace]==list(range(edges))
    delayed,delayed_edges=exercise(units,enabled,7,7,stalls=(0,1,9,27,128,1024))
    assert [t[1:] for t in delayed]==[t[1:] for t in trace]
    assert delayed_edges==edges+6
    assert trace[-1][1:]==(7,7,7,1,6)  # final source class with 63 units


def test_empty_go_and_single_short_class():
    assert exercise((0,)*8,(False,)*8,0,7)==([],0)
    t,e=exercise((0,0,1,0,0,0,0,0),(False,False,True,False,False,False,False,False),0,7)
    assert e==64 and len(t)==64
    assert {row[4] for row in t}=={2} and {row[5] for row in t}=={0}


@pytest.mark.parametrize('mutant',['stale_last','two_cycle'])
def test_model_mutants_cannot_hide_a_changed_transition(mutant):
    with pytest.raises(AssertionError):
        exercise((3,1,0,0,0,0,0,0),(True,True,False,False,False,False,False,False),0,1,mutant=mutant)


def test_precise_state_and_cost_not_double_charged():
    model=build_model();c=model['construction'];cost=model['cost']
    assert c['data_FF_increment']==249 and c['async_valid_FF_increment']==3
    assert c['total_FF_increment']==252
    assert c['tables_per_local_copy_bits']==72
    assert c['facts_per_local_copy_bits']==11
    assert not c['existing_nA_nB_nQ2_state_charged_again']
    assert c['fill_cycles_increment']==0 and c['accepted_beat_II_cycles']==1
    assert cost['combined_incremental_cell_area_reserve_um2'] > cost['state_area_um2']
    assert cost['added_external_boundary_bits_per_cycle']==0
    assert 'pending' in cost['track_capacity_and_extracted_RC']


def test_corrupt_archive_refuses_without_git_fallback(tmp_path):
    shutil.copytree(RECORD,tmp_path/'record')
    (tmp_path/'record/inputs/clock_screen.json').write_bytes(b'wrong bytes')
    with pytest.raises(ValueError,match='source input changed'):
        verify_inputs(tmp_path/'record')
