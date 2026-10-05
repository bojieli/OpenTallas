import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_qwen_hbm_qkv_stage_w12 as S


def test_full_replica_gather_preserves_rows_and_requires_every_sm():
    parts={(d,s):np.arange(d*3072+s*96,d*3072+(s+1)*96,dtype=np.uint32)
           for d in (0,1) for s in range(32)}
    out=S.gather(parts)
    assert np.array_equal(out[0],np.arange(3072,dtype=np.uint32))
    assert np.array_equal(out[1],np.arange(3072,6144,dtype=np.uint32))
    del parts[1,31]
    with pytest.raises(ValueError):S.gather(parts)


def test_parser_rejects_duplicate_outputs_and_preserves_timeout(tmp_path):
    p=tmp_path/'out.txt'
    p.write_text('0 3f800000\n0 3f800000\n')
    with pytest.raises(ValueError):S.parse_output(p)
    p.write_text('# TIMEOUT\n')
    assert S.parse_output(p)[1]['timeout']
