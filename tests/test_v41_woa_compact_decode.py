import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_exhaustive_decode_and_full_rank_record_current():
    x=json.loads((ROOT/'results/rtl/v41_woa_compact_decode.json').read_text())
    assert x['exhaustive_pairs']==65536
    assert x['valid_pairs']==254*255
    assert x['fault_pairs']==65536-254*255
    assert x['real_rank_values']==2048*4096
    assert x['real_mismatches']==0
    for p,h in x['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
