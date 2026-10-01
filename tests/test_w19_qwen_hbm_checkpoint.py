"""Protect ownership boundaries, packing order and fail-closed RTL verdicts."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import w19_qwen_hbm_checkpoint as C


def test_all_sm_windows_cover_tp_qkv_once():
    for die in (0, 1):
        got = {kind: [] for kind in ('q','k','v')}
        for sm in range(32):
            parts = C.row_segments(die,sm)
            assert sum(hi-lo for _,lo,hi in parts) == 96
            for kind,lo,hi in parts:
                got[kind].extend(range(lo,hi))
        for kind,n in [('q',2048),('k',512),('v',512)]:
            assert got[kind] == list(range(die*n,(die+1)*n))
    assert [x[0] for x in C.row_segments(0,21)] == ['q','k']
    assert [x[0] for x in C.row_segments(1,26)] == ['k','v']
    with pytest.raises(ValueError):
        C.row_segments(0,32)


def test_verdict_rejects_fault_missing_release_and_missing_lines():
    expected = np.array([0x3f800000,0xbf800000],dtype=np.uint32)
    res = {0:'3f800000',1:'bf800000'}
    meta = dict(fault=0,consumed=64,released=1)
    assert C.verify(res,meta,expected,1,64) == (0,True)
    for key,value in [('fault',1),('released',0),('consumed',63),('timeout',True)]:
        assert not C.verify(res,dict(meta,**{key:value}),expected,1,64)[1]
    assert C.verify({0:res[0]},meta,expected,1,64) == (1,False)
    assert not C.verify(dict(res,**{} ) | {2:'00000000'},meta,expected,1,64)[1]


def test_real_shape_packing_uses_complete_contiguous_chunks(tmp_path):
    # Each chunk has a distinct byte; t stays within it, g selects 128 chunks.
    q = np.tile(np.repeat(np.arange(256,dtype=np.uint8),16).view(np.int8),(96,1))
    x = np.arange(4096,dtype=np.float32)
    assert C.pack(tmp_path,q,np.ones(96,dtype=np.float32),x,1) == 3072
    lines = (tmp_path/'lines.hex').read_text().splitlines()
    assert int(lines[0][-2:],16) == 0
    assert int(lines[0][:2],16) == 127
    # rb,g,t,slot order: 16 t iterations of 8 slots precede group 1.
    assert int(lines[128][-2:],16) == 128
    xwords = (tmp_path/'x.hex').read_text().splitlines()
    assert int(xwords[0][-4:],16) == int(C.S.bf16_bits(x)[0])
    assert int(xwords[16][-4:],16) == int(C.S.bf16_bits(x)[2048])
    assert int(xwords[32],16) == 0


def test_results_are_append_only(tmp_path):
    p = tmp_path/'failed.json'
    C.save_json(p,dict(status='fail'))
    with pytest.raises(FileExistsError):
        C.save_json(p,dict(status='pass'))
