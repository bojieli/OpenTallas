import hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_pc10_engine_r44 as m

class Events(list):pass

def witness():
    # Digest-observer refusal tests only, not production producer data.
    w=object.__new__(m.Witness);w.failed=False;w.seen=set();w.events=Events()
    row=json.loads(m.PC10_REFERENCE.read_bytes())['expectations'][0]
    w.expected={(row['PC'],row['version'],row['rank'],row['generation'],row['field']):row}
    identity={k:row[k] for k in ('PC','version','rank','generation','home_indices')}
    return w,identity

@pytest.mark.parametrize('mutation',['payload','shape','dtype','home','key','duplicate'])
def test_pc10_changed_identity_or_bytes_preserves_refusal(mutation,monkeypatch):
    w,i=witness();a=np.zeros(8192,np.float32)
    if mutation=='shape':a=a.reshape(8,1024)
    if mutation=='dtype':a=a.astype(np.float64)
    if mutation=='home':i=dict(i,home_indices=[])
    if mutation=='key':i=dict(i,version='wrong')
    if mutation=='duplicate':w.seen.add((10,i['version'],0,1,'data'))
    # Isolate digest witness refusal; no source publication proof claimed.
    monkeypatch.setattr(m,'peer',lambda _:SimpleNamespace(publication_receipt=lambda *args:None))
    before=set(w.seen)
    with pytest.raises(ValueError,match='actual PC10 output'):w.observe(i,{'data':a},{})
    assert w.failed and w.seen==before and w.events[-1]['byte_exact'] is False
    assert w.events[-1]['reference_sha256']==m.PC10_REFERENCE_SHA


def test_exact96_independent_rows_reference_only():
    raw=m.PC10_REFERENCE.read_bytes();r=json.loads(raw)
    assert hashlib.sha256(raw).hexdigest()==m.PC10_REFERENCE_SHA
    assert len(r['expectations'])==96 and r['observes_only']
    assert all(x['shape']==[8192] and x['dtype']=='<f4' for x in r['expectations'])
