import copy
import json
from types import SimpleNamespace as S
import pytest
from qwen_split import gfp_homes as g


def model():
    return dict(die=dict(w=100,h=100),insts=[S(name='a',master='M',x=0,y=0,w=10,h=10,orient='R0'),S(name='b',master='M',x=20,y=0,w=10,h=10,orient='R0')],buses=[('bus','data',1,[('a','q'),('b','d')])])


def candidate(m):
    return dict(schema='opentallas.qwen.globalfp-homes.v1',source_model_sha256=g.source_fingerprint(m),homes={'a':dict(m='M',x=0,y=20,w=10,h=10,o='MX')})


def run(tmp_path,m,d):
    p=tmp_path/'homes.json';p.write_text(json.dumps(d));return g.apply(m,p)


def test_whole_block_move_and_source_pin(tmp_path):
    m=model(); d=candidate(m); r=run(tmp_path,m,d)
    assert (m['insts'][0].y,m['insts'][0].orient)==(20,'MX')
    assert r['moved_names']==['a'] and r['qualified'] is False
    m=model(); d=candidate(m);m['buses'][0]=('bus','data',2,[('a','q'),('b','d')])
    with pytest.raises(ValueError,match='source_model'):run(tmp_path,m,d)


@pytest.mark.parametrize('change', ['overlap','outside','master','nan','orientation','reserve','outline'])
def test_malformed_candidate_is_transactional(tmp_path,change):
    m=model();d=candidate(m);before=copy.deepcopy(m)
    if change=='overlap':d['homes']['a'].update(x=20,y=0)
    if change=='outside':d['homes']['a']['x']=101
    if change=='master':d['homes']['a']['m']='other'
    if change=='nan':d['homes']['a']['x']=float('nan')
    if change=='orientation':d['homes']['a']['o']='R90'
    if change=='reserve':d['reserve']={'new':dict(x=20,y=0,w=10,h=10)}
    if change=='outline':d['homes']['a']['w']=11
    with pytest.raises(ValueError):run(tmp_path,m,d)
    assert m==before
