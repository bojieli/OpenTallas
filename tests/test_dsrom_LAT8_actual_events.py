import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('trace',ROOT/'tools/extract_dsrom_LAT8_actual_events.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
class ActualEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log=(t.BASE/'inputs/existing_fast8_simulate.log').read_text()
        cls.products=t.generate()
    def test_byte_exact_reproduction(self):
        for name,data in self.products.items():
            expected=''.join(json.dumps(row,sort_keys=True)+'\n' for row in data) if name.endswith('.jsonl') else json.dumps(data,indent=2,sort_keys=True)+'\n'
            self.assertEqual((t.BASE/name).read_text(),expected,name)
    def test_actual_calendar_and_values(self):
        p=self.products['profile.json'];self.assertEqual(p['counts']['accepted_configuration_writes'],25)
        self.assertEqual(p['counts']['accepted_fifo_pushes'],16)
        self.assertEqual(p['hazard_samples'],112);self.assertEqual(p['issues_during_hazard'],0)
        public=[e for e in self.products['events.jsonl'] if e['kind']=='pair_public_partial']
        self.assertEqual([(x['cycle'],x['position'],x['value_hex'],x['error']) for x in public],[(155,0,'44000000',0),(219,1,'44000000',0)])
        cfg=[e for e in self.products['events.jsonl'] if e['kind']=='accepted_configuration_write']
        self.assertEqual([e['address'] for e in cfg],list(range(25)))
        self.assertEqual(cfg[16]['source_derived_word_hex'],'000000000008')
        self.assertFalse(any(e['data_observed'] for e in cfg))
    def test_no_invented_return_write_drain_deadline(self):
        c=self.products['consumer_contract.json']
        self.assertIsNone(c['original_consumer_deadline_cycles'])
        self.assertEqual(c['writes']['observed_events'],[])
        self.assertEqual(c['root_returns']['observed_events'],[])
        self.assertFalse(c['retirement_drain']['complete_observed'])
        self.assertEqual(c['retirement_drain']['source_rows_left_initial'],514)
        self.assertFalse(any(e['kind'] in ['root_return','write','drain_complete'] for e in self.products['events.jsonl']))
    def test_fixture_units_proven_not_comment_frequency(self):
        p=self.products['profile.json']['fixture_clock'];self.assertEqual(p['tick_ps'],833000);self.assertFalse(p['frequency_credit'])
        bench=(t.BASE/'inputs/tb_dsrom_upstream_pair_cadence.sv').read_text()
        self.assertIn('`timescale 1ns/1ps',bench);self.assertIn('#416;',bench);self.assertIn('#415;clk=0;#1;',bench)
        clock=json.loads((t.BASE/'inputs/clock_generated_inspection.json').read_text())
        cpp='\n'.join(e['text'] for e in clock[0]['excerpts'])
        self.assertIn('65900ULL',cpp);self.assertIn('65518ULL',cpp)
        self.assertIn('timeprecision(-12)',str(clock[1]))
    def test_missing_duplicate_wrong_cycle_samples_refused(self):
        lines=self.log.splitlines()
        for mutant in [lines[1:],lines[:1]+lines, [lines[0].replace('cycle=3','cycle=4')]+lines[1:]]:
            with self.subTest(mutant=mutant[0]):
                with self.assertRaises(ValueError):t.parse('\n'.join(mutant))
    def test_terminal_and_malformed_controls(self):
        for mutant in [self.log.replace(t.PASS,''),self.log+'\n'+t.PASS,self.log.replace('LOADER cycle=3','LOADER cycle=x'),self.log.replace('value=44000000','value=44000001',1),self.log.replace('valid=1 addr=24','valid=1 addr=25')]:
            with self.assertRaises(ValueError):t.parse(mutant)
    def test_public_cycle_context_refused(self):
        with self.assertRaises(ValueError):t.parse('PUBLIC row=256 seg=0 nseg=1 pos=0 value=44000000 err=0\n'+self.log)
    def test_offered_join_preserves_program_scope(self):
        j=self.products['offered_word_join.json']
        self.assertEqual(j['config_binding']['observed_go_relative_cfg'],27)
        self.assertEqual(j['config_binding']['observed_last_loader_relative_cfg'],26)
        self.assertFalse(j['full_program_acceptance_proven'])
        self.assertEqual((j['selected_fixture_K'],j['offered_profile_K']),(512,5120))
        self.assertEqual([(m['position'],m['slice'],m['fixture_stream_index'],m['offered_index']) for m in j['matches']],[(p,b,8*b,16*b) for p in range(2) for b in range(8)])
        for m in j['matches']:
            self.assertEqual(m['source_derived_need_q'],288+32*m['slice'])
            self.assertGreaterEqual(m['observed_have'],m['source_derived_need_q'])
            self.assertEqual(m['observed_pair_emit_cycle']-m['observed_stream_advance_cycle'],3)
        self.assertEqual(j['first_loaded_data_admission']['observed_have'],256)
        self.assertEqual(j['first_loaded_data_admission']['observed_s_adv'],0)
        self.assertEqual(j['first_loaded_data_admission']['accepted_have'],320)
    def test_changed_go_pulse_refused(self):
        with self.assertRaisesRegex(ValueError,'cfg/go pulse'):
            t.parse(self.log.replace('cfg=0 go=1','cfg=0 go=0'))
    def test_package_tampering_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'sourcepins.json').write_text(json.dumps({'extraction_inputs_sha256':{'input':'0'*64}}));(p/'input').write_text('wrong')
            with self.assertRaisesRegex(ValueError,'source pin mismatch'):t.generate(p)
if __name__=='__main__':unittest.main()
