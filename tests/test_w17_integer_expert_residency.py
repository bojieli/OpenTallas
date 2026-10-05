import importlib.util
from pathlib import Path
from collections import defaultdict
import pytest
spec=importlib.util.spec_from_file_location('resident',Path(__file__).resolve().parents[1]/'tools/w17_integer_expert_residency.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
@pytest.fixture(scope='module')
def candidate():return m.build()

def test_lossless_template_segments_and_physical_addresses(candidate):
    # Exhaust the reusable affine template, both mates/parities, three actual shapes.
    occupied=set()
    for f in m.FAMILIES:
        cells=m.lookup(candidate,0,0,0,f)
        assert len(cells)==candidate['templates'][f]['physical_word_count']
        rows=defaultdict(set);segments=defaultdict(set)
        for c in cells:
            key=(c['pair'],c['mate'],c['parity'],c['physical_row'])
            assert key not in occupied;occupied.add(key)
            assert 0<=c['physical_row']<4096
            assert 2*c['physical_row']+c['parity']<candidate['pair_stride'][c['pair']]
            assert c['pair']//64== (c['row_index']//2)%128
            rows[c['row_index']].add((c['segment_index'],c['unit'],c['block'],c['half']))
            segments[c['row_index']].add((c['first_K_element'],c['K_elements']))
        t=candidate['templates'][f]
        assert set(rows)==set(range(t['rank_rows']))
        for row in rows:
            spans=sorted(segments[row]);assert spans[0][0]==0
            assert all(a+n==b for (a,n),(b,_) in zip(spans,spans[1:]))
            assert sum(n for a,n in spans)==t['K']
            assert len(rows[row])==t['physical_word_count']//t['rank_rows']

def test_all_resident_capacity_and_terminal_triplet(candidate):
    owners=candidate['owners'];cap=candidate['experts_per_stage_capacity']
    assert len(owners)==15360 and len({(o['layer'],o['expert']) for o in owners})==15360
    assert candidate['expert_only_stage_count']==(15360+cap-1)//cap
    assert candidate['expert_only_stage_count']!=45
    # Every bank's repeated templates occupy disjoint strides; terminal stage fits.
    assert max(candidate['pair_stride'].values())*cap<=8192
    assert max(candidate['pair_stride'].values())*(cap+1)>8192
    for f in m.FAMILIES:
        for rank in (0,3):
            cells=m.lookup(candidate,39,rank,383,f)
            assert all(c['physical_row']<4096 for c in cells)
            assert {c['stage'] for c in cells}=={owners[-1]['stage']}
    assert candidate['descriptor']['current_64_entry_phase_capacity_fails']
    assert not candidate['physical_admission'] and not candidate['top_build_ready']
    assert candidate['full_token_rate'] is None
    assert all(h['finite_hop_cycles'] is None for h in candidate['layer_hop_requirements'])
    g=candidate['geometry_reconciliation']
    assert g['capacity_bits_per_pair']==g['physical_capacity_bits_per_pair']
    assert not g['historical_3749_q_fit_transferred']

def test_no_whole_expert_capacity_is_explicit_failure(candidate):
    with pytest.raises(ValueError,match='whole triplet cannot fit'):
        m.assignments(None,candidate['templates'],candidate['pair_stride'],depth=1)


def test_hop_serialization_cannot_bypass_one_bit_port():
    r=m.price_hop(1024,1,1,1,0,0,3072,4)
    assert r['serialization_source_cycles_per_hop']==1024
    assert r['packet_credit_release_tick']==3076
    with pytest.raises(ValueError,match='precedes'):
        m.price_hop(1024,1,1,1,0,0,3,4)
    with pytest.raises(ValueError,match='missing positive'):
        m.price_hop(1024,None,1,1,0,0,3072,4)
    with pytest.raises(ValueError,match='missing hop latency'):
        m.price_hop(1024,1,1,1,0,None,3072,4)
