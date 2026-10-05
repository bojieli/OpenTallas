import collections,gzip,hashlib,json,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from hbm_bound_event_journal_r30 import JournalBudget,BoundSectorProvider,DiskEvents
from hbm_provider_microvm_r21 import SectorProvider,Storage,Tensor,Identity
import h3_ds_checkpoint_provider_r30 as P
import ds_hbm_finite_state_homes_r30 as H
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002'
def test_journal_exact_events_and_identity_digest_equal_original(tmp_path):
    ext={('DeepSeek',0):[dict(base=0,bytes=512)]};old=SectorProvider(ext);new=BoundSectorProvider(ext,journal_budget=JournalBudget(tmp_path,16<<20))
    for p in [old,new]:
        s=Storage(p,'DeepSeek',0,0,512);t=Tensor('DeepSeek',0,0,(128,),'U32');s.write(t,0,np.arange(128,dtype=np.uint32));assert np.array_equal(s.read(t,np.arange(128)),np.arange(128,dtype=np.uint32))
    assert list(new.events)==old.events
    dig=hashlib.sha256()
    for e in old.events:
        raw=json.dumps(e,sort_keys=True,separators=(',',':')).encode();dig.update(len(raw).to_bytes(8,'little')+raw)
    assert new.events.summary()['framed_event_SHA256']==dig.hexdigest()
    assert not isinstance(new.events,list) and isinstance(next(iter(new.backing.values())),bytearray)
def test_finite_journal_rejects_before_new_credit_and_preserves_debt(tmp_path):
    p=BoundSectorProvider({('DeepSeek',0):[dict(base=0,bytes=32)]},journal_budget=JournalBudget(tmp_path,131072))
    with pytest.raises(BufferError):p.submit(Identity('DeepSeek',0,1,0,1,0),True,bytes(32))
    assert not p.live and not p.queue
    # After actual acceptance a host budget failure never grants owner credit.
    q=BoundSectorProvider({('DeepSeek',0):[dict(base=0,bytes=32)]},journal_budget=JournalBudget(tmp_path/'second',1<<20));t=q.submit(Identity('DeepSeek',0,1,0,1,0),True,bytes(32));q.events.budget.cap=q.events.budget.used
    with pytest.raises(BufferError):q.step()
    assert q.live[t.tag] is t and t.state!='released'
def test_exact_catalog_56_missing_writes_disjoint_aw27_capacity():
    d=json.loads((D/'finite_state_homes.json').read_bytes());assert len({(r['PC'],r['version']) for r in d['rows']})==56 and len(d['rows'])==4616
    for rank in range(96):
        rows=sorted([r for r in d['rows'] if r['rank']==rank],key=lambda r:r['base']);assert all(r['dtype']=='F32' for r in rows)
        assert all(a['base']+a['reservation_bytes']<=b['base'] for a,b in zip(rows,rows[1:]));assert rows[-1]['base']+rows[-1]['reservation_bytes']<=1<<26
    assert d['capacity_charged_bytes_all96_ranks']==96*(32<<20)
def test_actual_checkpoint_state_fragment_transport_and_no_history_substitution(tmp_path):
    m=dict(json.loads((D/'checkpoint_input_manifest.json').read_bytes()),journal_root=str(tmp_path),journal_capacity_bytes=512<<20)
    b=next(r for r in json.loads((D/'finite_state_homes.json').read_bytes())['rows'] if r['PC']==5 and r['rank']==0)
    home=dict(version=b['version'],rank_group=[0],home={'class':'HBM_NATIVE_STATE'},binding=b);p=P.create_provider(m,{}, {},[home])
    # Real checkpoint tensor bytes test address transport, not computed KV data.
    data,dt=p.checkpoint.tensor('embed.weight',rows=[0,128],cols=[0,512]);assert dt=='BF16' and list(data.shape)==b['shape']
    identity=dict(PC=5,version=b['version'],rank=0,generation=1,home_indices=[0]);r=p.publish(identity,{'data':data},{'result':b['source_result']})
    assert [e['event'] for e in r['events']]==['software_backing_visible','consumer_accept','validated_reverse_grant'];assert np.array_equal(p.restore(b['version'],0),data)
    assert not p.state[0].live;assert len(p.state[0].events)>1000
    assert p.workspace(0)['base']==64<<20
    with pytest.raises(KeyError):p.restore('missing.retained.history',0)
    p.release_version(b['version'],1)
    with pytest.raises(KeyError):p.restore(b['version'],0)
