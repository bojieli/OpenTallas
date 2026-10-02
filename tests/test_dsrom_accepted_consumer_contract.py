import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_accepted_consumer_contract as M
import dsrom_accepted_waveform_trace as C

class ConsumerContract(unittest.TestCase):
    def fixture(self):
        # Checker fixture only; no fabricated production receipt is published.
        identity=dict(phase=10,stage=0,rank=0,shard=1,key=2149580800,reset_era=1,owner=0)
        contract=dict(identity=identity,cfg_addresses=[0,1],root_row_positions=[[0,0]],writes=[dict(row=0,position=0,address=100)],
            clocks={k:['tile.clk'] for k in M.REQUIRED})
        contract['clocks']['activation_capture']=['leaf.gclk']
        events=[]
        def add(k,t,**fields):
            events.append(dict(identity,kind=k,time_ps=t,clock=contract['clocks'][k][0],
                basis='actual_VCD_pre_consumer_rising_edge',**fields))
        add('phase_accept',5)
        add('cfg_accept',10,cfg_address=0);add('cfg_accept',15,cfg_address=1)
        add('vm_request_accept',20);add('activation_capture',27)
        add('root_return_accept',50,row=0,position=0,fault=0)
        add('writer_accept',55,row=0,position=0,address=100,word=0x44000000,collision_mask=0)
        add('writer_visible',60,row=0,position=0,address=100,word=0x44000000,collision_mask=0)
        add('phase_retire',65,source_idle=1,writer_drained=1)
        return events,contract
    def test_collector_role_mapping_preserves_actual_observations(self):
        e,c=self.fixture();roles=[]
        for n,event in enumerate(e):
            kind=event['kind'];event['binding_id']=str(n)
            roles.append(dict(binding_id=str(n),raw_kind='writer_accept' if kind=='writer_visible' else kind,kind=kind))
            event['kind']=roles[-1]['raw_kind']
        normalized=list(M.normalize_events(e,roles));self.assertEqual(normalized[7]['time_ps'],60)
        self.assertEqual(normalized[7]['word'],e[7]['word']);self.assertEqual(normalized[7]['kind'],'writer_visible')
        self.assertEqual(M.check_events(normalized,c)['final_visible'],1)
        e[7]['binding_id']='foreign'
        with self.assertRaisesRegex(ValueError,'foreign consumer'):list(M.normalize_events(e,roles))
    def test_independent_consumer_clocks_and_exact_visibility(self):
        e,c=self.fixture();r=M.check_events(e,c)
        self.assertEqual(r['final_visible'],1);self.assertFalse(r['ACK_inferred']);self.assertFalse(r['hardware_qualified'])
    def test_foreign_identity_wrong_clock_and_offered_basis(self):
        for field,value,diagnostic in [('key',1,'identity'),('clock','offered.clk','clock'),('basis','offered','basis')]:
            e,c=self.fixture();e[4][field]=value
            with self.assertRaisesRegex(ValueError,diagnostic):M.check_events(e,c)
    def test_missing_duplicate_cfg_or_root(self):
        for index in [1,5]:
            e,c=self.fixture();e.insert(index,copy.deepcopy(e[index]))
            with self.assertRaisesRegex(ValueError,'duplicate'):M.check_events(e,c)
        e,c=self.fixture();e.pop(2)
        with self.assertRaisesRegex(ValueError,'coverage'):M.check_events(e,c)
    def test_write_offer_or_unsettled_readback_not_final_visibility(self):
        e,c=self.fixture();e.pop(7)
        with self.assertRaisesRegex(ValueError,'missing'):M.check_events(e,c)
        e,c=self.fixture();e[7]['time_ps']=55
        with self.assertRaisesRegex(ValueError,'settled'):M.check_events(e,c)
        e,c=self.fixture();e[7]['word']=0
        with self.assertRaisesRegex(ValueError,'differs'):M.check_events(e,c)
    def test_foreign_destination_and_extra_duplicate_writer_refused(self):
        e,c=self.fixture();e[6]['address']=101
        with self.assertRaisesRegex(ValueError,'destination'):M.check_events(e,c)
        e,c=self.fixture();e.insert(7,copy.deepcopy(e[6]))
        with self.assertRaisesRegex(ValueError,'duplicate writer'):M.check_events(e,c)
    def test_actual_vm_collision_and_absent_drain_refused(self):
        e,c=self.fixture();e[6]['collision_mask']=1
        with self.assertRaisesRegex(ValueError,'collision'):M.check_events(e,c)
        e,c=self.fixture();e[-1]['writer_drained']=0
        with self.assertRaisesRegex(ValueError,'drain'):M.check_events(e,c)
    def test_actual_pin_and_wrong_anchor(self):
        commit='d4b9a4a6966bf211df81136b3df886a980f4bd36';path='results/uarch/ds_mtp_agentic_headline_policy_20261002.json'
        b=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
        binding={'schema':'DSROM_CURRENT_CONSUMER_BINDINGS_V1','sources':[dict(commit=commit,path=path,sha256=hashlib.sha256(b).hexdigest(),anchor='AGENTIC_MEDIAN_SOURCE_PENDING')]}
        self.assertFalse(M.verify_source_bindings(ROOT,binding)['launch_admitted'])
        binding['sources'][0]['anchor']='IMAGINARY_HEADLINE_PASS'
        with self.assertRaisesRegex(ValueError,'anchor'):M.verify_source_bindings(ROOT,binding)
        binding['sources'][0]['commit']='d4b9'
        with self.assertRaisesRegex(ValueError,'full immutable'):M.verify_source_bindings(ROOT,binding)
    def test_source_expected_rows_not_recalibrated_from_trace(self):
        e,c=self.fixture();c['root_row_positions'].append([1,0]);c['writes'].append(dict(row=1,position=0,address=101))
        with self.assertRaisesRegex(ValueError,'coverage'):M.check_events(e,c)
    def test_waveform_consumers_different_clocks_and_preNBA_values(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'fixture.vcd';out=Path(td)/'events.jsonl'
            # Source-semantics parser fixture; not actual RTL execution evidence.
            p.write_text('''$timescale 1ps $end
$scope module tile $end
$var wire 1 ! clk $end
$var wire 1 " rst_n $end
$var wire 1 # take $end
$var wire 8 $ data $end
$var wire 1 % gclk $end
$upscope $end
$enddefinitions $end
#0
0!
0%
1"
1#
b00000101 $
#5
1!
b00001001 $
#7
1%
#10
0!
0%
0#
''')
            defs=[dict(id=k,kind=k,clock='tile.gclk' if k=='activation_capture' else 'tile.clk',valid='tile.take',reset_n='tile.rst_n',fields={'word':{'signal':'tile.data','width':8}}) for k in C.KINDS]
            b=dict(input_class='ACTUAL_RUNTIME_VCD',writer_sink_bound=True,whole_phase_geometry_bound=True,events=defs)
            C.record(p,b,out);e=[json.loads(x) for x in out.read_text().splitlines()]
            self.assertEqual([(x['time_ps'],x['word']) for x in e if x['kind']=='activation_capture'],[(7,9)])
            self.assertTrue(all(x['time_ps']==5 and x['word']==5 for x in e if x['kind']!='activation_capture'))

if __name__=='__main__':unittest.main()
