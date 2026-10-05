import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_complete_layer_map_and_no_unproved_destination():
    x=json.loads((ROOT/'results/floorplan/v41_spill_relocation.json').read_text())
    assert len(x['stages'])==28
    assert x['expert_matrix_headers_checked']==40*384*3
    assert sum(s['expert_count'] for s in x['stages'])==40*384
    assert x['stages'][17]['ranks'][0]['free_bytes']==-7408140
    assert x['proposed_move'] is None
    assert x['eligible_destinations']==[]
    assert x['total_conservative_layer_spare_bytes']==0
    for s in x['stages']:
        names=[n for t in s['dense_tensors'] for n in t['source_tensors']]
        assert len(names)==len(set(names))
        for r in s['ranks']:
            assert r['payload_upper_bound_bytes']+r['free_bytes']==x['capacity_bytes']

def test_dense_refinement_and_compact_candidate_are_distinct():
    base=json.loads((ROOT/'results/floorplan/v41_spill_resolved_dense.json').read_text())
    comp=json.loads((ROOT/'results/floorplan/v41_spill_compact_woa_candidate.json').read_text())
    assert base['total_layer_deficit_bytes']==1253750576
    assert base['total_conservative_layer_spare_bytes']==0
    assert base['proposed_move'] is None
    assert comp['representation_profile']=='candidate_compact_woa_not_adopted'
    assert comp['stages'][17]['ranks'][0]['free_bytes']==718324
    assert comp['required_rows_to_move']==0 and comp['proposed_move'] is None
    assert comp['total_layer_deficit_bytes']>0
