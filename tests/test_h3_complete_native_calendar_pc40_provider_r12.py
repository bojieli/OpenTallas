import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('pc40_provider_r12',ROOT/'tools/h3_complete_native_calendar_pc40_provider_r12.py')
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)


class ProviderCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.inputs=M.load()

    def test_actual_checkpoint_payload(self):
        r=M.payload_binding(self.inputs)
        self.assertTrue(r['checkpoint_payload_pass'])
        self.assertFalse(r['up_payload_captured'])
        self.assertFalse(r['hardware_handshake_observed'])
        self.assertFalse(r['source_gate_released'])

    def test_wrong_payload(self):
        inputs=dict(self.inputs);inputs['gate.bin']=b'x'*512
        with self.assertRaises(ValueError):M.payload_binding(inputs)

    def test_wrong_checkpoint_verdict(self):
        inputs=dict(self.inputs);r=json.loads(inputs['terminal.json']);r['verdict']='FAIL'
        inputs['terminal.json']=json.dumps(r).encode()
        with self.assertRaises(ValueError):M.payload_binding(inputs)

    def test_provider_port_inventory(self):
        r=M.compile_join(self.inputs)
        self.assertEqual(r['physical_RF_reads'],5)
        self.assertEqual(sum(e.get('physical_read_bytes',0) for e in r['events']),5120)
        self.assertEqual(sum(e.get('physical_mirror_write_bytes',0) for e in r['events']),5120)
        self.assertEqual(r['NoC_payload_bytes'],512)
        self.assertEqual(r['W2_HBM_commands'],0)
        self.assertFalse(r['I64_or_RMW_recharged'])

    def test_actual_remote_home_refuses_fake_local(self):
        inputs=dict(self.inputs);r=json.loads(inputs['caller.json']);r['source_up_home']['storage_SM']=0
        inputs['caller.json']=json.dumps(r).encode()
        with self.assertRaises(ValueError):M.compile_join(inputs)

    def test_wrong_version(self):
        inputs=dict(self.inputs);r=json.loads(inputs['caller.json']);r['source_up_home']['version']='wrong'
        inputs['caller.json']=json.dumps(r).encode()
        with self.assertRaises(ValueError):M.compile_join(inputs)

    def test_actual_workspace_alias(self):
        for slot in (17,18,19):
            with self.assertRaises(ValueError):
                M.compile_join(self.inputs,entering_leases=[dict(rank=0,SM=0,slot=slot,lease='actual live')])

    def test_other_SM_same_slot_does_not_alias(self):
        r=M.compile_join(self.inputs,entering_leases=[dict(rank=0,SM=24,slot=17,lease='actual live')])
        self.assertEqual(r['workspace_admission'],'SOURCE_DISJOINT_ONLY')
        self.assertIsNone(r['finite_production_upper'])

    def test_absent_live_inventory_refuses(self):
        self.assertEqual(M.compile_join(self.inputs)['workspace_admission'],'REFUSED_MISSING_ENTERING_LEASES')

    def test_common_ACK_has_no_fabricated_tag(self):
        r=M.compile_join(self.inputs)
        self.assertEqual(r['physical_common_ACK_tag_bits'],0)
        self.assertFalse(r['reset_allcopy_issuer_bound'])
        self.assertFalse(any(e['accepted_receipt'] for e in r['events']))

    def test_visible_before_real_read_consumer_before_reverse(self):
        r=M.compile_join(self.inputs);by={e['eventID']:e for e in r['events']}
        self.assertEqual(by['FMIN.RF19_read_pair']['deps'],['W6.ACK_to_visible'])
        self.assertIn('FMIN.held_value_accept',by['W6.consumer_to_child_reverse']['deps'])
        self.assertIsNone(by['W6.allcopies_to_retire']['end_min_edges'])
        self.assertEqual(r['W6_boundary_edges'],19)
        self.assertFalse(r['W6_request_and_RF_ACK_subtracted'])

    def test_unknown_noc_not_zero_or_global_stop(self):
        r=M.compile_join(self.inputs);by={e['eventID']:e for e in r['events']}
        self.assertIsNone(by['up.NoC_SM24_SM0']['end_min_edges'])
        self.assertIsNotNone(by['FMAX.write19_ACK']['end_min_edges'])
        self.assertIsNone(by['PC40.final_product_source_join']['end_min_edges'])
        self.assertFalse(by['PC40.final_product_source_join']['releases_gate_or_up'])

    def test_unrelated_resources_and_shared_RF_serialize(self):
        events=[dict(eventID='a',deps=['p'],resource='RF0',min_edges=3),
                dict(eventID='b',deps=['p'],resource='RF0',min_edges=3),
                dict(eventID='c',deps=['p'],resource='RF24',min_edges=3)]
        r=M.schedule(events,{'p':0})
        self.assertEqual([x['end_min_edges'] for x in r],[3,6,3])

    def test_positive_transport_parameter_control_only(self):
        r=M.compile_join(self.inputs,transport={
            'up.NoC_SM24_SM0':dict(min_edges=8,source_pin='explicit control source'),
            'up.publication_at_SM0':dict(min_edges=2,source_pin='explicit control source'),
            'FMIN.held_value_accept':dict(min_edges=1,source_pin='explicit control source')})
        by={e['eventID']:e for e in r['events']}
        self.assertEqual(by['up.publication_at_SM0']['end_min_edges'],13)
        self.assertIsNotNone(by['W6.allcopies_to_retire']['end_min_edges'])
        self.assertIsNone(r['finite_production_upper'])
        self.assertFalse(r['physical_qualified'])

    def test_unpinned_or_zero_transport_refuses(self):
        for b in [dict(min_edges=0,source_pin='control'),dict(min_edges=1)]:
            with self.assertRaises(ValueError):M.compile_join(self.inputs,transport={'up.NoC_SM24_SM0':b})

    def test_source_FMIN_drift(self):
        inputs=dict(self.inputs);inputs['consumer.sv']=inputs['consumer.sv'].replace(b"32'h42b00000",b"32'h42c00000")
        with self.assertRaises(ValueError):M.compile_join(inputs)

    def test_dag_duplicate_rejected(self):
        event=dict(eventID='x',deps=['p'],resource='RF',min_edges=1)
        with self.assertRaises(ValueError):M.schedule([event,event],{'p':0})

    def test_cold_exact(self):
        self.assertEqual(M.compile_join(self.inputs),json.loads((M.BASE/'calendar.json').read_text()))

if __name__=='__main__':unittest.main()
