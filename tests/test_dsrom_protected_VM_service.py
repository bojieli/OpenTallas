import importlib.util,json,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tools/dsrom_protected_VM_service.py'
s=importlib.util.spec_from_file_location('protected_vm',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class ProtectedVM(unittest.TestCase):
    def finish(self,s):
        for _ in range(21):
            s.step()
            if s.response or s.fault:return
        self.fail('Finite service did not complete')
    def initialized(self):
        s=m.Service()
        for i in range(4):
            self.assertTrue(s.accept('INIT',i,100+i,data=sum((0x3f000000+i*16+l)<<(32*l)for l in range(16)),mask=65535))
            self.finish(s);self.assertIsNone(s.fault);s.consume(100+i)
        return s
    def test_frozen_source_only_model(self):
        self.assertEqual(json.loads((m.BASE/'model.json').read_text()),m.build())
        self.assertEqual(len(m.pins()),11)
    def test_real_sidecar_capacity_and_half_mapping(self):
        homes={m.home(w)for w in range(32768)}
        self.assertEqual(len(homes),32768)
        self.assertEqual(m.home(0)[:3],m.home(2048)[:3])
        self.assertNotEqual(m.home(0)[3],m.home(2048)[3])
        self.assertEqual(32*512*128,2097152)
    def test_no_uninitialized_prefix_or_zero_assumption(self):
        s=m.Service()
        with self.assertRaises(ValueError):s.accept('READ4',0,1)
        with self.assertRaises(ValueError):s.accept('INIT',1,2,data=0,mask=65535)
        with self.assertRaises(ValueError):s.accept('WRITE_MASKED',0,3,data=1,mask=1)
    def test_init_checked_before_prefix_advance(self):
        s=m.Service();s.accept('INIT',0,1,data=1,mask=65535)
        for _ in range(12):s.step()
        self.assertEqual(s.init_next,0);self.assertIsNone(s.response)
        s.step();self.assertEqual(s.init_next,1);self.assertEqual(s.response['at'],12)
    def test_reset_acceptance_and_debt(self):
        s=m.Service();self.assertFalse(s.accept('INIT',0,1,mask=65535,rst_n=False))
        self.assertTrue(s.accept('INIT',0,1,mask=65535))
        with self.assertRaises(ValueError):s.reset(True)
        self.finish(s);s.consume(1)
        with self.assertRaises(ValueError):s.reset(False)
        s.reset(True);self.assertEqual(s.init_next,0)
    def test_all_lane_masks_preserve_checked_siblings(self):
        s=self.initialized();expected=s.data[0]
        for lane in range(16):
            value=0x40000000+lane
            s.accept('WRITE_MASKED',0,200+lane,data=value<<(32*lane),mask=1<<lane)
            self.finish(s);self.assertIsNone(s.fault)
            expected=(expected&~(m.MASK32<<(32*lane)))|(value<<(32*lane))
            self.assertEqual(s.response['data'],expected)
            self.assertEqual(s.response['at']-s.pending['start'],19)
            s.consume(200+lane)
    def test_full_write_checked_visibility_order(self):
        s=self.initialized();s.accept('WRITE_FULL',0,300,data=7,mask=65535);start=s.now
        self.finish(s)
        e={v['event']:v['edge']-start for v in s.events if v.get('owner')==300}
        self.assertEqual(e['data_and_parity_visible'],4);self.assertEqual(e['raw_ack_NOT_publication'],5)
        self.assertEqual(e['checked_publication'],12)
        self.assertFalse(s.accept('WRITE_FULL',1,301,data=8,mask=65535))
        s.consume(300)
    def test_consumer_stall_retains_sole_credit_and_identity(self):
        s=self.initialized();s.accept('READ4',0,400);self.finish(s);old=dict(s.response)
        for _ in range(100):s.step();self.assertEqual(s.response,old);self.assertFalse(s.accept('READ4',0,401))
        with self.assertRaises(ValueError):s.consume(401)
        self.assertEqual(s.response,old);s.consume(400)
        with self.assertRaises(ValueError):s.consume(400)
    def test_single_data_error_corrected_before_partial_merge(self):
        s=self.initialized();old=s.data[0];s.data[0]^=1<<40
        s.accept('WRITE_MASKED',0,500,data=0x40400000,mask=1);self.finish(s)
        self.assertIsNone(s.fault);self.assertEqual(s.response['data'],(old&~m.MASK32)|0x40400000)
    def test_double_error_quarantines_before_write(self):
        s=self.initialized();s.data[0]^=3;old=s.data[0]
        s.accept('WRITE_MASKED',0,600,data=123,mask=1);self.finish(s)
        self.assertIsNotNone(s.fault);self.assertIsNone(s.response);self.assertEqual(s.data[0],old)
        self.assertFalse(any(e['event']=='data_and_parity_visible' and e.get('owner')==600 for e in s.events))
        with self.assertRaises(ValueError):s.consume(600)
        with self.assertRaises(ValueError):s.reset(True)
    def test_postwrite_double_error_prevents_publication(self):
        s=self.initialized();s.accept('WRITE_FULL',0,700,data=1,mask=65535)
        for _ in range(5):s.step()
        s.data[0]^=3;self.finish(s)
        self.assertIsNotNone(s.fault);self.assertIsNone(s.response)
        self.assertFalse(s.accept('READ4',0,701))
    def test_parity_single_error_corrected(self):
        s=self.initialized();bank,pair,row,half=m.home(0);s.parity[(bank,pair,row)]^=1<<(half*64)
        s.accept('READ4',0,800);self.finish(s)
        self.assertIsNone(s.fault);self.assertEqual(s.response['corrected']&1,1)
    def test_tuple_width_and_zero_mask_refusal(self):
        s=self.initialized()
        for w in (-1,32768,True):
            with self.assertRaises(ValueError):s.accept('READ4',w,1)
        with self.assertRaises(ValueError):s.accept('READ4',0,1<<228)
        with self.assertRaises(ValueError):s.accept('WRITE_MASKED',0,1,data=1,mask=0)
    def test_backend_mutable_registration_exact_inventory(self):
        x=m.build()['source_control_gap']
        self.assertEqual(sum(r['raw_bits']for r in x['raw_register_inventory'].values()),89086)
        self.assertEqual(x['prospective_protected_codewords'],1597)
        self.assertEqual(x['prospective_protected_bits'],114984)
        self.assertEqual(x['replacement_FF_delta_bits'],25898)
    def test_CDC_full_width_and_reverse_receipt(self):
        x=m.build()['CDC_parent_swap']
        self.assertEqual((x['prospective_forward_raw_bits'],x['prospective_reverse_raw_bits']),(773,2343))
        self.assertEqual((x['forward_W6_coded_bits'],x['reverse_W6_coded_bits'],x['reverse_consumer_receipt_W6_bits']),(936,2664,288))
        self.assertEqual(x['FIFO_encoded_data_plus_raw_control_FF'],31182)
        self.assertFalse(x['FIFO_control_protection_installed'])
        self.assertFalse(x['4_over_3_slow_port_widening'])
        self.assertFalse(x['loaded_actual_parent_sources_and_receivers_bound'])
    def test_sidecar_exact_full_state_and_timing_scope(self):
        x=m.build()['sidecar_component']
        self.assertEqual(x['total_FF_bits'],5*288+4*360+3*256+72)
        self.assertEqual((x['codec_encoder_count'],x['codec_decoder_count']),(10,41))
        self.assertFalse(x['physical_admission'])
        self.assertTrue(x['functional_component_build_allowed_after_source_freeze'])
    def test_no_physical_or_unprotected_control_adoption(self):
        x=m.build()
        self.assertFalse(x['source_control_gap']['actual_raw_backend_address_and_selector_protection_installed'])
        for k in ('protected_parent_engine_RTL','connected_protected_VM_build','physical','SSFF','whole_token'):
            self.assertFalse(x['admission'][k])

if __name__=='__main__':unittest.main()
