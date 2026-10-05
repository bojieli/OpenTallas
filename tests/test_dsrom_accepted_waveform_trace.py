import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_accepted_waveform_trace as M

class WaveformExtraction(unittest.TestCase):
    def setup_fixture(self,td):
        # Parser control ONLY; this waveform is not actual DUT qualification evidence.
        p=Path(td)/'fixture.vcd'
        p.write_text('''$timescale 1ps $end
$scope module sink $end
$var wire 1 ! clk $end
$var wire 1 " rst_n $end
$var wire 1 # valid $end
$var wire 8 $ data $end
$upscope $end
$enddefinitions $end
#0
0!
1"
1#
b00000101 $
#5
1!
b00001001 $
#10
0!
0#
#15
1!
''')
        b={'input_class':'ACTUAL_RUNTIME_VCD','writer_sink_bound':True,'whole_phase_geometry_bound':True,'events':[{'id':k,'kind':k,'clock':'sink.clk','valid':'sink.valid','reset_n':'sink.rst_n','fields':{'data':{'signal':'sink.data','width':8}}} for k in sorted(M.KINDS)]}
        return p,b,Path(td)/'events.jsonl'
    def test_actual_preedge_value_not_NBA_value(self):
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);r=M.record(p,b,out);events=[json.loads(x) for x in out.read_text().splitlines()]
            self.assertEqual(len(events),7);self.assertEqual({e['data'] for e in events},{5});self.assertEqual({e['time_ps'] for e in events},{5})
            self.assertTrue(r['all_event_classes_observed']);self.assertFalse(r['complete_phase_qualified'])
    def test_writer_offer_binding_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);b['writer_sink_bound']=False
            with self.assertRaisesRegex(ValueError,'writer offer'):M.record(p,b,out)
    def test_missing_exact_signal_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);b['events'][0]['valid']='other.valid'
            with self.assertRaisesRegex(ValueError,'missing exact'):M.record(p,b,out)
    def test_unknown_active_payload_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);p.write_text(p.read_text().replace('b00000101','bxxxxxxxx'))
            with self.assertRaisesRegex(ValueError,'unknown active'):M.record(p,b,out)
    def test_reset_and_inactive_edge_no_credit(self):
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);p.write_text(p.read_text().replace('1"','0"'))
            r=M.record(p,b,out);self.assertEqual(r['events'],0);self.assertEqual(len(r['missing_event_classes']),7)
    def test_multiple_clock_changes_same_time_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);p.write_text(p.read_text().replace('#5\n1!','#5\n1!\n0!'))
            with self.assertRaisesRegex(ValueError,'multiple clock'):M.record(p,b,out)
    def test_width_mismatch_and_shape_unbound_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);b['events'][0]['fields']['data']['width']=9
            with self.assertRaisesRegex(ValueError,'width mismatch'):M.record(p,b,out)
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);b['whole_phase_geometry_bound']=False
            with self.assertRaisesRegex(ValueError,'geometry unbound'):M.record(p,b,out)
    def test_input_not_offered_calendar(self):
        with tempfile.TemporaryDirectory() as td:
            p,b,out=self.setup_fixture(td);b['input_class']='OFFERED_PROFILE'
            with self.assertRaisesRegex(ValueError,'not an actual'):M.record(p,b,out)

    def test_cli_missing_input_preserves_first_exception(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);out=base/'out'
            r=subprocess.run([sys.executable,str(ROOT/'tools/dsrom_accepted_waveform_trace.py'),'--vcd',str(base/'missing.vcd'),'--bindings',str(base/'missing.json'),'--out',str(out)],capture_output=True)
            self.assertNotEqual(r.returncode,0)
            failure=json.loads((out/'failure.json').read_text())
            self.assertEqual(failure['exception_type'],'FileNotFoundError')
            self.assertIn('missing.json',failure['exception'])
            self.assertIn('vcd_pin_error',failure)
            self.assertFalse((out/'record.json').exists())
    def test_source_plan_does_not_qualify_generic_sink_or_ack(self):
        plan=json.loads((ROOT/'results/uarch/dsrom_absolute_acceptance_trace_prepare_20261002/model.json').read_text())
        self.assertFalse(plan['G0']['whole_phase_accepted'])
        self.assertFalse(plan['G0']['compile_admitted'])
        self.assertIsNone(plan['owned_runtime_job'])
        self.assertEqual(plan['source_sink_contract']['ACK'],'no ACK inferred or invented')
        self.assertTrue(plan['source_producer']['no_current_PAR2_binding'])
        self.assertFalse(plan['source_producer']['existing_producer_is_sufficient'])
        self.assertIsNone(plan['consumer_deadlines'])

if __name__=='__main__':unittest.main()
