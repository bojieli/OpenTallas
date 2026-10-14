"""Mechanism tests only; fixtures are not an allocation or native execution."""
import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from native_stage_lowering import lower


class Lowering(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.binding=self.root/'b';self.binding.mkdir()
        (self.root/'endpoint.sv').write_text('module endpoint; endmodule\n')
        sm={'PHW_required_by_stage':[9,9],'rank_dies':[{'stage':s,'rank':r,'die_id':4*s+r} for s in range(2) for r in range(4)]}
        (self.binding/'stage_map.json').write_text(json.dumps(sm))
        (self.binding/'inventory.json').write_text(json.dumps({'stages':2,'TP':4,'layer_dies':8}))
        with gzip.open(self.binding/'matrix_map.jsonl.gz','wt') as f:f.write(json.dumps({'layer':0,'alias':'m','stage':0})+'\n')
        pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.binding.iterdir()}
        endpoint_sha=hashlib.sha256((self.root/'endpoint.sv').read_bytes()).hexdigest()
        def job(ident,engine,arg,**more):
            return dict(source_id=ident,engine=engine,arg=arg,vm_inputs=[],endpoint_codec='ot_s81_hc_cseq.arg24.v1' if engine==2 else 'field_phase',endpoint_source='endpoint.sv',endpoint_source_sha256=endpoint_sha,**more)
        self.req={'allocation_sha256':pins,'candidate_only':True,'hc_hwords':640,'source_jobs':['field','load','store'],
                  'stages':[{'stage':0,'boot':[{'engine':2,'arg':5<<20}],
                      'operations':[job('load',2,0,h_region_base=0,h_region_rows=640),
                          job('field',0,3,field_phase=3,matrices=[[0,'m']]),
                          job('store',2,(1<<20)|2048,h_region_base=2048,h_region_rows=640)]},
                     {'stage':1,'boot':[],'operations':[]}]}
    def tearDown(self):self.tmp.cleanup()
    def compile(self):return lower(self.req,self.binding,self.root)
    def test_real_slot_flag_and_distinct_boot(self):
        r=self.compile();p=r['programs'][0]
        self.assertEqual(p['token'],[0x2800000,3,0x2900800]);self.assertEqual(p['boot'],[0x2500000])
        self.assertEqual(r['transfer_descriptor_counts'],{'hload':1,'hstore':1})
        self.assertIsNone(r['native_executed_transfer_count']);self.assertFalse(r['dispatch_eligible'])
    def add_post(self):
        ops=self.req['stages'][0]['operations']
        post=dict(ops[0],source_id='post',arg=3<<20,vm_inputs=[])
        self.req['source_jobs'].append('post')
        field=ops[1]
        field['vm_inputs']=[{'producer_source_id':'post','materializer_source_id':'store','base':2048,'rows':640}]
        self.req['stages'][0]['operations']=[ops[0],post,ops[2],field]
    def test_post_spill_before_vm_reader(self):
        self.add_post();self.assertEqual(self.compile()['transfer_descriptor_counts']['hstore'],1)
    def test_post_vm_without_materializer_refused(self):
        self.add_post();self.req['stages'][0]['operations'][-1]['vm_inputs'][0]['materializer_source_id']='missing'
        with self.assertRaisesRegex(ValueError,'no actual materialization'):self.compile()
    def test_late_post_spill_refused(self):
        self.add_post();ops=self.req['stages'][0]['operations'];ops[2],ops[3]=ops[3],ops[2]
        with self.assertRaisesRegex(ValueError,'ordered H_STORE'):self.compile()
    def test_capture_opcode_is_not_a_cseq_load(self):
        self.req['stages'][0]['operations'][0]['endpoint_codec']='ot_dsrom_hc_mean_capture'
        with self.assertRaisesRegex(ValueError,'explicit cseq codec'):self.compile()
    def test_missing_real_stage_refused(self):
        self.req['stages'].pop()
        with self.assertRaisesRegex(ValueError,'every real stage'):self.compile()
    def test_matrix_stage_swap_refused(self):
        self.req['stages'][0]['stage']=1;self.req['stages'][1]['stage']=0
        with self.assertRaisesRegex(ValueError,'different physical stage'):self.compile()
    def test_gain_cannot_delay_landing(self):
        self.req['stages'][0]['operations'][0]['arg']=5<<20
        with self.assertRaisesRegex(ValueError,'GAIN reload'):self.compile()
    def test_changed_endpoint_pin_refused(self):
        (self.root/'endpoint.sv').write_text('module changed; endmodule\n')
        with self.assertRaisesRegex(ValueError,'source contract changed'):self.compile()
    def test_missing_source_job_refused(self):
        self.req['source_jobs'].append('omitted')
        with self.assertRaisesRegex(ValueError,'source jobs omitted'):self.compile()
    def test_slot_vm_overflow_refused(self):
        self.req['stages'][0]['operations'][0].update(arg=16000,h_region_base=16000)
        with self.assertRaisesRegex(ValueError,'two-slot H region'):self.compile()


if __name__=='__main__':unittest.main()
