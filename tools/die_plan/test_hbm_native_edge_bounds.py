import copy,json,tempfile,unittest
from pathlib import Path
import hbm_native_edge_bounds as B

class BoundsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        f=self.root/'pins.json';f.write_text(json.dumps([dict(name='p',x=0,y=0)]));self.sha=B.digest(f)
        self.plan=dict(partitions=[dict(name='P',type='T',origin_um=[0,0])],partition_types={'T':dict(outline_um=[2000,1000],hard_cores=[dict(inst='a',module='a',origin_um=[0,0],outline_um=[10,10],pins_file='pins.json'),dict(inst='z',module='z',origin_um=[810,0],outline_um=[10,10],pins_file='pins.json')])})
        self.manifest={'A':dict(master='a',ports={'o':dict(direction='output',segments=[['n','n',0,0]])}),'Z':dict(master='z',ports={'i':dict(direction='input',segments=[['n','n',0,0]])})}
        def pin(core):return dict(partition='P',type='T',core=core,expected_module=core,pin='p',pins_sha256=self.sha)
        self.edge=dict(id='e',bundle='bus',bundle_bit=0,kind='signal',epoch_binding='actual-ledger-row-0',source_native=dict(instance='A',expected_master='a',port='o',bit=0),sink_native=dict(instance='Z',expected_master='z',port='i',bit=0),history=[],source_pin=pin('a'),sink_pin=pin('z'))
        self.history={'transport_instances':{}}
        self.ledger=dict(authority='ACTUAL_NATIVE_BIT_BINDING',bundles={'bus':dict(width=1,kind='signal')},edges=[self.edge])
    def run_bounds(self):return B.analyze(self.plan,self.root,self.manifest,self.history,self.ledger)
    def test_true_per_bit_bound_810_needs_one_stage(self):
        r=self.run_bounds();self.assertEqual(r['bundles'][0]['minimum_extra_uniform_stages'],1)
    def test_actual_history_preserved_and_mismatch_rejected(self):
        self.manifest['R']=dict(master='relay',ports={'i':dict(direction='input',segments=[['n','n',0,0]]),'o':dict(direction='output',segments=[['n','r',0,0]])})
        self.manifest['Z']['ports']['i']['segments']=[['n','r',0,0]]
        self.history['transport_instances']['R']=dict(master='relay',stages=2,rule={'map':{'o':'i'}})
        self.edge['history']=[dict(instance='R',input_port='i',output_port='o',input_bit=0,output_bit=0)]
        r=self.run_bounds();self.assertEqual(r['bundles'][0]['minimum_extra_uniform_stages'],0);self.assertEqual(r['rows'][0]['actual_transport_stages'],2)
        self.manifest['R']['ports']['i']['segments']=[['n','wrong',0,0]]
        self.assertEqual(self.run_bounds()['failed_edges'],1)
    def test_incomplete_bus_cannot_claim_uniform_stage_count(self):
        self.ledger['bundles']['bus']['width']=2;r=self.run_bounds();self.assertEqual(r['verdict'],'FAIL');self.assertNotIn('minimum_extra_uniform_stages',r['bundles'][0])
    def test_stale_physical_pins_fail(self):
        (self.root/'pins.json').write_text('[]');self.assertEqual(self.run_bounds()['failed_edges'],1)
    def test_partition_mirroring_applied_before_global_distance(self):
        self.plan['partitions'].append(dict(name='Q',type='T',origin_um=[3000,0],orient='MY'));self.edge['sink_pin']['partition']='Q'
        r=self.run_bounds();self.assertEqual(r['rows'][0]['sink_um'],[4190,0]);self.assertEqual(r['bundles'][0]['minimum_extra_uniform_stages'],10)
    def test_clock_geometry_cannot_claim_signal_cycles(self):
        self.edge['kind']='clock';self.ledger['bundles']['bus']['kind']='clock';r=self.run_bounds();self.assertNotIn('minimum_extra_uniform_stages',r['bundles'][0]);self.assertNotIn('extra_signal_stage_lower_bound',r['rows'][0])
    def test_ambiguous_physical_access_is_not_silently_chosen(self):
        f=self.root/'pins.json';f.write_text(json.dumps([dict(name='p',x=0,y=0),dict(name='p',x=2,y=0)]))
        for side in ['source_pin','sink_pin']:self.edge[side]['pins_sha256']=B.digest(f)
        self.assertEqual(self.run_bounds()['failed_edges'],1)
    def test_missing_epoch_binding_fails(self):
        self.edge['epoch_binding']='';self.assertEqual(self.run_bounds()['failed_edges'],1)
if __name__=='__main__':unittest.main()
