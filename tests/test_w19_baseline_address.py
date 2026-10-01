import json
import hashlib
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_baseline_address as B
P=Path(__file__).resolve().parents[1]/'results/uarch/w19_baseline_aw27_prebuild.json'
CASES=json.loads(P.read_text())['cases']

@pytest.mark.parametrize('case',CASES)
def test_actual_boundary_roundtrip_and_narrow_rejection(case):
    row=case['descriptor'];e=case['expert_id']
    with pytest.raises(ValueError,match='OFF'):B.descriptor(row,e,address_bits=27)
    with pytest.raises(ValueError,match='overflow'):B.descriptor(row,e,enable=True)
    d=B.descriptor(row,e,enable=True,address_bits=27)
    assert d['first_sector']*32==case['first_byte']
    assert case['first_byte']<case['boundary_bytes']<case['first_byte']+d['sector_count']*32
    assert not d['resident_admitted'] and d['fragment_only']

@pytest.mark.parametrize('delta',[dict(cfg_base_line=0),dict(cfg_off=65536),dict(byte_length=136),dict(stack=0),dict(expert_stride_bytes=128),dict(resident_last_exclusive=0)])
def test_no_alias_compact_or_geometry_changes(delta):
    c=CASES[0]
    with pytest.raises(ValueError):B.descriptor(dict(c['descriptor'],**delta),c['expert_id'],enable=True,address_bits=27)


def test_independent_full_address_sector_packing(tmp_path):
    c=CASES[0];r=c['descriptor'];src=tmp_path/'lines.hex'
    record=bytes(range(136));src.write_text((f'{int.from_bytes(record,"little"):0272x}\n')*r['payloads'])
    sha=hashlib.sha256(src.read_bytes()).hexdigest()
    d=B.load_fragment(src,tmp_path,r,c['expert_id'],expected_sha256=sha,enable=True,address_bits=27)
    keys=[int(x,16) for x in (tmp_path/'sparse_keys.hex').read_text().splitlines()]
    vals=[int(x,16).to_bytes(32,'little') for x in (tmp_path/'sparse_values.hex').read_text().splitlines()]
    assert keys==list(range(d['first_sector'],d['first_sector']+r['payloads']*8))
    assert b''.join(vals)==(record+bytes(120))*r['payloads']
    with pytest.raises(ValueError,match='overwrite'):B.load_fragment(src,tmp_path,r,c['expert_id'],expected_sha256=sha,enable=True,address_bits=27)
    with pytest.raises(ValueError,match='hash'):B.load_fragment(src,tmp_path,r,c['expert_id'],expected_sha256='wrong',enable=True,address_bits=27)
