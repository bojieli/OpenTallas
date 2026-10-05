import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import h4_hbm_qwen_observed_kv_cache as q


class ObservedKVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = q.compile_directory()

    def endpoint(self):
        return q.KVEndpoint(self.directory, banks={})

    def test_exact_counts_and_masks(self):
        m = q.model(self.directory)
        self.assertEqual((m['groups'], m['source_lifecycle_events']), (72, 432))
        self.assertEqual(m['payload_write_address_sectors32'], 19584)
        self.assertEqual(m['payload_read_address_sectors32'], 19584)
        self.assertEqual(m['committed_U8_bytes'], 73728)
        self.assertEqual(m['partial_write_sectors'], 18432)
        self.assertEqual(m['preserved_tail_bytes_required'], 552960)
        for g in self.directory['groups']:
            self.assertEqual(sum(s['kind'] == 'K' for s in g['sectors']), 256)
            self.assertEqual(sum(s['kind'] == 'V' for s in g['sectors']), 16)
            for s in g['sectors']:
                self.assertEqual(s['mask'], 0x10001 if s['kind'] == 'K' else 0xffffffff)
                self.assertIsNone(g['SM'])
                self.assertIn('Qwen.rank'+str(g['die'])+'.extent.', s['provider_ref'])

    def test_actual_source_rf_homes_and_dependencies_exported(self):
        for group in self.directory['groups']:
            homes=group['source_RF_control_version_homes']
            self.assertTrue(homes)
            producers={s['producer_version'] for s in group['sectors']}
            self.assertTrue(producers.issubset({h['version'] for h in homes}))
            for home in homes:
                self.assertEqual(home['rank'],group['die'])
                self.assertIn('release_requires',home)
                if home['home']['class']=='RF':
                    self.assertTrue(home['home']['first_word']['mirrored_ACK_required'])
                    self.assertEqual(home['home']['first_word']['physical_mirrors'],2)
            self.assertIsNone(group['RF_visibility_and_mirror_ACK_observations'])
            self.assertEqual(len(group['source_operation_bindings']),5)
            write=group['source_operation_bindings'][0]
            self.assertEqual(write['opcode'],'KV_WRITE');self.assertTrue(write['dependencies'])

    def test_all_groups_explicit_tail_visibility_and_retirement(self):
        endpoint = self.endpoint()
        writes = reads = preserved = 0
        for g in self.directory['groups']:
            key = g['key']; endpoint.begin(key); backing = {}
            for s in g['sectors']:
                endpoint.grant(key, address=s['address'])
                if s['old_bytes_required']:
                    old = bytes((i*37+0x80)&255 for i in range(32))
                    merged = endpoint.child(key, event='old_sector_capture', payload=old)
                    for i in range(32):
                        if not s['mask'] >> i & 1:
                            self.assertEqual(merged[i], old[i]); preserved += 1
                else:
                    merged = endpoint.child(key, event='full_sector_write')
                backing[s['address']] = merged
                endpoint.child(key, event='backend_write_visible', payload=merged)
                endpoint.child(key, event='consumer_accept')
                endpoint.child(key, event='validated_reverse_grant'); writes += 1
            e = g['source_events'][1]
            endpoint.parent(key, event='commit_publish', receipt=dict(provider_ref=g['state_provider_ref'],
                writer_tag=g['writer_tag'], record_address=e['state']['record_address'], record_hex=e['state']['record_hex'],
                bitmap_address=e['state']['bitmap_address'], bitmap_byte=e['state']['bitmap_byte']))
            endpoint.parent(key, event='acquire', receipt=g['reader_lease'])
            for s in g['sectors']:
                endpoint.grant(key, address=s['address'])
                endpoint.child(key, event='read_capture', payload=backing[s['address']])
                endpoint.child(key, event='consumer_accept')
                endpoint.child(key, event='validated_reverse_grant'); reads += 1
            for index, event in ((3, 'SCORES'), (4, 'PV')):
                e = g['source_events'][index]
                endpoint.parent(key, event=event, receipt=dict(pc=e['pc'], lease=g['reader_lease'], reads=e['reads']))
            endpoint.parent(key, event='release', receipt=dict(lease=g['reader_lease'], reverse_accepted=True))
        self.assertEqual((writes, reads, preserved), (19584,19584,552960))
        self.assertEqual(len(endpoint.finished), 72)
        self.assertFalse(endpoint.banks); self.assertFalse(endpoint.active)

    def test_partial_write_refuses_zero_tail_and_early_ack(self):
        e = self.endpoint(); g = self.directory['groups'][0]; key = g['key']
        e.begin(key); e.grant(key, address=g['sectors'][0]['address'])
        for event in ('full_sector_write', 'backend_write_visible', 'consumer_accept', 'validated_reverse_grant'):
            with self.assertRaises(ValueError):
                e.child(key, event=event, payload=bytes(32))
        with self.assertRaises(ValueError):
            e.child(key, event='old_sector_capture', payload=None)
        with self.assertRaises(ValueError):
            e.parent(key, event='commit_publish', receipt={})
        self.assertEqual(len(e.banks), 1)

    def test_connected_bank_busy_and_exact_sector(self):
        e = self.endpoint(); g = self.directory['groups'][0]; key = g['key']; s = g['sectors'][0]
        e.begin(key); c=s['L2']; bank=(g['die'],c['slice'],c['bank'])
        e.banks[bank] = ('actual_matrix_owner', 1)
        with self.assertRaises(ValueError): e.grant(key, address=s['address'])
        self.assertEqual(e.banks[bank], ('actual_matrix_owner',1))
        del e.banks[bank]
        with self.assertRaises(ValueError): e.grant(key, address=s['address']+32)
        e.grant(key, address=s['address'])
        with self.assertRaises(ValueError): e.grant(key, address=s['address'])

    def test_retained_owner_model_shares_exact_bank_table(self):
        import h4_hbm_w19_pc10_endpoints as owner_source
        owner = owner_source.vector_owner_controller([0,1])
        endpoint = q.KVEndpoint(self.directory, banks=owner.banks)
        self.assertIs(endpoint.banks, owner.banks)
        g=self.directory['groups'][0];sector=g['sectors'][0];c=sector['L2']
        # Directed controller stimulus: no actual Qwen matrix readiness claim.
        sm=c['slice']*8+c['bank'];identity=(1,9,1,0,sm)
        owner.acquire(identity,die=0,sm=sm,bank=c['bank'],address=0,size=32,
            lease=1,reference=0,write=False,mirror_required=False)
        endpoint.begin(g['key'])
        with self.assertRaises(ValueError):endpoint.grant(g['key'],address=sector['address'])
        for event in ['all_prior_H1_sinks_drained','bank_request_accepted']:
            owner.event(identity,die=0,lease=1,reference=0,event=event)
        for event in ['bank_word_request_accepted','bank_word_capture_accepted']:
            owner.event(identity,die=0,lease=1,reference=0,event=event,ordinal=0)
        for event in ['visibility_fence_accepted','consumer_completion_accepted','reverse_lease_grant_accepted']:
            owner.event(identity,die=0,lease=1,reference=0,event=event)
        endpoint.grant(g['key'],address=sector['address'])
        with self.assertRaises(ValueError):
            owner.acquire((1,9,2,0,sm),die=0,sm=sm,bank=c['bank'],address=0,size=32,
                lease=2,reference=0,write=False,mirror_required=False)

    def test_bad_visible_payload_cannot_release_granted_bank(self):
        e=self.endpoint();g=self.directory['groups'][0];key=g['key'];s=g['sectors'][0]
        e.begin(key);e.grant(key,address=s['address'])
        merged=e.child(key,event='old_sector_capture',payload=bytes([255]*32))
        bad=bytes([merged[0]^1])+merged[1:]
        with self.assertRaises(ValueError):e.child(key,event='backend_write_visible',payload=bad)
        with self.assertRaises(ValueError):e.child(key,event='validated_reverse_grant')
        self.assertEqual(len(e.banks),1)
        e.child(key,event='backend_write_visible',payload=merged)
        e.child(key,event='consumer_accept');e.child(key,event='validated_reverse_grant')
        self.assertFalse(e.banks)

    def test_exception_bits_are_opaque_and_tails_preserved(self):
        old=bytes(range(32)); patch=bytes([0xff,0x80,0x7f,0,0x7e,0xfe]*6)[:32]
        merged=q.merge32(old,patch,0x10001)
        self.assertEqual((merged[0],merged[16]), (patch[0],patch[16]))
        self.assertEqual(bytes(merged[i] for i in range(32) if i not in (0,16)), bytes(old[i] for i in range(32) if i not in (0,16)))
        with self.assertRaises(ValueError): q.merge32(None,patch,0x10001)

    def test_reserved_exclusion_and_full_tag(self):
        a=2044*32*128
        self.assertTrue(q.coordinate(a)['reserved'])
        self.assertEqual(q.coordinate(a)['index'], 2044)
        lo=q.coordinate(0);hi=q.coordinate(2**23)
        self.assertEqual(lo['index'],hi['index']);self.assertNotEqual(lo['tag'],hi['tag'])
        self.assertEqual(q.coordinate(2**34-32)['tag'], 2047)
        with self.assertRaises(ValueError):q.coordinate(2**34)
        with self.assertRaises(ValueError):q.coordinate(1)

    def test_no_hardware_command_or_timing_inference(self):
        m=q.model(self.directory)
        for k in ['HBM_command_count','refill_count','physical_cycles','metadata_bus_transactions','actual_event_intervals']:
            self.assertIsNone(m[k])
        self.assertFalse(m['hardware_admitted']);self.assertFalse(m['engine_build_ready'])
        self.assertFalse(self.directory['production_lifecycle_qualified'])
        self.assertEqual(m['selected_cost_event_counts']['KV_sector_reverse'],39168)

    def test_source_directory_mutation_refused(self):
        d=copy.deepcopy(self.directory);d['groups'][0]['sectors'][0]['mask']=0xffffffff
        with self.assertRaises(ValueError):q.KVEndpoint(d,banks={})
        e=self.endpoint()
        with self.assertRaises(ValueError):e.begin((1,0,0))
        e.begin((0,0,0))
        with self.assertRaises(ValueError):e.begin((0,0,0))
        with self.assertRaises(ValueError):e.parent((0,0,0),event='release',receipt={'reverse_accepted':True})

    def test_hard_manifest_and_input_pins(self):
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary);(p/'input_manifest.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'manifest'):q.inputs(p)
        data=q.inputs();data['committed_U8.bin']=data['committed_U8.bin'][:-1]
        with self.assertRaisesRegex(ValueError,'payload range hash'):q.compile_directory(data)

    def test_byte_exact_replay(self):
        for name, data in q.outputs().items():
            self.assertEqual((q.BASE/name).read_bytes(),data)


if __name__ == '__main__':
    unittest.main()
