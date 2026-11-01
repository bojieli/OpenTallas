import copy,json
from pathlib import Path
import pytest
from layer_prog.norm_nx_candidate import events,collisions,retime

R=Path(__file__).resolve().parents[3]/'results/token_pass/norm_leaf_calendar_1101'


def test_actual_book_retiming_preserves_inputs_and_removes_conflicts():
    b=json.loads((R/'book_head_final/candidate.json').read_text())
    t=json.loads((R/'nx_routes_kva3.json').read_text())
    assert collisions(events(b,t,6))
    p=retime(b,t,6)
    assert not collisions(events(p,t,6))
    assert len({(r['eng'],r['issue'])for r in p['rows']})==96
    assert p['templates']==b['templates'] and p['head_egress_flag']==128
    for sl in p['nx_cohort_shifts']:
        old=[c for c in b['commands']if c['kind']=='NORMR'and c['slice']==sl]
        new=[c for c in p['commands']if c['kind']=='NORMR'and c['slice']==sl]
        assert len({n['issue']-o['issue']for o,n in zip(old,new)})==1
    assert p['actual_output_edges']is None and not p['native_job_sealed']


def test_missing_actual_path_and_wrong_source_cannot_be_timed():
    b=json.loads((R/'book_head_final/candidate.json').read_text())
    t=json.loads((R/'nx_routes_kva3.json').read_text());bad=copy.deepcopy(t)
    bad['source_top_sha256']='different'
    with pytest.raises(ValueError,match='same-source'):retime(b,bad,6)
    bad=copy.deepcopy(t);bad['snake_peer_paths'].pop()
    with pytest.raises(ValueError,match='all240'):retime(b,bad,6)
    with pytest.raises(ValueError,match='explicit measured'):retime(b,t,None)
