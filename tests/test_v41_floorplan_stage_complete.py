import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_all_dense_headers_bound_once_and_capacity_refused():
    x=json.loads((ROOT/'results/floorplan/v41_stage17_complete_reservation.json').read_text())
    old=json.loads((ROOT/'results/floorplan/v41_stage17_bankmap.json').read_text())
    names=[n for e in x['dense_reservations'] for n in e['source_tensors']]
    assert len(names)==len(set(names))==30
    assert set(names)=={t['tensor'] for t in old['unbound_dense_tensors']}
    assert not x['totals']['capacity_pass']
    assert x['totals']['payload_excess_bytes']==7408140
    assert sum((i['row_end']-i['row_begin']) for i in x['spill_proposal']['intervals'])==x['spill_proposal']['rows']
    assert x['root_options'][0]['minimum_rows_to_remove']*264>=7408140
