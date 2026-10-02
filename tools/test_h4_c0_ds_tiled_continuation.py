"""Actual provider storage/native arithmetic controls, not trained outputs."""
import gzip, hashlib, importlib.util, json, os, pathlib, sys, tempfile, unittest
from unittest.mock import patch
import numpy as np
from h4_c0_ds_tiled_continuation import TiledContinuation, compose_r36
from h4_c0_group_operand_tiles import GroupOperandTiles, NATIVE
from h3_ds_checkpoint_provider_r30 import Provider, JournalBudget, BoundSectorProvider, Storage, Tensor, RF_BYTES
sys.dont_write_bytecode=True
sys.path.append('/home/ubuntu/OpenTallas/tools')
from h3_ds_checkpoint_provider_r34 import Provider as R34
from h3_ds_query_provider_r36 import SizedRF

class ContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=pathlib.Path('/tmp/kepler-ds-r34-provider-joined-sealed/native.json.gz').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=NATIVE:raise ValueError('exact native artifact')
        cls.native=json.loads(gzip.decompress(raw));cls.plan=GroupOperandTiles()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.budget=JournalBudget(pathlib.Path(self.tmp.name)/'journal',1<<30)
        actual=compose_r36(R34,base_sha256='9d47acf6f44481cf15458e8162118ec53395a03b3aa1d5242c1d1423e7d8b014')
        self.p=actual.__new__(actual)
        self.p.__dict__.update(native=self.native,generation=1,locations={},homes=[],rf={},state={},views={},published={},seq=0,trace=[],journal_budget=self.budget,history_view_leases={},query_visible={},query_homes={})
        self.p.rf=SizedRF({})
        self.pc=next(iter(self.plan.parents));parent=self.plan.parents[self.pc]
        self.version=parent['provider_bindings'][parent['new_template']]['parts']['version']
        self.writer=parent['writes'][0];self.data=np.random.default_rng(42).standard_normal((8,8,1024)).astype(np.float32)
        # Actual addressed state backing, deliberately distinct from published
        # cache. Payloads are clearly labelled seeded protocol controls.
        for rank in range(64):
            group,j=divmod(rank,8);engine=BoundSectorProvider({('DeepSeek',rank):[dict(base=33554432,bytes=33554432)]},journal_budget=self.budget)
            self.p.state[rank]=engine;store=Storage(engine,'DeepSeek',rank,33554432,33554432);store.pc=self.pc-1;store.epoch=1
            tensor=Tensor('DeepSeek',rank,33554432,(1024,),'U32');words=self.data[j,group].view(np.uint32)
            for first in range(0,1024,128):store.write(tensor,first,words[first:first+128])
            binding=dict(PC=self.pc-1,version=self.version,rank=rank,base=33554432,reservation_bytes=4096)
            self.p.locations[self.version,rank]=dict(kind='state_fragment',shape=[1024],dtype='float32',pc=self.pc-1,binding=binding)
        indices=[]
        for sm in range(32):
            indices.append(len(self.p.homes));self.p.homes.append(dict(version=self.writer['version'],rank_group=[0],SM=sm,partition='linear',word_count=256,home=dict(class_='RF',slot_first=32,vectors=2)))
            self.p.homes[-1]['home']['class']='RF'
        self.identity=dict(PC=self.pc,rank=0,generation=1,version=self.writer['version'],home_indices=indices)
        self.run=TiledContinuation(self.p,native_artifact_path='/tmp/kepler-ds-r34-provider-joined-sealed/native.json.gz')
    def tearDown(self):
        self.budget.db.close();self.tmp.cleanup()
    def test_actual64_tile_run_and_mirrored_publication(self):
        record=self.run.run(self.pc,0,generation=1,identity=self.identity,source_store_view=self.writer['native_result_binding'])
        a=self.data;f=((a[0]+a[1])+(a[2]+a[3]))+((a[4]+a[5])+(a[6]+a[7]));u=f.view(np.uint32)
        expected=((u+np.uint32(32767)+((u>>16)&np.uint32(1)))&np.uint32(0xffff0000)).reshape(-1)
        np.testing.assert_array_equal(self.p.published[self.writer['version'],0].view(np.uint32),expected)
        self.assertEqual(len(record['tiles']),64);self.assertEqual(sum(len(t['source_reads']) for t in record['tiles']),512)
        self.assertFalse(self.p._leased(self.version));self.assertEqual(record['scratch_data_bound_bytes'],41472)
        self.assertFalse(record['full_token_qualified']);self.assertEqual(record['production_calls_closed'],0)
        with self.assertRaisesRegex(ValueError,'duplicate'):self.run.run(self.pc,0,generation=1,identity=self.identity,source_store_view=self.writer['native_result_binding'])
        evidence=os.environ.get('H4_C0_CONTINUATION_EVIDENCE')
        if evidence:
            out=pathlib.Path(evidence);out.mkdir(parents=True,exist_ok=False);self.budget.db.commit()
            raw=self.budget.path.read_bytes();(out/'events.sqlite.gz').write_bytes(gzip.compress(raw,mtime=0))
            record['scope']='seeded protocol source bytes, actual native/provider software execution; not released compressor output'
            record['journal_uncompressed_sha256']=hashlib.sha256(raw).hexdigest()
            for tile in record['tiles']:
                for receipt in tile['source_reads']:receipt['journal_path']='events.sqlite.gz'
            record['result_journal']['path']='events.sqlite.gz'
            (out/'execution.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    def test_missing_backing_retains_lease_and_no_publication(self):
        del self.p.locations[self.version,7]
        with self.assertRaisesRegex(ValueError,'producer backing'):self.run.run(self.pc,0,generation=1,identity=self.identity,source_store_view=self.writer['native_result_binding'])
        self.assertTrue(self.p._leased(self.version));self.assertNotIn((self.writer['version'],0),self.p.published)
        with self.assertRaisesRegex(ValueError,'failed'):self.run.run(self.pc,0,generation=1,identity=self.identity,source_store_view=self.writer['native_result_binding'])
    def test_stale_identity_refuses_before_read(self):
        before=self.budget.used
        with self.assertRaisesRegex(ValueError,'destination writer'):self.run.run(self.pc,0,generation=1,identity=dict(self.identity,generation=2),source_store_view=self.writer['native_result_binding'])
        self.assertEqual(self.budget.used,before);self.assertFalse(self.p.views)

class R36CompositionTests(unittest.TestCase):
    def test_actual_compound_query_and_history_controls_on_composed_class(self):
        # Reuse Kepler's immutable actual-writer/native-consumer gates, changing
        # only the opt-in class composition. Do not create a second provider ABI.
        path=pathlib.Path('/home/ubuntu/OpenTallas/tests/test_ds_hbm_history_provider_r36.py')
        if hashlib.sha256(path.read_bytes()).hexdigest()!='b8b2d81d8d3b13d2db0383146012334324ba7d2c6274a9e0a19bb31a9c80ee7e':raise ValueError('immutable r36 gate source')
        spec=importlib.util.spec_from_file_location('retained_r36_tests',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        import h3_ds_query_provider_r36 as query
        import h3_ds_history_provider_r36 as history
        actual=compose_r36(R34,base_sha256='9d47acf6f44481cf15458e8162118ec53395a03b3aa1d5242c1d1423e7d8b014')
        def create(manifest,native,dispatch,homes):
            if 'query_field_homes' not in manifest:
                manifest=dict(manifest,query_field_homes=json.loads(gzip.decompress((module.D/'query_field_homes.json.gz').read_bytes())))
            p=actual(manifest,native,dispatch,homes)
            p.enable_source_views(hashlib.sha256(__import__('h4_c0_ds_source_views').canonical(native)).hexdigest())
            return p
        with tempfile.TemporaryDirectory() as tmp, patch.object(query,'create_provider',create), patch.object(history,'create_provider',create):
            module.test_actual_compound_query_writes_and_signed_consumer_read(pathlib.Path(tmp)/'query')
            module.test_actual_writer_receipts_to_selectedKV_native_consumer(pathlib.Path(tmp)/'history')

if __name__=='__main__':unittest.main()
