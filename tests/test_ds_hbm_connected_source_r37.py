import copy,gzip,hashlib,json,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from ds_hbm_source_merge_r37 import SourceMergeMixin,merge_plan
from h3_ds_connected_provider_r37 import composed_class,peer
from h3_ds_query_provider_r36 import QueryMixin
from h3_ds_history_provider_r36 import HistoryMixin
from ds_hbm_attention_views_r37 import AttentionViewsMixin
from hbm_bound_event_journal_r30 import BoundSectorProvider,JournalBudget
D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002'
def native():return json.loads(gzip.decompress((D/'inputs/source_join_projection.json.gz').read_bytes()))

def test_connected_MRO_preserves_query_codec_and_peer_source():
    cls=composed_class();m=cls.__mro__
    assert m.index(AttentionViewsMixin)<m.index(SourceMergeMixin)<m.index(QueryMixin)<m.index(HistoryMixin)
    assert any('/inputs/h4_c0_ds_source_views.py' in getattr(c._read_one,'__code__',None).co_filename for c in m if hasattr(c,'_read_one'))

def test_all20_merge_plans_exact_without_padding():
    n=native();plans=json.loads(gzip.decompress((D/'ordered_merge_plans.json.gz').read_bytes()))
    assert len(plans)==20
    for r in plans:
        o=n['instructions'][r['PC']];k=o['rank_bindings'][0]['template'];name=r['name']
        assert merge_plan(n,o,name,o['provider_bindings'][k][name],n['templates'][k]['providers'][name])==r['plan']
    r=next(r for r in plans if r['PC']==1116 and r['name']=='scores')
    assert r['plan']['version']=='DeepSeek.1115.cand_v.1631' and r['plan']['output_shape']==[131072]
    assert sum(row['shape'][0] for row in r['plan']['ranks'])==131072
    o=n['instructions'][1116];k=o['rank_bindings'][0]['template'];bad=dict(n['templates'][k]['providers']['scores'],shape=[131073])
    with pytest.raises(ValueError):merge_plan(n,o,'scores',o['provider_bindings'][k]['scores'],bad)

class ControlBase:
    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        assert not bindings
        result={};self.views[op['pc'],owned['rank'],generation,id(result)]=result;return result
class Control(SourceMergeMixin,ControlBase):pass

def test_actual_addressed96rank_merge_protocol_no_numeric_kernel(tmp_path):
    n=native();op=next(o for o in n['instructions'] if o.get('family')=='topk_merge' and o['source_op'].get('what')=='argmax');rb=op['rank_bindings'][0];k=rb['template'];bs=op['provider_bindings'][k];specs=n['templates'][k]['providers']
    p=Control();p.native=n;p.generation=1;p.locations={};p.state={};p.rf={};p.homes=[];p.views={};p.journal_budget=JournalBudget(tmp_path/'actual-journal',192*65536+131072)
    expected={};version_for={}
    for field in ('scores','ids'):
        plan=merge_plan(n,op,field,bs[field],specs[field]);parts=[];version_for[field]=plan['version']
        for row in plan['ranks']:
            rank=row['rank'];base=33554432+(0 if field=='scores' else 512);count=row['shape'][0]
            # Explicit labelled protocol controls, not checkpoint numerical data.
            a=np.full(count,rank,np.float32 if field=='scores' else np.int64);parts.append(a)
            if rank not in p.state:p.state[rank]=BoundSectorProvider({('DeepSeek',rank):[dict(base=33554432,bytes=33554432)]},journal_budget=p.journal_budget)
            raw=a.tobytes();p.state[rank].seed('DeepSeek',rank,base,raw+bytes((-len(raw))%32))
            binding=dict(PC=plan['producer_PC'],version=plan['version'],rank=rank,base=base,reservation_bytes=512)
            p.locations[plan['version'],rank]=dict(kind='state_fragment',shape=row['shape'],dtype=a.dtype,pc=plan['producer_PC'],binding=binding)
        expected[field]=np.concatenate(parts)
    S=peer('h4_c0_ds_source_views');p.C0_source_views=S.SourceViews(p,native_content_sha256=hashlib.sha256(S.canonical(n)).hexdigest())
    result=p._read_one(op,rb,k,bs,1)
    for field in ('scores','ids'):
        assert np.array_equal(result[field]['data'],expected[field]) and result[field]['provenance_certified']
        assert len(result[field]['source_ranks'])==96
        assert len(result[field]['source_journal_spans'])==96
    assert sum(len(e.events) for e in p.state.values())>0
    for e in p.state.values():assert not e.live and not e.queue;e.events.flush()
    p.C0_source_views.receipts.flush()

