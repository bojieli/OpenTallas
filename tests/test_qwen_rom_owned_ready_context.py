import json
import hashlib
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_owned_ready_context as Q


def test_snapshot_needs_crossed_FIFO_debt_and_sequence():
    assert Q.accept_snapshot(7,7,True,True,True,True,True)
    for i in range(5):
        v=[True]*5;v[i]=False
        assert not Q.accept_snapshot(7,7,*v)
    assert not Q.accept_snapshot(7,6,True,True,True,True,True)
    with pytest.raises(ValueError):Q.accept_snapshot(7,7,True,True,1,True,True)


def test_register_domain_conservation_and_distinct_candidate_sites():
    rows,channels=Q.allocation()
    assert len(rows)==6*77+34+379+128+192+5+1
    assert sum(c['source_FFs']+c['stream_FFs'] for c in channels)==462
    m,rows=Q.price()
    assert m['readiness_clock_reset_counts_per_rank']==dict(service=160,serial=40,stream=1001)
    assert len({tuple(r['candidate_site_um']) for r in rows})==len(rows)
    assert all(r['restoring_cell']==Q.INV for r in rows)


def test_no_transferred_physical_or_source_admission():
    m,_=Q.price()
    assert not any(m[k] for k in ('parent_reset_provider_instantiated','source_map_admission','startup_admitted','PnR','default_enabled'))
    assert m['tile_successor_counts_unchanged']==dict(clock=102352,reset=56683)
    assert m['service_macro_clocks_rank_once']==512
    assert m['actual_selected_parent_bridge_instance_count'] is None
    assert not m['predicate_logic_and_causal_export_cost_complete']


def test_latency_and_finite_wire_loads():
    m,_=Q.price()
    assert m['clean_two_stage_startup_demand_ps']['serial']>11000
    assert m['steady_latency_price_ps']==pytest.approx(833.333333333)
    assert m['readiness_control_corridor_reserved_tracks_demand']==222
    for c in ('ss','ff'):
        assert m['finite_leaf_clock_load_price'][c]['within_320ps_slew']
        assert m['finite_leaf_reset_load_price'][c]['cap_fF']>16*.165790


def test_receipt_reproduces_and_sourcepins():
    base=Q.R.ROOT/Q.OUT
    assert json.loads((base/'model-r1.json').read_text())==json.loads(json.dumps(Q.price()[0]))
    for p,h in json.loads((base/'sourcepins-r1.json').read_text()).items():
        assert hashlib.sha256((Q.R.ROOT/p).read_bytes()).hexdigest()==h
