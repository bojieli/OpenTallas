"""Single candidate and emitted golden packet semantics; no hardware credit."""
import gzip,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_candidate_packet_contract as C

@pytest.fixture(scope='module')
def contract():
    d=json.loads(gzip.decompress((C.B.ROOT/'results/uarch/dsrom_full_product_binding_20261002/demand-r3.json.gz').read_bytes()))
    return C.build(d)

@pytest.mark.parametrize('bits,total',[(272,282),(264,274),(256,266)])
def test_secded_required_bits(bits,total):
    assert bits+C.secded_bits(bits)==total

def test_one_budget_no_floor_or_selection(contract):
    b=contract['budget'];assert b['stages']==58 and b['TP']==4
    assert b['q_complete_pairs_per_die']+b['BF_complete_pairs_per_die']==3375
    assert b['reservation_macros_per_die']==13500
    assert b['corrected_capacity_verdict']=='FAIL'
    assert not contract['new_count_selected'] and not contract['hardware_admission']

def test_collective_manifest_matches_actual_emission(contract):
    rows=contract['collective_interface']['descriptors'];assert rows
    for c in rows:
        assert c['input_bytes_per_rank']==c['n']*(8 if c['op']==2 else 4)
        assert c['output_bytes_per_rank']==(c['k']*4 if c['op']==2 else c['n']*(16 if c['op']==1 else 4))
        assert len(c['rank_node_ids'])==4
    assert '((r0+r1)+(r2+r3))' in contract['collective_interface']['all_reduce']

def test_layer_packet_and_ECC_no_free_credit(contract):
    p=contract['stage_packet']['layer_boundary_payload'];assert p['packed_bytes_per_rank']==40976
    assert p['h_bytes_per_rank']+p['pre_bytes_per_rank']==40976
    w=contract['ECC']['word_formats'];assert not w[0]['fits_raw_word_bit_budget']
    assert all(not r['actual_SECDED_provider'] for r in w)
    assert contract['ECC']['no_free_physical_side_macro']
