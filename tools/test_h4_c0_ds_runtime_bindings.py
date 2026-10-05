"""Scoped protocol/typed movement tests; fixtures confer no production credit."""
import hashlib
import unittest
import numpy as np
from h4_c0_ds_runtime_bindings import TypedOperandViewsMixin,recipe,canonical,concat_rows,buffer_writers,VersionLeaseClosureMixin

class Parent:
    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        if bindings: raise ValueError('fixture parent intentionally has no fallback')
        out={};self.views[(op['pc'],owned['rank'],generation,id(out))]=out;return out

class Bridge:
    def __init__(self,p): self.p=p;self.calls=[];self.source_sha=hashlib.sha256(canonical(p.native)).hexdigest()
    def _read_words(self,version,rank,indices):
        # Witness that lease is registered BEFORE simulated addressed acquisition.
        assert any(v.get('leased_versions')==[version] for vs in self.p.views.values() for v in vs.values())
        self.calls.append(indices.copy())
        raw=self.p.storage[(version,rank)].reshape(-1).view('<u4')
        return raw[indices],self.p.locations[(version,rank)],dict(software_reverse_drained=True)

class Bound(TypedOperandViewsMixin,Parent): pass

def provider(array,spec,address='full source value reshaped to declared LOAD shape'):
    p=Bound();p.generation=1;p.views={};p.source_images={};p.published={}
    p.locations={('v',0):dict(shape=list(array.shape),dtype=array.dtype)};p.storage={('v',0):array}
    p.native=dict(templates={'t':dict(providers={'x':spec})})
    p.C0_source_views=Bridge(p);p.enable_fullgraph_typed_views(native_content_sha256=p.C0_source_views.source_sha)
    b=dict(kind='versioned_operand',version='v',native_address_view=address)
    return p,b

