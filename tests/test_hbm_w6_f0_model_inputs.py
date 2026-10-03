import copy
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('w6_f0',ROOT/'tools/hbm_w6_f0_model_inputs.py')
W=importlib.util.module_from_spec(spec);sys.modules[spec.name]=W;spec.loader.exec_module(W)


class SourceCompatibleTests(unittest.TestCase):
    def setUp(self):
        self.s=W.SourceTuple(127,5,0xFE123456,4,1,7,31,511,1736,0xFEDCBA98)
        self.payload=bytes(range(256))*2

    def test_F0_pins_and_minimum_W2_inventory(self):
        p=W.model_inputs()
        self.assertEqual(p['source_compatible']['backend_tag_plus_generation'],39)
        self.assertEqual(p['W2']['NC5_rows_per_PC'],80)
        self.assertEqual(p['W2']['NC6_rows_per_PC'],96)
        self.assertEqual(p['W2']['row_minimum_bits'],38)
        self.assertEqual(p['W6_state_candidate']['raw_bits_per_slot'],224)
        self.assertEqual(p['W6_state_candidate']['SECDED64_padded_protected_bits_per_slot'],288)
        self.assertFalse(p['build_admitted'])
        self.assertEqual(len(p['F0_contract_sha256']),3)
        self.assertEqual(p['W2']['full_wrapper_client5'],'occupied KV')

    def test_frozen_contract_mutation_refused_without_source_edits(self):
        target=ROOT/W.F0_ARCHIVE/'W2-interface-contract-r1.json'
        original=Path.read_bytes
        def changed(p):
            return original(p)+b'\n' if p==target else original(p)
        with patch.object(Path,'read_bytes',changed),self.assertRaisesRegex(ValueError,'frozen F0 input pin'):
            W.model_inputs()

    def test_original_tag32_and_generation4_are_separate(self):
        e=self.s.backend_echo()
        self.assertEqual(e['p_tag'],(5<<32)|0xFE123456)
        self.assertEqual(e['p_generation'],4)
        self.assertEqual(e['p_tag']&0xFFFFFFFF,self.s.original_tag)
        self.assertNotEqual(self.s.original_tag&15,self.s.generation)
        self.assertTrue(W.exact_backend_match(self.s,e))

    def test_no_truncated_original_tag_or_missing_generation_echo(self):
        for field,bad in [('p_tag',self.s.physical_tag&65535),('p_generation',3),
                           ('physical_PC',126),('direction',0),('p_generation',True)]:
            e=self.s.backend_echo();e[field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):W.exact_backend_match(self.s,e)
        e=self.s.backend_echo();del e['p_generation']
        with self.assertRaises(ValueError):W.exact_backend_match(self.s,e)

    def test_same_tag_other_PC_or_namespace_not_same_owner(self):
        pc=W.namespace_handle(namespace='PC',physical_PC=5,tag=0x1234)
        coal=W.namespace_handle(namespace='coalescer',physical_PC=5,tag=0x1234)
        other=W.namespace_handle(namespace='PC',physical_PC=6,tag=0x1234)
        self.assertNotEqual(pc,coal);self.assertNotEqual(pc,other)
        e=replace(self.s,physical_PC=126).backend_echo()
        with self.assertRaises(ValueError):W.exact_backend_match(self.s,e)

    def test_NC5_vs_NC6_and_program_domains(self):
        with self.assertRaisesRegex(ValueError,'enrolled'):self.s.validate(NC=5,model='Qwen')
        self.s.validate(NC=6,model='Qwen')
        with self.assertRaises(ValueError):replace(self.s,program_PC=1737).validate(NC=6,model='Qwen')
        replace(self.s,program_PC=2212).validate(NC=6,model='DS')
        with self.assertRaises(ValueError):replace(self.s,program_PC=2213).validate(NC=6,model='DS')
        for field,bad in [('original_tag',2**32),('generation',16),('physical_PC',128),('SM',32)]:
            with self.subTest(field=field),self.assertRaises(ValueError):replace(self.s,**{field:bad}).validate(NC=6,model='Qwen')

    def test_modulo16_is_not_monotonic_run_cap_or_drain(self):
        for g in range(16):
            p=W.generation_successor(g)
            self.assertEqual(p['next_generation'],(g+1)%16)
            self.assertFalse(p['run_cap']);self.assertFalse(p['source_quiescence_installed'])
            self.assertIn('SOURCE_ALL_COPIES',p['admission'])
        self.assertTrue(W.generation_successor(15)['wrapped'])

    def test_finite_C0_then_KV_read_exact_source_tuple(self):
        r=W.bench();self.assertEqual([c['path'] for c in r['cases']],['C0','KV_READ'])
        for c in r['cases']:
            self.assertEqual(c['final_phase'],'REUSE_PENDING')
            identities=[x['source'] for x in c['trace']]
            self.assertTrue(all(x==identities[0] for x in identities))
            self.assertFalse(c['actual_hardware_events'])
            edges=[x['edge'] for x in c['trace']]
            self.assertEqual(edges,sorted(set(edges)))

    def test_stale_full_owner_fields_do_not_advance_held_fence(self):
        g=W.SourceFenceReference(enabled=True)
        g.accept(self.s,path='C0',payload=self.payload);g.tick()
        g.completion(self.s,echo=self.s.backend_echo(),payload=self.payload,copy_mask=3);g.tick()
        g.boundary(self.s,event='visibility',ready=False)
        for field in ('generation','original_tag','physical_PC','client','rank','SM','RF_slot','program_PC','home_id'):
            wrong=replace(self.s,**{field:getattr(self.s,field)-1})
            with self.subTest(field=field),self.assertRaises(ValueError):g.boundary(wrong,event='visibility')
        self.assertEqual(g.phase,'VISIBILITY');self.assertEqual(g.active,self.s)
        g.tick();g.boundary(self.s,event='visibility')
        with self.assertRaises(ValueError):g.boundary(self.s,event='visibility')

    def test_no_early_consumer_or_retire_and_both_copies_required(self):
        g=W.SourceFenceReference(enabled=True)
        g.accept(self.s,path='C0',payload=self.payload);g.tick()
        for mask in (0,1,2,True):
            with self.assertRaises(ValueError):g.completion(self.s,echo=self.s.backend_echo(),payload=self.payload,copy_mask=mask)
        for event in ('consumer','reverse','retire'):
            with self.assertRaises(ValueError):g.boundary(self.s,event=event)
        self.assertEqual(g.phase,'COMPLETION')

    def test_retire_fixture_cannot_claim_source_quiescence(self):
        g=W.SourceFenceReference(enabled=True)
        g.accept(self.s,path='C0',payload=self.payload);g.tick()
        g.completion(self.s,echo=self.s.backend_echo(),payload=self.payload,copy_mask=3)
        for e in ('visibility','consumer','reverse','retire'):
            g.tick();g.boundary(self.s,event=e)
        self.assertEqual(g.phase,'REUSE_PENDING');self.assertEqual(g.active,self.s)
        g.tick()
        with self.assertRaises(ValueError):g.accept(replace(self.s,generation=5),path='C0',payload=self.payload)

    def test_KV_direction_version_exactness(self):
        g=W.SourceFenceReference(enabled=True);s=replace(self.s,direction=0);data=bytes(range(32))
        g.accept(s,path='KV_READ',payload=data,read_version=7);g.tick()
        for version in (None,6,True):
            with self.assertRaises(ValueError):g.completion(s,echo=s.backend_echo(),payload=data,read_version=version)
        g.completion(s,echo=s.backend_echo(),payload=data,read_version=7)

    def test_default_off_no_engine_or_priced_boundary_credit(self):
        with self.assertRaises(ValueError):W.SourceFenceReference().accept(self.s,path='C0',payload=self.payload)
        p=W.model_inputs()
        self.assertTrue(all(x['positive_cycles_required'] and x['cycles'] is None for x in p['boundary_model_inputs']))
        self.assertFalse(p['new_engine_RTL']);self.assertFalse(p['physical_qualified'])
        self.assertIsNone(p['wrap']['wait_cycles']);self.assertFalse(p['source_compatible']['compact_parent16_selected'])


if __name__=='__main__':unittest.main()
