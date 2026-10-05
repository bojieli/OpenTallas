import gzip,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_ratio_fifo_gap as a
class RatioGap(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.m=a.build()
 def test_exact_source_and_two_actual_clock_sdc(self):
  m=self.m;self.assertEqual(m['source_hash'],'56fec932b1f673eb10169dab58d4b1510af94f9d1ec4bdf75d17f1378f690284')
  s=(a.BASE/'inputs/6_final.sdc').read_text();self.assertIn('period 833.3330',s);self.assertIn('period 1111.1110',s)
  self.assertEqual(s.count('set_clock_uncertainty -setup 60.0000'),2);self.assertEqual(s.count('set_clock_uncertainty -hold 25.0000'),2)
 def test_failed_data_path_not_pointer_success(self):
  p=self.m['retained_physical'];self.assertAlmostEqual(p['SS_setup_ps'],-75.591148);self.assertGreater(p['SS_reported_pointer_path_ps'],0)
  self.assertEqual(p['failed_path'],'mem[0][63] -> r_d[63]');self.assertGreater(p['FF_hold_ps'],0)
 def test_every_related_phase_sparse_bound_and_consumer_edge(self):
  for name,period,cycles in [('fast_to_slow',4,4),('slow_to_fast',3,5)]:
   rows=self.m['exact_phase_event_model'][name];self.assertEqual(len(rows),4 if period==4 else 3)
   for r in rows:
    self.assertEqual(r['consumer_accept_ticks']-r['data_capture_ticks'],period)
    self.assertLessEqual(r['consumer_accept_ticks'],cycles*period)
 def test_backpressure_exceeds_fixed_sparse_latency(self):
  r=a.isolated(3,4,0,stall_until=80);self.assertGreater(r['consumer_accept_ticks'],16)
  self.assertEqual(self.m['existing_model']['archived_stalled']['f2s_lat_slow_cycles'],'3.00/4.28/15.01')
 def test_credits_prevent_overwrite_and_output_holds(self):
  for r in self.m['stream_event_checks'].values():
   self.assertEqual(r['words'],2048);self.assertTrue(r['ordered_once']);self.assertEqual(r['overwrite_before_capture'],[]);self.assertEqual(r['stalled_output_changes'],[])
 def test_reset_witnesses_are_preserved_no_epoch_pass(self):
  w=self.m['reset_witnesses'];self.assertTrue(w['write_during_write_reset']['write_fire']);self.assertEqual(w['write_during_write_reset']['wp_after'],0)
  self.assertEqual(w['reader_only_reset_after_retirement']['consumer_replay'],['old_epoch'])
 def test_no_width_converter_or_parent_replica_inferred(self):
  self.assertEqual(self.m['ports']['input_payload_bits'],self.m['ports']['output_payload_bits']);self.assertIsNone(self.m['ports']['replica_count_in_actual_parent'])
  self.assertEqual(self.m['ports']['structural_cross_domain_bits']['data_array_to_mux'],256)
  self.assertTrue(any(p['historical_slow_bits']<p['required_slow_bits_ceil'] for p in self.m['historical_port_ledger']))
 def test_actual_dual_clock_logs_reproduce_archived_phase_results(self):
  record=self.m['actual_retained_dual_clock_bench'];self.assertEqual(len(record['runs']),3)
  for row in record['runs']:
   self.assertEqual(row['exit_code'],0)
   if row['name']!='compile':
    self.assertEqual(row['terminal'],'PASS')
    log=(a.BASE/row['log']).read_bytes();self.assertEqual(hashlib.sha256(log).hexdigest(),row['log_sha256'])
 def test_actual_reset_diagnostic_keeps_negative_scope(self):
  r=self.m['actual_reset_witness_record'];self.assertTrue(all(x['exit_code']==0 for x in r['runs']))
  log=(a.ROOT/'results/rtl/dsrom_ratio_fifo_reset_witness_20261003/simulate.log').read_text()
  self.assertIn('stale_replays=1',log);self.assertIn('WITNESS_WRITE_RESET',log);self.assertIn('NOT_CDC_QUALIFICATION',log)
  self.assertFalse(r['successor_RTL_admitted'])
 def test_admission_and_no_cycle_or_area_credit(self):
  self.assertFalse(self.m['admission']['successor_engine_RTL_admitted']);self.assertFalse(self.m['admission']['physical_build_admitted'])
  self.assertEqual(self.m['minimal_successor']['planned_capture_cycles_added'],0);self.assertEqual(self.m['minimal_successor']['removed_state_area_credit'],0)
if __name__=='__main__':unittest.main()
