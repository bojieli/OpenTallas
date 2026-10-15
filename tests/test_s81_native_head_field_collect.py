"""Native terminal must never receive unproduced or source-mixed head roots."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest

P=Path(__file__).resolve().parents[1]/'tools/s81_ftok/collect_native_head_field.py'
spec=importlib.util.spec_from_file_location('head_collect',P)
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)


def ranks(tmp):
    ds=[]
    for r in range(4):
        d=tmp/f'r{r}';d.mkdir();ds.append(d)
        rec=dict(bad=0,mutant=False,groups=253,xf_sha256='native-xf',source={'RTL':'same'},native_xf_chained=True,b_root_format='padded',static_group_cycles=[8414])
        (d/'record.json').write_text(json.dumps(rec))
        (d/'groups.json').write_text(json.dumps([dict(rank=r,bad=0)]*253))
        np.savez(d/f'rtl_rank{r}.npz',roots=np.full((32320,2),r,np.uint32),logits=np.full(32320,r,np.uint32),seen=np.ones(32320,bool))
    return ds


def test_all_rows_copied_and_native_token_remains_unqualified(tmp_path):
    ds=ranks(tmp_path); out=tmp_path/'out';rec=C.collect(ds,out)
    assert rec['rows']==129280 and rec['native_xf_chained']
    assert not rec['full_native_token_qualified']
    assert (out/'roots_r3.mem').read_text().splitlines()==['0000000300000003']*32320


def test_missing_hardware_row_rejected(tmp_path):
    ds=ranks(tmp_path);p=ds[2]/'rtl_rank2.npz'; z=dict(np.load(p));z['seen'][256]=False;np.savez(p,**z)
    with pytest.raises(ValueError,match='missing RTL rows'):C.collect(ds,tmp_path/'out')
    assert not (tmp_path/'out/field.provenance.json').exists()


def test_different_hardware_source_rejected(tmp_path):
    ds=ranks(tmp_path);p=ds[3]/'record.json';z=json.loads(p.read_text());z['source']={'RTL':'different'};p.write_text(json.dumps(z))
    with pytest.raises(ValueError,match='sources, schedule or input differ'):C.collect(ds,tmp_path/'out')
    assert not (tmp_path/'out/field.provenance.json').exists()
