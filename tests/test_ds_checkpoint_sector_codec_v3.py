"""Bounded metadata and byte-validity checks for actual sector serialization."""
import io
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_producer_checkpoint_resume_v3 as C


def encode(values,extent=4096):
    port=SimpleNamespace(backing=values,extents={('DeepSeek',0):[{'base':0,'bytes':extent}]})
    writer=C.Writer.__new__(C.Writer)
    writer.f=io.BytesIO();writer.bytes=writer.arrays=writer.array_temporary_bytes=0
    tree=writer.tree(C.SectorBacking(port))
    return tree,writer.f.getvalue()


def test_actual_validity_and_sector_bytes_roundtrip():
    values={('DeepSeek',0,0):list(range(32)),('DeepSeek',0,1):[None]*16+list(range(16))}
    tree,payload=encode(values)
    assert len(payload)==2*46
    assert {k:list(v) for k,v in C.read_tree(tree,payload).items()}==values


def test_sector_metadata_does_not_expand_per_sector():
    small,_=encode({('DeepSeek',0,0):[1]*32})
    large,payload=encode({('DeepSeek',0,n):[n%256]*32 for n in range(128)})
    assert len(payload)==128*46
    assert len(C.canonical(large))-len(C.canonical(small))<8
    assert C.deep_metadata_bytes(large)==C.deep_metadata_bytes(small)


def test_invalid_extent_duplicate_and_index_are_rejected():
    with pytest.raises(ValueError,match='extent'):encode({('DeepSeek',0,128):[0]*32})
    tree,raw=encode({('DeepSeek',0,0):[0]*32})
    tree['sector_backing']['count']=2
    with pytest.raises(ValueError,match='duplicate'):C.read_tree(tree,raw+raw)
    tree['sector_backing']['count']=1
    bad=C.SECTOR_RECORD.pack(1,0,0,b'\0'*32)
    with pytest.raises(ValueError,match='index'):C.read_tree(tree,bad)


def test_noncontiguous_array_temporary_is_priced():
    writer=C.Writer.__new__(C.Writer)
    writer.f=io.BytesIO();writer.bytes=writer.arrays=writer.array_temporary_bytes=0
    a=np.arange(32,dtype=np.float32).reshape(4,8)[:,::2]
    writer.tree(a)
    assert writer.array_temporary_bytes==a.nbytes
