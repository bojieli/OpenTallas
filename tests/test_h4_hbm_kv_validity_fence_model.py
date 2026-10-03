import copy
from fractions import Fraction
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_hbm_kv_validity_fence_model as k


class SourceBoundModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=k.compile_plan()

    def test_source_metadata_and_runtime_spill_projection(self):
        self.assertEqual(len(self.plan['groups']),72)
        for g in self.plan['groups']:
            self.assertEqual(len(g['metadata_writes']),6)
            self.assertEqual(sum(p['bytes'] for p in g['metadata_writes']),73)
            self.assertEqual([p['operation'] for p in g['metadata_writes']][1:3],['commit_bitmap','commit_record'])
            self.assertEqual(g['source_metadata_read_calls'],dict(bitmap_byte=1027,record16=5))
            self.assertEqual(len(g['producer_vectors']),8)
            self.assertEqual(len(g['decoded_sectors']),128)
            self.assertTrue(all(h['home']['class']=='spill' for h in g['decoded_result_homes']))
            self.assertTrue(all(h['home']['class']=='RF' for h in g['source_producer_homes']))
            self.assertTrue(g['producer_RF_write_cost_already_owned_by_PC5_PC9'])

    def test_no_implicit_zero_or_invalid_old_capture(self):
        t=k.SectorTransaction();i=(1,0,1);t.reserve(i,address=32,mask=0x10001)
        for event in ['merge','write_visible','consumer','reverse']:
            with self.assertRaises(ValueError):t.event(i,event,payload=bytes(32),receipt={})
        with self.assertRaises(ValueError):t.event(i,'old_capture',payload=bytes(32),receipt=dict(identity=i,address=64,full_sector_valid=True))
        with self.assertRaises(ValueError):t.event(i,'old_capture',payload=None,receipt=dict(identity=i,address=32,full_sector_valid=True))
        self.assertEqual(t.active['phase'],'OLD')

    def test_all_actual_payload_and_metadata_masks_preserve_old_bytes(self):
        t=k.SectorTransaction();sequence=0;count=0
        old=bytes((i*47+0x80)&255 for i in range(32))
        for g in self.plan['groups']:
            for row in g['payload']+g['metadata_writes']:
                sequence+=1;i=(1,g['die'],sequence);t.reserve(i,address=row['address'],mask=row['mask'])
                t.event(i,'old_capture',payload=old,receipt=dict(identity=i,address=row['address'],full_sector_valid=True))
                patch=bytes.fromhex(row['patch_hex']);merged=t.event(i,'merge',payload=patch)
                self.assertEqual(merged,bytes(patch[j] if row['mask']>>j&1 else old[j] for j in range(32)))
                t.event(i,'write_visible',receipt=dict(identity=i,address=row['address'],data=merged))
                t.event(i,'consumer');t.event(i,'reverse');count+=1
        self.assertEqual(count,20016);self.assertIsNone(t.active)

    def test_stale_capture_and_credit_held_through_reverse(self):
        t=k.SectorTransaction();i=(1,0,1);t.reserve(i,address=0,mask=1)
        with self.assertRaises(ValueError):t.reserve((1,0,2),address=32,mask=1)
        with self.assertRaises(ValueError):t.event((1,1,1),'old_capture',payload=bytes(32))
        t.event(i,'old_capture',payload=bytes(32),receipt=dict(identity=i,address=0,full_sector_valid=True))
        merged=t.event(i,'merge',payload=bytes([255]*32))
        with self.assertRaises(ValueError):t.event(i,'write_visible',receipt=dict(identity=i,address=0,data=bytes(32)))
        t.event(i,'write_visible',receipt=dict(identity=i,address=0,data=merged));t.event(i,'consumer')
        with self.assertRaises(ValueError):t.reserve((1,0,2),address=32,mask=1)
        t.event(i,'reverse')
        with self.assertRaises(ValueError):t.reserve(i,address=0,mask=1)

    def test_bitmap_visible_does_not_grant_reader_or_metadata_credit(self):
        g=self.plan['groups'][0];f=k.MetadataFence(g)
        with self.assertRaises(ValueError):f.acquire(1)
        for v,p in enumerate(g['producer_vectors']):
            for c in (0,1):f.mirror_ACK(vector=v,copy=c,provider_ref=p['provider_ref'],RF_slot=p['RF_slot'])
        for ordinal in (0,1):
            p=g['metadata_writes'][ordinal];f.visible(ordinal,address=p['address'],data=bytes.fromhex(p['patch_hex']))
        with self.assertRaises(ValueError):f.publish_fence()
        with self.assertRaises(ValueError):f.acquire(1)
        p=g['metadata_writes'][2];f.visible(2,address=p['address'],data=bytes.fromhex(p['patch_hex']))
        f.publish_fence();f.acquire(1)
        with self.assertRaises(ValueError):f.consumer('SCORES',lease=1)

    def test_full72_fences_require_producer_mirrors_spill_and_consumer_records(self):
        for g in self.plan['groups']:
            f=k.MetadataFence(g);lease=g['reader_lease']
            p=g['metadata_writes'][0]
            with self.assertRaises(ValueError):f.visible(0,address=p['address'],data=bytes.fromhex(p['patch_hex']))
            for v,p in enumerate(g['producer_vectors']):
                for c in (0,1):f.mirror_ACK(vector=v,copy=c,provider_ref=p['provider_ref'],RF_slot=p['RF_slot'])
            with self.assertRaises(ValueError):f.mirror_ACK(vector=0,copy=0,provider_ref=g['producer_vectors'][0]['provider_ref'],RF_slot=g['producer_vectors'][0]['RF_slot'])
            for ordinal in range(3):
                p=g['metadata_writes'][ordinal];f.visible(ordinal,address=p['address'],data=bytes.fromhex(p['patch_hex']))
            f.publish_fence();f.acquire(lease)
            p=g['metadata_writes'][3];f.visible(3,address=p['address'],data=bytes.fromhex(p['patch_hex']))
            for p in g['decoded_sectors']:f.decoded_visible(lease=lease,version=p['version'],address=p['address'])
            with self.assertRaises(ValueError):f.consumer('PV',lease=lease)
            f.consumer('SCORES',lease=lease)
            p=g['metadata_writes'][4];f.visible(4,address=p['address'],data=bytes.fromhex(p['patch_hex']))
            f.consumer('PV',lease=lease)
            with self.assertRaises(ValueError):f.retire(lease=lease,reverse_accepted=True)
            p=g['metadata_writes'][5];f.visible(5,address=p['address'],data=bytes.fromhex(p['patch_hex']))
            f.retire(lease=lease,reverse_accepted=True)
            with self.assertRaises(ValueError):f.retire(lease=lease,reverse_accepted=True)

    def test_actual_shared_write_edge_combined_ack_maps_two_copy_facts(self):
        g=self.plan['groups'][0];f=k.MetadataFence(g);ref=g['producer_vectors'][0]['provider_ref']
        with self.assertRaises(ValueError):f.combined_ACK(vector=0,provider_ref=ref,RF_slot=g['producer_vectors'][0]['RF_slot'],copy0_write_edge=10,copy1_write_edge=11,host_ACK_edge=12,valid=True,ready=True)
        with self.assertRaises(ValueError):f.combined_ACK(vector=0,provider_ref=ref,RF_slot=g['producer_vectors'][0]['RF_slot'],copy0_write_edge=10,copy1_write_edge=10,host_ACK_edge=9,valid=True,ready=True)
        f.combined_ACK(vector=0,provider_ref=ref,RF_slot=g['producer_vectors'][0]['RF_slot'],copy0_write_edge=10,copy1_write_edge=10,host_ACK_edge=12,valid=True,ready=True)
        self.assertEqual(f.mirrors,{(0,0),(0,1)})
        with self.assertRaises(ValueError):f.combined_ACK(vector=0,provider_ref=ref,RF_slot=g['producer_vectors'][0]['RF_slot'],copy0_write_edge=10,copy1_write_edge=10,host_ACK_edge=12,valid=True,ready=True)

    def test_wrong_actual_reader_lease_and_RF_row_refuse(self):
        g=self.plan['groups'][1];f=k.MetadataFence(g)
        p=g['producer_vectors'][0]
        with self.assertRaises(ValueError):f.mirror_ACK(vector=0,copy=0,provider_ref=p['provider_ref'],RF_slot=p['RF_slot']+1)
        for v,p in enumerate(g['producer_vectors']):
            for c in (0,1):f.mirror_ACK(vector=v,copy=c,provider_ref=p['provider_ref'],RF_slot=p['RF_slot'])
        for ordinal in range(3):
            p=g['metadata_writes'][ordinal];f.visible(ordinal,address=p['address'],data=bytes.fromhex(p['patch_hex']))
        f.publish_fence()
        with self.assertRaises(ValueError):f.acquire(g['reader_lease']+1)
        f.acquire(g['reader_lease'])

    def test_finite_arbitration_no_starvation_under_continuous_reads(self):
        clients=tuple(['KV']+['SM'+str(i) for i in range(8)])
        a=k.BankArbiter(clients,{c:Fraction(i+1) for i,c in enumerate(clients)})
        for i,c in enumerate(clients):a.enqueue(c,i)
        order=[]
        for round in range(3):
            for _ in range(9):
                c,identity=a.grant();order.append(c)
                with self.assertRaises(ValueError):a.enqueue(c,round+10)
                self.assertIsNone(a.grant())
                a.reverse(c,identity);a.enqueue(c,round+10)
        self.assertEqual(order,list(clients)*3)
        self.assertEqual(a.wait_bound('KV'),sum(range(2,10)))
        with self.assertRaises(ValueError):a.reverse('KV',999)

    @staticmethod
    def profile():
        # Directed model parameters ONLY, explicitly not source physical timing.
        return dict(costs_ps={key:('2500' if key=='RF_pair_read' else '5000/3' if key=='RF_mirror_ACK' else '2500/3') for key in k.COST_KEYS},
            contender_hold_ps={str(b):{'directed_fixture':'2500/3'} for b in range(64)},
            qualification='provisional',origin='directed test cost profile; not actual emitted calendar')

    def test_complete_profile_prices_all_mandatory_terms(self):
        p=k.price(self.plan,self.profile())
        self.assertGreater(Fraction(p['serialized_total_upper_ps']),0)
        self.assertEqual(p['metadata_cold_init_sectors'],2344)
        self.assertEqual(p['counts']['merge'],18864)
        self.assertEqual(p['counts']['RF_pair_read'],576)
        self.assertEqual(p['counts']['RF_both_copy_write'],0)
        self.assertFalse(p['actual_program_contender_composition'])
        self.assertFalse(p['hardware_admitted'])

    def test_missing_zero_or_promoted_costs_refuse(self):
        profile=self.profile();del profile['costs_ps']['child_reverse']
        with self.assertRaises(ValueError):k.price(self.plan,profile)
        profile=self.profile();profile['costs_ps']['refill']=0
        with self.assertRaises(ValueError):k.price(self.plan,profile)
        profile=self.profile();profile['qualification']='source_bound'
        with self.assertRaises(ValueError):k.price(self.plan,profile)
        profile=self.profile();del profile['contender_hold_ps']['0']
        with self.assertRaises(ValueError):k.price(self.plan,profile)

    def test_validity_connection_holds_actual_shared_bank_ledger(self):
        import h4_hbm_w19_pc10_endpoints as o
        matrix=o.vector_owner_controller([0,1])
        bridge=k.ConnectedPayloadService(banks=matrix.banks,profile=self.profile(),epoch=1)
        self.assertIs(bridge.endpoint.banks,matrix.banks)
        g=self.plan['groups'][0];key=g['key'];row=g['payload'][0]
        bridge.begin(key);identity=bridge.grant(key,address=row['address'])
        with self.assertRaises(ValueError):bridge.reverse(key)
        with self.assertRaises(ValueError):bridge.merge(key,old=None,validity_receipt={})
        self.assertEqual(len(matrix.banks),1)
        data=bridge.merge(key,old=bytes([0x80]*32),validity_receipt=dict(identity=identity,address=row['address'],full_sector_valid=True))
        bridge.visible(key,receipt=dict(identity=identity,address=row['address'],data=data))
        self.assertEqual(len(matrix.banks),1)
        bridge.consumer(key);self.assertEqual(len(matrix.banks),1)
        bridge.reverse(key);self.assertFalse(matrix.banks)

    def test_model_geometry_and_admission_remain_separate(self):
        m=k.model();self.assertFalse(m['engine_build_ready']);self.assertFalse(m['physical_cuts_admitted'])
        self.assertEqual(m['source_demands']['metadata_partial_writes'],432)
        self.assertGreater(m['constructive_design']['incremental_footprint_mm2_per_die_ASSUMED'],0)
        self.assertEqual(m['constructive_design']['request_descriptor_bits'],280)
        self.assertTrue(m['source_findings']['source_bitmap_precedes_record'])
        self.assertTrue(m['constructive_design']['source32SM_organisation_preserved'])

    def test_exact_replay(self):
        for name,raw in k.outputs().items():self.assertEqual((k.BASE/name).read_bytes(),raw)


if __name__=='__main__':unittest.main()
