import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('adapter',ROOT/'tools/dsrom_PAR2_decoder_adapter_prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class AdapterPrepare(unittest.TestCase):
 def setUp(self):self.lease=m.Lease(0,0,1,10,3,0);self.read=m.Read(self.lease,0,0,0,10,0);self.t=m.TerminalModel(self.lease)
 def words(self,slot=0):
  main0,side0=m.split_protected_main(123,enabled=True);main1,side1=m.split_protected_main((1<<271)|29,enabled=True);fields=[0]*32;fields[2*slot]=side0;fields[2*slot+1]=side1
  return main0,main1,m.protected_sidecar_word(fields)
 def test_default_off_and_exact_systematic_bit_split(self):
  with self.assertRaises(ValueError):m.split_protected_main(0)
  e=m.ecc_source()
  for data in [0,1,(1<<271),(1<<272)-1,int('a5'*34,16)]:
   main,side=m.split_protected_main(data,enabled=True);self.assertEqual(main&((1<<272)-1),data);self.assertEqual(m.join_main(main,side),e.encode(data,272));self.assertEqual(side>>7,e.encode(data,272)>>281)
 def test_all_main_codeword_single_bit_faults(self):
  e=m.ecc_source();data=(1<<271)|123;main,side=m.split_protected_main(data,enabled=True);cw=m.join_main(main,side)
  for bit in range(282):self.assertEqual(e.decode(cw^(1<<bit),272),(data,'corrected'))
  self.assertEqual(e.decode(cw^3,272)[1],'uncorrectable')
 def test_sidecar_protected_word_and_every_single_bit(self):
  e=m.ecc_source();fields=[i*7%256 for i in range(32)];cw=m.protected_sidecar_word(fields);raw=sum(v<<(8*i) for i,v in enumerate(fields));self.assertEqual(e.decode(cw,256),(raw,'ok'))
  for bit in range(266):self.assertEqual(e.decode(cw^(1<<bit),256),(raw,'corrected'))
 def test_terminal_order_both_main_then_consumer_ACK(self):
  a,b,cw=self.words();self.t.accept(7,self.read)
  with self.assertRaises(ValueError):self.t.main_terminal(7,0,a)
  self.t.capture(self.read,cw);self.assertFalse(self.t.drained);self.t.raw_terminals([self.read.word]);self.assertFalse(self.t.drained)
  self.t.main_terminal(7,0,a)
  with self.assertRaises(ValueError):self.t.consumer_ack(7)
  self.t.main_terminal(7,1,b);self.assertFalse(self.t.drained);self.t.consumer_ack(7);self.assertTrue(self.t.drained)
 def test_wrong_generation_and_duplicate_returns(self):
  self.t.accept(7,self.read);old=m.Read(m.Lease(0,0,1,10,3,1),0,0,0,10,0)
  with self.assertRaises(ValueError):self.t.capture(old,0)
  self.t.capture(self.read,self.words()[2]);self.t.raw_terminals([self.read.word])
  with self.assertRaises(ValueError):self.t.capture(self.read,0)
  with self.assertRaises(ValueError):self.t.raw_terminals([self.read.word])
 def test_one_leaf_debt_and_four_shared_capture_slots(self):
  self.t.accept(1,self.read)
  with self.assertRaises(ValueError):self.t.accept(2,m.Read(self.lease,0,0,0,11,0))
  for i in range(1,5):
   r=m.Read(self.lease,i,0,0,10,0);self.t.accept(i+2,r)
   if i<4:self.t.capture(r,0)
  self.t.capture(self.read,0)
  with self.assertRaises(ValueError):self.t.capture(m.Read(self.lease,4,0,0,10,0),0)
  with self.assertRaises(ValueError):self.t.raw_terminals([self.read.word]*5)
 def test_cancelled_epoch_requires_capture_debt_drain(self):
  self.t.accept(1,self.read);self.t.capture(self.read,self.words()[2]);self.t.cancel()
  with self.assertRaises(ValueError):self.t.raw_terminals([self.read.word])
  with self.assertRaises(ValueError):self.t.retire_cancelled(1)
  with self.assertRaises(ValueError):self.t.rearm(m.Lease(0,0,1,10,4,1))
  self.t.drain_capture(self.read.word);self.t.retire_cancelled(1);self.assertTrue(self.t.drained);self.t.rearm(m.Lease(0,0,1,10,4,1));self.assertFalse(self.t.cancelled)
 def test_cancel_before_capture_does_not_erase_backend_debt(self):
  self.t.accept(1,self.read);self.t.cancel()
  with self.assertRaises(ValueError):self.t.retire_cancelled(1)
  self.assertFalse(self.t.drained);self.t.quarantine_return(self.read);self.t.retire_cancelled(1);self.assertTrue(self.t.drained)
  with self.assertRaises(ValueError):self.t.quarantine_return(self.read)
 def test_raw_uncorrectable_poison_blocks_arithmetic(self):
  a,b,cw=self.words();self.t.accept(1,self.read);self.t.capture(self.read,cw^3);self.t.raw_terminals([self.read.word]);self.assertTrue(self.t.fault)
  with self.assertRaises(ValueError):self.t.main_terminal(1,0,a)
  self.t.retire_cancelled(1);self.assertTrue(self.t.drained)
 def test_same_word_coalescing_requires_matching_slots(self):
  a,b,cw=self.words();self.t.accept(1,self.read);r=m.Read(self.lease,0,0,0,10,1);self.t.accept(2,r);self.t.capture(self.read,cw);self.t.raw_terminals([self.read.word]);self.assertNotEqual(self.t.raw_visible[1],self.t.raw_visible[2])
 def test_current_resource_model_follows_Maxwell_four_grants(self):
  x=m.build();f=x['finite_context'];self.assertEqual(f['shared_raw_decoder_replicas'],4);self.assertEqual(f['raw_capture_seats'],4);self.assertEqual(f['max_phase_prefetch_raw_reads'],800);self.assertEqual(f['max_phase_read_rounds_per_single_port_leaf'],400);self.assertEqual(f['raw266_412to4_mux2_nodes'],437304);self.assertTrue(x['producer_contract']['current_payload_packer_emits_no_protected_checks']);self.assertEqual(x['no_engine_RTL_compile_PR_jobs'],0)
if __name__=='__main__':unittest.main()
