from pathlib import Path
import importlib.util
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('w6_fullwidth',ROOT/'tools/hbm_w6_fullwidth_model.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)


class FullwidthTests(unittest.TestCase):
    def setUp(self):
        self.owner=W.encode_owner(127,5,0xFE123456,15)
        self.g=W.Golden(enabled=True,SM=31)

    def step(self,event,**kw):
        self.g.tick(3 if event=='reverse_CDC' else 2)
        self.g.event(owner=self.owner,RF_slot=511,kind=event,**kw)

    def test_canonical46_55_and_generation_not_duplicated(self):
        self.assertEqual(W.decode_owner(self.owner),dict(physical_PC=127,client=5,original_tag=0xFE123456,generation=15))
        p=W.price();self.assertEqual(p['owner_bits'],46);self.assertEqual(p['total_identity_bits'],55)
        self.assertEqual(p['table']['raw_fields']['owner_and_RFslot'],55)
        self.assertNotIn('generation',p['table']['raw_fields'])
        self.assertFalse(p['minimum_gain_threshold_required'])

    def test_positive_price_ports_area_replication(self):
        p=W.price()
        self.assertEqual(p['table']['raw_bits_per_SM'],71)
        self.assertEqual(p['table']['protected_bits_per_SM'],144)
        self.assertEqual(p['latency']['candidate_W6_minimum_edges'],19)
        self.assertTrue(all(x['candidate_minimum_edges']>0 and x['replicas']==32 for x in p['boundaries']))
        self.assertGreater(p['area']['full32SM_slot_mm2'],0)
        self.assertTrue(p['component_control_construction_costed_prospectively'])
        self.assertFalse(p['whole_composed_build_admitted'])
        self.assertEqual(p['completion_input_ports']['host_common_ACK_control_bits'],57)

    def test_default_off(self):
        with self.assertRaises(ValueError):W.Golden().accept(owner=self.owner,RF_slot=511)

    def test_canonical_mutation_refused(self):
        target=ROOT/W.OUT/'F0_inputs'/W.CANONICAL;read=Path.read_bytes
        def changed(p):return read(p)+b'\n' if p==target else read(p)
        with patch.object(Path,'read_bytes',changed),self.assertRaises(ValueError):W.price()

    def test_bounded_fixture_and_exact_stale_fields(self):
        self.g.accept(owner=self.owner,RF_slot=511)
        self.g.tick(2)
        for shift in (0,4,36,39):
            with self.assertRaises(ValueError):self.g.event(owner=self.owner^(1<<shift),RF_slot=511,kind='common_ACK')
        with self.assertRaises(ValueError):self.g.event(owner=self.owner,RF_slot=510,kind='common_ACK')
        self.assertEqual(self.g.phase,'ACK')

    def test_backpressure_duplicate_consumer_reverse_once(self):
        self.g.accept(owner=self.owner,RF_slot=511)
        for e in ('common_ACK','visible','consumer','child_reverse','parent_reverse','reverse_CDC','drain_request','allcopies','retire'):
            self.g.tick(3 if e=='reverse_CDC' else 2)
            kw=dict(allcopies=(True,)*9) if e=='allcopies' else {}
            self.assertFalse(self.g.event(owner=self.owner,RF_slot=511,kind=e,ready=False,**kw))
            self.g.tick(2);self.g.event(owner=self.owner,RF_slot=511,kind=e,**kw)
            with self.assertRaises(ValueError):self.g.event(owner=self.owner,RF_slot=511,kind=e,**kw)
        self.assertEqual(self.g.phase,'IDLE')
        self.assertEqual(sum(x['event']=='consumer_fixture' for x in self.g.trace),1)
        self.assertEqual(sum(x['event']=='reverse_CDC_fixture' for x in self.g.trace),1)

    def test_internal_SIMD_ACK_separate_from_host(self):
        self.g.accept(owner=self.owner,RF_slot=511,origin='internal_SIMD');self.g.tick(2)
        with self.assertRaisesRegex(ValueError,'host ACK'):self.g.event(owner=self.owner,RF_slot=511,kind='common_ACK')
        self.g.event(owner=self.owner,RF_slot=511,kind='internal_SIMD_ACK_retire')
        self.assertEqual(self.g.phase,'VISIBLE')
        g=W.Golden(enabled=True);g.accept(owner=self.owner,RF_slot=511);g.tick(2)
        with self.assertRaisesRegex(ValueError,'internal ACK'):g.event(owner=self.owner,RF_slot=511,kind='internal_SIMD_ACK_retire')

    def test_no_premature_release_or_empty_counter_drain(self):
        self.g.accept(owner=self.owner,RF_slot=511)
        for e in ('common_ACK','visible','consumer','child_reverse','parent_reverse','reverse_CDC','drain_request'):self.step(e)
        self.g.tick(2)
        for flags in (None,(),(True,)*8,(True,)*8+(False,),(1,)*9):
            with self.assertRaises(ValueError):self.g.event(owner=self.owner,RF_slot=511,kind='allcopies',allcopies=flags)
        self.assertEqual(self.g.phase,'QUIESCENCE')
        with self.assertRaises(ValueError):self.g.event(owner=self.owner,RF_slot=511,kind='retire')

    def test_reset_quarantines_owner_and_positive_drain(self):
        self.g.accept(owner=self.owner,RF_slot=511);self.g.reset()
        self.assertEqual(self.g.owner,self.owner)
        with self.assertRaises(ValueError):self.g.accept(owner=self.owner,RF_slot=511)
        with self.assertRaises(ValueError):self.g.event(owner=self.owner,RF_slot=511,kind='reset_allcopies',allcopies=(True,)*9)
        self.g.tick(2)
        self.g.event(owner=self.owner,RF_slot=511,kind='reset_drain_request')
        self.g.tick(2)
        self.g.event(owner=self.owner,RF_slot=511,kind='reset_allcopies',allcopies=(True,)*9)
        with self.assertRaises(ValueError):self.g.accept(owner=self.owner,RF_slot=511)
        self.g.tick(2);self.g.accept(owner=self.owner,RF_slot=511)
        self.assertEqual(self.g.phase,'ACK')

    def test_repeated_fixture_wrap_only_after_matched_reverse_and_drain(self):
        for generation in range(18):
            self.owner=W.encode_owner(127,5,0xFE123456,generation%16)
            self.g.tick(2);self.g.accept(owner=self.owner,RF_slot=511)
            for e in ('common_ACK','visible','consumer','child_reverse','parent_reverse','reverse_CDC','drain_request','allcopies','retire'):
                self.step(e,**({'allcopies':(True,)*9} if e=='allcopies' else {}))
        self.assertEqual(sum(x['event']=='retire_fixture' for x in self.g.trace),18)
        # These are supplied fully drained fixture inputs, not actual source
        # quiescence implementation or a production repeated-token PASS.

    def test_fixture_not_production_and_no_arbitrary_caps(self):
        self.assertFalse(W.finite_bench()['hardware_qualified'])
        p=W.price();self.assertTrue(p['latency']['no_run_or_generation_cap'])
        self.assertIsNone(p['latency']['unconditional_finite_maximum'])
        self.assertEqual(p['continuous_stream']['DS_PCs'],2213)
        self.assertEqual(p['continuous_stream']['Qwen_PCs'],1737)
        self.assertFalse(p['directory_client_added'])
        for row in p['latency']['sensitivity']:self.assertGreaterEqual(row['W6_edges'],19)

if __name__=='__main__':unittest.main()
