"""Precompile arithmetic oracle and preparation controls; no RTL tools."""
import json
from pathlib import Path
import sys
import subprocess
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w17_window_qdq8_arithmetic_model as M
import hdc_golden_v41 as G


def test_binary_rounding_tie_and_gradual_underflow():
    assert M.ieee_round(M.p2(-149))==1
    assert M.ieee_round(M.p2(-150))==0
    assert M.ieee_round(3*M.p2(-150))==2
    assert M.ieee_round(M.F(1)+M.p2(-24))==0x3f800000
    assert M.ieee_round(M.F(1)+3*M.p2(-24))==0x3f800002
    assert M.ieee_round(M.F(0),7,True)==0x8000


def test_full_512_modes_independent_oracle_against_repository_golden():
    for name,rows in M.vectors().items():
        if name=='nonfinite_flags':continue
        assert len(rows)==16 and all(len(b)==32 for b in rows)
        x=np.array(rows,dtype=np.uint32).reshape(-1).view(np.float32)
        q,e=G.quant_fp8(x);ys=G.bits(G.qdq_fp8(x))
        for b,words in enumerate(rows):
            out=M.oracle(words)
            assert out['exponent']==int(e[b])
            assert out['bf16_widened']==list(map(int,ys[32*b:32*b+32]))
            assert [float(M.fp8_value(c)) for c in out['codes']]==list(q[32*b:32*b+32])


def test_all_nonpoison_codes_and_signed_zero_behavior():
    out=[M.oracle(b) for b in M.vectors()['fp32_rounding']]
    coverage={c for b in out for c in b['codes']}
    assert coverage==set(range(256))-{127,255}
    z=M.oracle([0x80000000,0xb5800000]+[0]*29+[M.ieee_round(M.F(448))])
    assert z['codes'][0]==0 and z['codes'][1]==128
    assert z['bf16_widened'][0]==0 and z['bf16_widened'][1]==0x80000000


def test_half_even_code_rounding_and_adjacent_neighbors():
    for c in (7,8,55,56,119,120):
        mid=M.ieee_round((M.fp8_value(c)+M.fp8_value(c+1))/2)
        out=M.oracle([mid-1,mid,mid+1]+[0]*28+[M.ieee_round(M.F(448))])
        assert out['codes'][:3]==[c,c if c%2==0 else c+1,c+1]


def test_nonfinite_flags_fail_closed():
    for words in M.vectors()['nonfinite_flags']:
        assert M.oracle(words)=={'fault':1,'valid':0}


def test_source_derived_edge_chain_and_mutant():
    qe=(ROOT/M.QE).read_text();aq=(ROOT/M.AQ).read_text()
    cal=M.edge_calendar(qe,aq)
    assert cal['capture_sample']==[n+2 for n in cal['aq_output_post']]
    assert cal['global_fault_sample']==[n+1 for n in cal['capture_sample']]
    assert cal['block_accept']==[c for c in range(cal['issue_sample']+1,cal['healthy_terminal_sample']) if c%5]
    with pytest.raises(AssertionError):M.edge_calendar(qe,aq.replace('s9_v <= s8_v','s9_v <= s7_v'))


def test_prepared_snapshot_and_complete_include_paths(tmp_path):
    directory=tmp_path/'prepared'
    subprocess.run([sys.executable,str(ROOT/'tools/w17_window_qdq8_arithmetic_model.py'),'--out',str(directory)],cwd=ROOT,check=True,capture_output=True)
    meta=json.loads((directory/'model.json').read_text())
    for p,h in json.loads((directory/'preparation_sha256.json').read_text()).items():
        assert M.sha(directory/p)==h
    cmd=meta['preparation']['compile_command']
    assert '-I'+str(directory) in cmd and (directory/'calendar.svh').is_file()
    assert meta['parameters']['BL']==16 and meta['parameters']['nb']==16
    assert len(meta['preparation']['snapshot_sha256'])==len(M.SOURCES)+1
    assert not(directory/'obj').exists()
    for n in meta['cases']:
        for p,h in meta['cases'][n]['files_sha256'].items():assert M.sha(directory/n/p)==h
    tb=(ROOT/M.BENCH).read_text()
    assert '.cap_codes(cap_codes)' in tb and '.kvb_codes(cap_codes)' in tb
    assert 'cap_codes=expected' not in tb and 'force ' not in tb
    assert 'WIN_STACK' not in tb  # This arithmetic fixture has no HBM aperture.