class SourceTests(unittest.TestCase):
    def test_reshape_acquires_producer_words_and_retains_lease(self):
        a=np.arange(4096,dtype='<f4');p,b=provider(a,dict(dtype='F32',shape=[32,128]))
        v=p._read_one(dict(pc=124,family='index_q'),dict(rank=0),'t',{'x':b},1)['x']
        np.testing.assert_array_equal(v['data'],a.reshape(32,128))
        self.assertEqual(len(p.C0_source_views.calls),32);self.assertFalse(v['data'].flags.writeable)
        self.assertEqual(v['leased_versions'],['v'])
    def test_engram_source_slice_has_no_other_words(self):
        a=np.arange(25600,dtype='<f4');p,b=provider(a,dict(dtype='F32',shape=[5120]),'flat[20480:25600]')
        v=p._read_one(dict(pc=57,family='engram_mix'),dict(rank=0),'t',{'x':b},1)['x']
        np.testing.assert_array_equal(v['data'],a[20480:])
        self.assertEqual(p.C0_source_views.calls[0][0],20480)
    def test_i64_halves_preserve_signed_and_high_bits(self):
        a=np.array([-(1<<63),0,(1<<62)+17,-1],dtype='<i8');p,b=provider(a,dict(dtype='I64',shape=[2,2]))
        out=p._read_one(dict(pc=20,family='expert_fetch'),dict(rank=0),'t',{'x':b},1)['x']['data']
        self.assertEqual(out.tobytes(),a.tobytes());self.assertEqual(p.C0_source_views.calls[0].tolist(),list(range(8)))
    def test_rejects_codec_truncation_and_unknown_slice(self):
        for spec,address in [(dict(dtype='U32',shape=[4]),'full384'),(dict(dtype='F32',shape=[3]),'full384'),(dict(dtype='F32',shape=[4]),'guess[0:4]')]:
            with self.assertRaises(ValueError):recipe(dict(kind='versioned_operand',native_address_view=address),spec,dict(shape=[4],dtype='<f4'))
    def test_failed_fragment_retains_owner_and_refuses_retry(self):
        p,b=provider(np.ones(4,dtype='<f4'),dict(dtype='F32',shape=[4]))
        p.C0_source_views._read_words=lambda *a:(_ for _ in ()).throw(ValueError('source refusal'))
        with self.assertRaises(ValueError):p._read_one(dict(pc=13,family='hc_post'),dict(rank=0),'t',{'x':b},1)
        self.assertTrue(p.views)
        with self.assertRaisesRegex(ValueError,'no retry'):p._read_one(dict(pc=13,family='hc_post'),dict(rank=0),'t',{'x':b},1)
    def test_real_sector_source_read_reverse_scoped_fixture(self):
        import tempfile
        from pathlib import Path
        from hbm_bound_event_journal_r30 import JournalBudget,BoundSectorProvider
        from hbm_provider_microvm_r21 import Storage,Tensor
        from h4_c0_ds_source_views import SourceViews
        with tempfile.TemporaryDirectory() as tmp:
            a=np.array([-(1<<63),(1<<62)+17,-1,0],dtype='<i8')
            p,b=provider(a,dict(dtype='I64',shape=[2,2]))
            p.journal_budget=JournalBudget(Path(tmp)/'journal',1<<20)
            backing=BoundSectorProvider({('DeepSeek',0):[dict(base=33554432,bytes=33554432)]},journal_budget=p.journal_budget,
                allocation_identity=dict(address_class='scoped_test_state_fragment',rank=0))
            p.state={0:backing}
            storage=Storage(backing,'DeepSeek',0,33554432,33554432);storage.pc=11;storage.epoch=1
            storage.write(Tensor('DeepSeek',0,33554432,(8,),'U32'),0,a.view('<u4'))
            p.locations['v',0].update(kind='state_fragment',pc=11,
                binding=dict(PC=11,version='v',rank=0,base=33554432,reservation_bytes=512))
            p.C0_source_views=SourceViews(p,native_content_sha256=p.fullgraph_source_sha)
            out=p._read_one(dict(pc=13,family='hc_post'),dict(rank=0),'t',{'x':b},1)['x']
            self.assertEqual(out['data'].tobytes(),a.tobytes())
            self.assertEqual(out['source_journal_spans'][0]['accepted_sectors'],1)
            self.assertTrue(out['source_journal_spans'][0]['software_reverse_drained'])
            self.assertFalse(backing.live or backing.queue or backing.calendar or backing.resident)
            self.assertTrue(p.views)  # Normal downstream release still required.
            p.journal_budget.db.close()

    def test_compound_checkpoint_cross_boundary_rows_stay_ordered(self):
        self.assertEqual(concat_rows(['wkv','wgate'],[[512,5120],[512,5120]],[501,522],dict(shape=[21,5120],dtype='F32')),
            [dict(tensor='wkv',rows=[501,512]),dict(tensor='wgate',rows=[0,10])])
        with self.assertRaises(ValueError):concat_rows(['wkv','wgate'],[[512,5120],[512,4096]],[501,522],dict(shape=[21,5120],dtype='F32'))

    def test_collective_aliases_keep_exact_source_order_and_slices(self):
        primary=dict(version='ea',native_result_binding=dict(buffer='ea',result='out'))
        a=dict(version='ea0',native_result_binding=dict(buffer='ea',result='out',flat_slice=[0,2304]))
        b=dict(version='ea1',native_result_binding=dict(buffer='ea',result='out',flat_slice=[2304,4608]))
        other=dict(version='other',native_result_binding=dict(buffer='other',result='out'))
        self.assertEqual(buffer_writers(dict(writes=[primary,a,b,other]),[primary]),[primary,a,b])
        with self.assertRaises(ValueError):buffer_writers(dict(writes=[primary]),[other])

    def test_native_mutation_refused_before_read(self):
        p,b=provider(np.ones(4,dtype='<f4'),dict(dtype='F32',shape=[4]));p.native['mutation']=1
        with self.assertRaisesRegex(ValueError,'changed'):p._read_one(dict(pc=13,family='hc_post'),dict(rank=0),'t',{'x':b},1)
        self.assertFalse(p.C0_source_views.calls)

class SpecialistLeaseTests(unittest.TestCase):
    def test_empty_additional_list_cannot_erase_primary_lease(self):
        class Legacy:
            def _read_one(self,op,owned,key,bindings,generation,collective=None):
                assert any('route' in v['leased_versions'] for vs in self.views.values() for v in vs.values())
                result={'route_weight':dict(data=np.array(1.,dtype='<f4'),leased_versions=[])}
                self.views[op['pc'],owned['rank'],generation,id(result)]=result
                return result
        class Fixed(VersionLeaseClosureMixin,Legacy):pass
        p=Fixed();p.views={};p.generation=1;p.fullgraph_source_sha='fixture';p.fullgraph_source_failed=False
        b=dict(kind='versioned_operand',version='route',additional_versions=[])
        result=p._read_one(dict(pc=23),dict(rank=0),'t',{'route_weight':b},1)
        self.assertEqual(result['route_weight']['leased_versions'],['route'])
        self.assertEqual(len(p.views),1)

if __name__=='__main__':unittest.main()