def test_source_declared_zero_is_typed_initialization_not_aux_image():
    n=native();op=n['instructions'][23];rb=op['rank_bindings'][0];k=rb['template'];b=op['provider_bindings'][k]['ea_old']
    p=Control();p.native=n;p.generation=1;p.views={}
    result=p._read_one(op,rb,k,{'ea_old':b},1)
    assert result['ea_old']['data'].dtype==np.float32 and result['ea_old']['data'].shape==(16128,)
    assert result['ea_old']['initialization_bytes']==64512
    with pytest.raises(ValueError):p._read_one(op,rb,k,{'ea_old':dict(b,new_version='wrong')},1)

def test_attention_wrong_location_refuses_before_source_IO():
    class Base:
        def _read_one(self,*a,**k):raise AssertionError('base/IO must not run')
    class Provider(AttentionViewsMixin,Base):pass
    n=native();op=n['instructions'][8];rb=op['rank_bindings'][0];k=rb['template'];p=Provider();p.native=n;p.generation=1;p.locations={}
    with pytest.raises(ValueError):p._read_one(op,rb,k,{'q_own':op['provider_bindings'][k]['q_own']},1)

def test_full_native_factory_refuses_without_input_GO_before_payload_IO():
    from h3_ds_connected_provider_r37 import create_provider
    with pytest.raises(ValueError,match='input GO absent'):create_provider({},None,None,None)

def test_actual_compressor_query_publication_types_all1552():
    rows=json.loads(gzip.decompress((D/'native_compressor_query_publications.json.gz').read_bytes()))
    assert len(rows)==1552
    comp=[r for r in rows if r['family']=='compressor'];assert len(comp)==16 and len({r['PC'] for r in comp})==4
    for r in comp:
        shape=[512] if '.compressed.L' in r['version'] or '.new_ckv.' in r['version'] else [128]
        assert next(iter(r['source_native_outputs'].values()))['shape']==shape
        if r['producer_extent'] is not None:assert r['producer_extent']['append_global_group']==r['source_op']['group']
    query=[r for r in rows if r['family']=='index_q' and r['source_result_binding']['result']=='iqf'];assert len(query)==8*96
    for r in query:
        assert r['source_native_outputs']['query_codes']==dict(shape=[32,64],dtype='U32',bytes=8192)
        assert r['source_native_outputs']['query_exp']==dict(shape=[32,4],dtype='U32',bytes=512)

def test_exact_dewey40_group_overlay_bound_no_execution_credit():
    rows=json.loads(gzip.decompress((D/'inputs/operand_span_overlay.json.gz').read_bytes()))
    assert len(rows)==40
    for r in rows:
        assert len(r['tiles'])==64
        for tile in r['tiles']:
            assert len(tile['source_spans'])==8
            assert [s['source_rank'] for s in tile['source_spans']]==list(range(tile['group']*8,tile['group']*8+8))
            assert {s['words'] for s in tile['source_spans']}=={128}
    manifest=json.loads((D/'inputs/group_tile_manifest.json').read_bytes())
    assert manifest['actual_parent_movement_journals'] is None and not manifest['hardware_admitted']

def test_independent_buffers_PC4_source_contracts_exact():
    from ds_hbm_collective_continuations_r37 import continuation_contract
    n=native();o=n['instructions'][4];f=peer('h4_c0_producer_extents').collective_contract
    a,b=o['rank_bindings'][0]['buffer_programs']
    qa=continuation_contract(n,4,a,n['source_native_sha256'],f)
    kv=continuation_contract(n,4,b,n['source_native_sha256'],f)
    assert qa['buffer']=='qa' and qa['shape']==[96,1280]
    assert kv['buffer']=='kvraw' and kv['shape']==[96,512]
    assert qa['version']!=kv['version']
    with pytest.raises(ValueError):continuation_contract(n,4,dict(a,read_version=b['read_version']),n['source_native_sha256'],f)

def test_all264_buffers_structural_binding_and_engram_waits_for_real_WRs():
    from ds_hbm_collective_continuations_r37 import continuation_contract
    n=native();f=peer('h4_c0_producer_extents').collective_contract;ok=0;wait=[]
    for o in n['instructions']:
        if o.get('family')!='all_gather':continue
        for c in o['rank_bindings'][0]['buffer_programs']:
            if o['native_outer_loops']['all_gather_buffers']==['eg_rows']:
                with pytest.raises(ValueError,match='actual accepted Engram ownership'):continuation_contract(n,o['pc'],c,n['source_native_sha256'],f)
                wait.append(o['pc'])
            else:
                contract=continuation_contract(n,o['pc'],c,n['source_native_sha256'],f)
                assert contract['version']==c['read_version'] and contract['shape']==[96,c['elements']];ok+=1
    assert ok==262 and wait==[54,768]
