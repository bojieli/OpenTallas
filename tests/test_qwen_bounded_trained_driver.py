"""Actual driver constructor, source admission and all1737-PC raw-byte VM join."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_bounded_trained_driver as D
from qwen_hbm_complete_program import compile_program


def fixture_native(layers=36):
    c=dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,
           intermediate_size=16,vocab_size=16,num_hidden_layers=layers,rms_norm_eps=1e-6,rope_theta=1000000)
    n=D.N.compile_tiled(compile_program(c,context=32,groups=16))
    for a in n['provider_binding']['allocation']:
        for e in a['extents']:
            if e.get('role')=='software_provider_state':e['role']='software_KV_publication_and_reader_lease_state'
            e.setdefault('codec',{'test_fixture_role':e.get('role')})
    return n


def fixture_backend(tmp_path,n):
    """Offline test producer. Native execution reads only file bytes thereafter."""
    p=n['source_program'];c=p['config'];weights=D.N.TileFixtureWeights(p)
    data={};wanted=D.B.immutable_refs(n);ex=D.B.extents(n)
    def bf(value):return (np.asarray(value,np.float32).view(np.uint32)>>16).astype('<u2').tobytes()
    for key,d in p['weight_descriptors'].items():
        prefix='head'if d['layer']is None else f'L{d["layer"]}.{d["name"]}'
        code=f'Qwen.rank{d["die"]}.extent.{prefix}.codes';scale=code[:-5]+'scales'
        data[code]=weights.matrix_tile(key,0,d['rows'],0,d['K']).tobytes()
        if scale in wanted:data[scale]=bf(weights.scale_tile(key,0,d['rows']))
    for ref in wanted:
        if ref.endswith('.embedding'):
            parts=[weights.embedding_tile(token,0,c['hidden_size'])for token in range(c['vocab_size'])]
            data[ref]=b''.join(x.tobytes()for x,_ in parts)+bf([s for _,s in parts])
        elif ref.endswith('.qk_norm'):data[ref]=bf(np.ones(2*c['head_dim'],np.float32))
        elif ref.endswith('.final_norm'):data[ref]=bf(np.ones(c['hidden_size'],np.float32))
        elif ref.endswith('.rope_table'):
            rows=[np.concatenate(weights.rope_tile(pos,c['rope_theta'],0,c['head_dim']//2))for pos in range(p['context_capacity'])]
            data[ref]=np.asarray(rows,dtype='<f4').tobytes()
    images={}
    for i,ref in enumerate(sorted(wanted)):
        raw=data[ref];e=ex[ref];assert len(raw)==e['bytes']
        file=tmp_path/f'{i}.bin';file.write_bytes(raw)
        images[ref]=dict(base=e['base'],bytes=e['bytes'],codec=e['codec'],segments=[
            dict(file=file.name,start=0,bytes=len(raw),sha256=D.B.sha(file))])
    manifest=dict(schema='opentallas.Qwen.trained-byte-images.v1',complete=True,
        identity=dict(native_sha256=D.canonical_identity(n),source_sha256={},
                      checkpoint_lock_sha256=D.B.sha(D.ROOT/'compiler/models/qwen3-8b/checkpoint_source.json')),images=images)
    (tmp_path/'manifest.json').write_bytes(D.B.canonical(manifest))
    return D.B.TrainedByteBackend(tmp_path,n)


def test_ready_artifact_pins_exact_relocated_module_and_all_source():
    report=D.readiness()
    assert report['bounded_module']=='tools/h3_qwen_bounded_native.py'
    assert report['bounded_module_sha256']==D.BOUNDED_SHA256
    assert report['PCs']==1737 and report['classes']==21 and report['matrix_descriptors']==290
    assert len(report['matrix_inventory'])==290
    assert report['storage_scope']['immutable_count']==586 and report['storage_scope']['mutable_count']==146
    assert report['canonical_native_sha256']==D.CANONICAL_NATIVE_SHA256
    assert not report['full_checkpoint_execution_performed'] and report['additional_native_HBM_bytes']==0
    assert D.BOUNDED_MODULE in report['source_sha256']
    assert 'tools/qwen_bounded_trained_driver.py' in report['source_sha256']


def test_all1737_PCs_retire_with_raw_immutable_bytes_and_mutable_KV(tmp_path):
    n=fixture_native();backend=fixture_backend(tmp_path,n);machine=D.bind_runtime(n,backend)
    scope=D.storage_scope(n);seen=[];old=backend.read_tile_bytes
    def raw_read(request):
        assert request['provider_ref'] in scope['immutable_checkpoint_refs']
        assert request['provider_ref'] not in scope['mutable_runtime_refs']
        seen.append(request['provider_ref']);return old(request)
    backend.read_tile_bytes=raw_read
    pcs=[];kvpcs=[];last=[0]
    def observer(op,store):
        pcs.append(op['pc'])
        if op['opcode'] in ('KV_WRITE','KV_FENCE','KV_READ'):
            assert backend.transactions==last[0];kvpcs.append(op['pc'])
        last[0]=backend.transactions
    try:
        actual=machine.run(3,0,observer=observer)
        assert len(pcs)==1737 and pcs==[o['pc']for o in n['operations']]
        assert len(kvpcs)==216 and actual['PCs']==1737
        assert isinstance(machine.memory,D.N.BoundKVStorage)
        assert not backend.active and not machine.memory.pending and not machine.memory.leases
        assert len(machine.memory.published)==72
        assert all(machine.memory.bit(layer,rank,0) for layer in range(36)for rank in (0,1))
        assert all((machine.memory.record(layer,rank)>>88)&3==3 for layer in range(36)for rank in (0,1))
        assert seen and not set(seen)&set(scope['mutable_runtime_refs'])
        assert actual['RF_workspace_peak_vectors']<=32
        # No oracle feeds the DUT: compare only after all1737 native PCs retire.
        expected=D.N.TiledMachine(n).run(3,0)
        assert actual['next_token']==expected['next_token']
    finally:backend.close()


def test_checkpoint_manifest_cannot_own_mutable_extent(tmp_path):
    n=fixture_native(1);backend=fixture_backend(tmp_path,n)
    mutable=D.storage_scope(n)['mutable_runtime_refs'][0];backend.manifest['images'][mutable]={}
    try:
        with pytest.raises(ValueError,match='exclude mutable'):D.bind_runtime(n,backend)
    finally:backend.close()


def test_KV_operation_cannot_bind_checkpoint_provider():
    n=fixture_native(1);op=next(o for o in n['operations']if o['opcode']=='KV_READ')
    immutable=D.storage_scope(n)['immutable_checkpoint_refs'][0]
    op['provider_binding']['external_providers'][0]['provider_ref']=immutable
    with pytest.raises(ValueError,match='mutable native'):D.storage_scope(n)


def test_actual_driver_delegates_exact_module_and_admission(tmp_path,monkeypatch):
    report=dict(source_sha256={'tools/exact.py':'abc'})
    monkeypatch.setattr(D,'readiness',lambda:report)
    admission=dict(source_sha256={'tools/exact.py':'abc'});calls=[]
    monkeypatch.setattr(D.G,'validate_admission',lambda a,g:calls.append(('GO',a,g)))
    monkeypatch.setattr(D.B,'native',lambda:{'test':'native'})
    class Backend:
        def __init__(self,*args):calls.append(('backend',args))
        def close(self):calls.append(('close',))
    monkeypatch.setattr(D.B,'TrainedByteBackend',Backend)
    monkeypatch.setattr(D,'bind_runtime',lambda n,b:calls.append(('mutable_bind',n)))
    out=tmp_path/'out'
    def actual(images,path,a,go,module,token):
        path.mkdir();calls.append(('run',module,token));return {'PASS':True}
    monkeypatch.setattr(D.G,'run',actual)
    assert D.run(tmp_path/'images',out,admission,'GO-SHA',9707)=={'PASS':True}
    assert ('run',Path('tools/h3_qwen_bounded_native.py'),9707)in calls
    assert calls.index(('close',))<calls.index(('run',Path(D.BOUNDED_MODULE),9707))
    assert json.loads((out/'bounded_driver_join.json').read_text())==report


def test_missing_driver_source_pin_rejects_before_images(monkeypatch,tmp_path):
    monkeypatch.setattr(D,'readiness',lambda:dict(source_sha256={'tools/exact.py':'abc'}))
    with pytest.raises(ValueError,match='dependency pin'):
        D.run(tmp_path/'missing',tmp_path/'out',dict(source_sha256={}), 'GO')
