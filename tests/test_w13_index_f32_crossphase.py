import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w13_index_f32_crossphase as M

def test_candidate_allocation_and_phase_dependency():
    d=M.build();r=list(d['layout'].values())
    assert all(a[1]<=b[0] for a,b in zip(r,r[1:]))
    assert max(z[1] for z in r)==61440<65536
    assert d['without_phase_reuse_peak_bytes']==65664>65536
    seen=set()
    for p in d['lifetime_plan']:
        assert set(p['deps'])<=seen;seen.add(p['id'])
        assert p['tick'] is None
    assert d['score_copy_extra_shared_read_write_bytes']==65536
    assert d['score_copy_extra_LOAD_STORE_warp_issues']==512

def test_copy_finite_banks_and_full_region_coverage():
    d=M.build();events=d['ordinary_copy_events'];src=set();dst=set()
    for e in events:
        assert len(set(x%32 for x in e['source_words']))==32
        assert len(set(x%32 for x in e['destination_words']))==32
        assert e['RF_reads_per_lane']<=2 and e['RF_write_ports']<=1
        src.update(e['source_words']);dst.update(e['destination_words'])
    assert src==set(range(12800,14848))
    assert dst==set(range(4096,12288))

def test_actual_callbacks_not_promoted_to_runtime():
    d=M.build()
    assert len(d['actual_callbacks'])==8
    for c in d['actual_callbacks']:
        assert c['raw_callback']['completed']
        assert not c['raw_callback']['DUT_executed']
        assert c['instruction_branch_trace'] is None
        assert c['RF_shared_service_ticks'] is None
    assert d['runtime_branch_choices'] is None
    assert d['physical_admission']=='FAIL_CLOSED'
