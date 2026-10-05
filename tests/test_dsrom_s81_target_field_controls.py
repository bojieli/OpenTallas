import gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_s81_target_field_controls import native_stream
from dsrom_s81_capture_profile import compile_profile

def test_full_target_fields_have_actual_pair_and_root_coverage():
    wanted={}
    with gzip.open(ROOT/'results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz','rt') as f:
        for line in f:
            m=json.loads(line)
            if m['layer']==20 and m['alias'] in ('wq_a','wkv'):
                wanted[m['alias']]=m
            if len(wanted)==2:break
    conn=json.loads((ROOT/'results/uarch/dsrom_s81_rd64_connectivity_20261004/canonical_binding_r1/connectivity.json').read_text())
    for alias,rows,pairs in [('wq_a',320,160),('wkv',128,64)]:
        m=wanted[alias]
        assert m['stage']==37
        ph,stream,pin=native_stream(m)
        assert len(stream)==192 and (ph[0]>>46)&65535==rows
        assert len(pin)==64 and len({p[1] for p in m['plans']})==pairs
        profile=compile_profile(m,conn,1)
        assert sorted(r for root in profile['rows'] for r in root)==list(range(rows))
        assert sum(profile['root_return_counts'])==rows
