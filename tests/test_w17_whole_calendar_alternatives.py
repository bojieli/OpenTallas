import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_whole_calendar_alternatives as C
import w17_integer_expert_residency as R

def test_atomic_pair_waves_do_not_split_output_rows():
    t,_=R.templates(R.inputs(),1024)
    for f,v in t.items():
        bins=C.waves(v,256)
        membership={p:i for i,b in enumerate(bins) for p in b}
        rows={}
        for p in v['pairs']:
            for s in p['segments']:
                rows.setdefault(s['row'],set()).add(membership[p['pair']])
        assert all(len(x)==1 for x in rows.values())
        assert sorted(membership)==sorted(p['pair'] for p in v['pairs'])
        assert C.wave_stream(v,list(membership))['stream_issue_cycles']==v['stream_issue_cycles']

def test_head_exact_capacity_parity_and_tiling():
    h=C.head_layout()
    assert sum(t['output_rows'] for t in h['tiles'])==32320
    assert h['physical_words_per_rank']==10342400
    assert h['stream_issue_cycles']==5120
    assert all(p['physical_max_row']<4096 for t in h['tiles'] for p in t['pair_address_receipt'])
    assert not h['actual_image_and_FP32_return_exactness']

def test_incomplete_dispatch_is_a_partial_calendar():
    owners=[dict(layer=l,stage=l*2,slot=e,expert=e) for l in range(40) for e in range(384)]
    x=C.dispatch_calendar(owners,1024)
    assert len(x['per_layer'])==40
    assert x['total_ticks']>0
    assert all(sum(n for _,n,_ in r['worst_six_distinct'])==6 for r in x['per_layer'])
