import copy
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('w6_connector',ROOT/'tools/hbm_w6_connector_model.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.parent=W.owner46(17,0,0xDEADBEEF,3)
        self.frame=W.ParentFrame(parentref=0xAABBCCDD,parent_owner=self.parent,SM=31,RFslot=511,base_byte=0,enabled=True)
        self.physical=W.load_sources()[1]

    def bind(self,index,**changes):
        p=self.physical(index*32)
        legacy=dict(die=0,stack=p['stack'],sector=p['local_sector31'],producer=0xFEDCBA9876543210,
            transport=0xFE123456,caller=0xFEDC,client=8,irs_slot=31,irs_serial=0xFEDCBA98)
        args=dict(client=5,originaltag=0xFEABC000+index,source_generation=3,
            physical_tag=100+index,backend_generation=14,legacy_identity=legacy)
        args.update(changes)
        return self.frame.bind(index,**args)

    def capture(self,index,row,**changes):
        args=dict(backend_token=row['token'],meta92=row['meta92'],legacy_identity=row['legacy'],data=bytes([index])*32)
        args.update(changes);self.frame.capture(index,**args)

    def event(self,kind,**changes):
        args=dict(parentref=self.frame.parentref,parent55=self.frame.parent55);args.update(changes)
        self.frame.event(kind,**args)

    def fullframe(self):
        rows=[]
        for i in range(16):
            row=self.bind(i);self.capture(i,row);rows.append(row)
        return self.frame.rf_frame(),rows

    def test_actual_address_mapping_differs_from_low7(self):
        p=self.physical(32);self.assertEqual(p['system_sector34'],1);self.assertEqual(p['PC'],0)
        rows=[self.bind(i) for i in range(16)]
        self.assertEqual({r['stack'] for r in rows},{0,1,2,3})
        self.assertEqual([r['PC'] for r in rows],[0]*4+[32]*4+[64]*4+[96]*4)

    def test_meta92_and_two_generations_independent_full_echo(self):
        r=self.bind(0)
        self.assertLess(r['meta92'],2**92)
        self.assertEqual(r['child']&15,3)
        self.assertEqual(r['token']>>12,14)
        self.assertEqual(r['meta92']&0xFFFFFFFF,self.frame.parentref)
        with self.assertRaisesRegex(ValueError,'full16'):self.capture(0,r,backend_token=r['token']&4095)
        self.capture(0,r);self.assertTrue(self.frame.children[0]['quarantined'])

    def test_legacy192_fields_preserved_not_client_directory_cast(self):
        r=self.bind(0);bad=copy.deepcopy(r['legacy']);bad['client']=0
        with self.assertRaises(ValueError):self.capture(0,r,legacy_identity=bad)
        for name in ('producer','transport','caller','irs_serial'):
            bad=copy.deepcopy(r['legacy']);bad[name]^=1
            with self.subTest(field=name),self.assertRaises(ValueError):self.capture(0,r,legacy_identity=bad)
        self.assertEqual(r['legacy']['client'],8)

    def test_wrong_source_meta_SM_slot_ref_or_direction(self):
        r=self.bind(0)
        for bit in (0,32,41,46):
            with self.subTest(bit=bit),self.assertRaises(ValueError):self.capture(0,r,meta92=r['meta92']^(1<<bit))
        with self.assertRaises(ValueError):self.capture(0,r,direction=1)
        self.assertFalse(self.frame.children[0]['captured'])

    def test_duplicate_and_early_physical_retirement_refused(self):
        r=self.bind(0);self.capture(0,r)
        with self.assertRaises(ValueError):self.capture(0,r)
        with self.assertRaisesRegex(ValueError,'early R14'):self.frame.legacy_ore(0)
        self.assertTrue(self.frame.children[0]['quarantined'])

    def test_full_frame_parent_not_last_child(self):
        f,rows=self.fullframe()
        self.assertEqual(f['data'],b''.join(bytes([i])*32 for i in range(16)))
        self.assertEqual(f['parent55'],(self.parent<<9)|511)
        wrong=(rows[-1]['child']<<9)|511
        self.assertNotEqual(wrong,f['parent55'])
        with self.assertRaises(ValueError):self.event('RF_ACK',parent55=wrong)
        self.event('RF_ACK');self.assertFalse(self.frame.released)

    def test_partial_requires_old_origin_and_preserves_tail(self):
        r=self.bind(0);self.capture(0,r)
        with self.assertRaisesRegex(ValueError,'partial'):self.frame.rf_frame()
        old=bytes(range(256))*2
        self.frame=W.ParentFrame(parentref=0xAABBCCDD,parent_owner=self.parent,SM=31,RFslot=511,base_byte=0,enabled=True,old_frame=old)
        for i in (0,1):r=self.bind(i);self.capture(i,r)
        f=self.frame.rf_frame()
        self.assertEqual(f['data'][:64],bytes(32)+bytes([1])*32)
        self.assertEqual(f['data'][64:],old[64:])

    def test_raw_FP8_not_FP32_RF_deposition(self):
        self.frame=W.ParentFrame(parentref=0xAABBCCDD,parent_owner=self.parent,SM=31,RFslot=511,base_byte=0,enabled=True,format='FP8_KV_RAW')
        r=self.bind(0);self.capture(0,r)
        with self.assertRaisesRegex(ValueError,'codec'):self.frame.rf_frame()

    def test_unique_live_child_and_backend_namespace(self):
        self.bind(0)
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.bind(1,originaltag=0xFEABC000)
        with self.assertRaisesRegex(ValueError,'backend token'):self.bind(1,physical_tag=100)
        with self.assertRaisesRegex(ValueError,'seventh'):self.bind(1,client=6)

    def test_reverse_every_full_child_once_then_parent_CDC_allcopies(self):
        f,rows=self.fullframe()
        for e in ('RF_ACK','visible','consumer'):self.event(e)
        with self.assertRaises(ValueError):self.event('parent_reverse')
        for i,r in enumerate(rows):
            for extra in ({'backend_token':r['token']&4095},{'meta92':r['meta92']^1},
                          {'reverse_DIE':1},{'reverse_STACK':r['stack']^1},{'reverse_direction':1},{'reverse_BEAT':1}):
                args=dict(index=i,backend_token=r['token'],meta92=r['meta92'],reverse_DIE=0,reverse_STACK=r['stack'],reverse_direction=0,reverse_BEAT=0);args.update(extra)
                with self.assertRaises(ValueError):self.event('child_reverse',**args)
            self.event('child_reverse',index=i,backend_token=r['token'],meta92=r['meta92'],reverse_DIE=0,reverse_STACK=r['stack'],reverse_direction=0,reverse_BEAT=0)
            with self.assertRaises(ValueError):self.event('child_reverse',index=i,backend_token=r['token'],meta92=r['meta92'],reverse_DIE=0,reverse_STACK=r['stack'],reverse_direction=0,reverse_BEAT=0)
        for e in ('parent_reverse','reverse_CDC','drain_request'):self.event(e)
        self.assertTrue(all(x['quarantined'] for x in self.frame.children.values()))
        with self.assertRaises(ValueError):self.event('allcopies',drain=(True,)*8+(False,))
        self.event('allcopies',drain=(True,)*9)
        self.assertTrue(self.frame.released);self.assertFalse(any(x['quarantined'] for x in self.frame.children.values()))

    def test_LEN1_BEAT0_DIESTACK_and_write_ready_freeze(self):
        with self.assertRaisesRegex(ValueError,'LEN1'):self.bind(0,request_LEN=4)
        r=self.bind(0)
        with self.assertRaisesRegex(ValueError,'BEAT0'):self.capture(0,r,BEAT=1)
        wrong=copy.deepcopy(r['legacy']);wrong['die']=1
        with self.assertRaises(ValueError):self.capture(0,r,legacy_identity=wrong)
        m=W.model();f=m['W2_frozen']
        self.assertTrue(f['p_wr_done_ready_required']);self.assertTrue(f['old_pulse_only_compatibility_superseded'])
        self.assertEqual(f['full_wrapper_costs']['raw_state_bits_per_PC'],4779)
        self.assertEqual(f['full_wrapper_costs']['protected_state_bits_per_PC'],9144)
        self.assertAlmostEqual(f['full_wrapper_costs']['gross128PC50pct_slot_mm2_ASSUMED'],6.62582757888)
        self.assertIsNone(f['net_increment_area']);self.assertTrue(f['gross_is_not_additive_delta'])
        self.assertEqual(f['boundary_signal_bits']['aggregated_request'],339)
        self.assertEqual(m['pipeline_delta']['raw_request'],389)

    def test_model_large_missing_cost_not_free_W2_source(self):
        m=W.model()
        self.assertEqual(m['pipeline_delta']['protected_increment_FFs'],1575936)
        self.assertEqual(m['widths']['meta'],92);self.assertEqual(m['widths']['owned_return'],561)
        self.assertEqual(m['sidecar']['macros'],128);self.assertFalse(m['sidecar']['second_CAM_added'])
        self.assertEqual(m['frame']['full32SM_child_row_protected_bits'],73728)
        self.assertFalse(m['build_admitted']);self.assertFalse(m['production_or_physical_credit'])
        self.assertEqual(m['latency_terms']['tag_owner_source_CORE_edges'],12)
        self.assertEqual(m['latency_terms']['return_arbiter_source_CORE_edges'],7)

if __name__=='__main__':unittest.main()
