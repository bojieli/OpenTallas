"""Atomic protocol controls; fixture mappings are NOT installed hardware."""
import copy, concurrent.futures, threading, unittest
from h4_c0_v1_owner_lock_addressed import PhysicalBindings,AtomicV1Owners,export_contract
from h4_c0_bridge import AdmissionError

def controls():
    inventory=dict(schema='C0_PHYSICAL_RF_CONNECTION_MAP_V1',connection_source_pin='a'*40,connection_source_sha256='b'*64,
        bindings=[dict(model=m,rank=0,SM=0,physical_RF_id='CONTROL_RF',hierarchy='CONTROL_ONLY.rf',RF_module='ot_gpu_rf_service',
            vectors=512,lanes=128,word_bits=32,mirrors=2) for m in ('Qwen','DeepSeek')])
    def home(version,slots):return dict(version=version,lease=version+'_lease',rank=0,SM=0,generation=7,physical_RF_id='CONTROL_RF',RF_vectors=slots)
    command=dict(model='DeepSeek',family='CONTROL_SELECT',source_PC=0,program_sha256='c'*64,template_id='CONTROL_ONLY',ordered_step_index=0,
        owner_tag=4,generation=7,rank=0,SM=0,opcode='SELECT',source_bittypes=[32,64,64],destination_bittype=64,
        source_version_home_refs=[home('predicate',[32]),home('a',[33,34]),home('b',[35,36])],destination_version_home_ref=home('dst',[37,38]),
        predicate={'source':0},active_lanes=128,response_stall_bound=10,source_attrs_rounding={'CONTROL_ONLY':True})
    return AtomicV1Owners(PhysicalBindings(inventory,protocol_control=True),enabled=True,software_model=True),command

def compute(lock,token):
    for i in range(3):lock.read_accept(token,i);lock.read_return(token,i)
    lock.compute_complete(token)

def write(lock,token):
    for i in range(2):lock.write_accept(token,i);lock.write_mirror_ACK(token,i,0);lock.write_mirror_ACK(token,i,1)

def reverse(token,sequence=100):
    return dict(event='validated_reverse_grant',sequence=sequence,identity=dict(physical_RF_id=token[0],model=token[1],rank=token[2],SM=token[3],owner_tag=token[4],generation=token[5]))

def fragment(token,kind='source_refill'):
    identity=dict(reverse(token)['identity'],version='a' if kind=='source_refill' else 'dst',lease='a_lease' if kind=='source_refill' else 'dst_lease',fragment_sequence=1)
    return dict(kind=kind,identity=identity,workspace_extent={'AW':27,'bytes':33554432,'base':33554432,'occupied_extents':[{'base':0,'bytes':33554432}]},
        byte_address=33554432,payload_bytes=64,scratch_byte_address=0,observed_payload_sha256='d'*64,provider_source_sha256='e'*64)

def fragment_events(lock,token,f):
    names=['software_backing_store_read_return' if f['kind']=='source_refill' else 'software_backing_store_write_commit','consumer_accept','validated_reverse_grant']
    for i,name in enumerate(names):lock.provider_event(token,f['identity']['fragment_sequence'],dict(event=name,identity=f['identity'],sequence=i+1,
        byte_address=f['byte_address'],payload_bytes=f['payload_bytes'],payload_sha256=f['observed_payload_sha256']))

class OwnerTests(unittest.TestCase):
    def test_three_reads_two_mirrored_writes_one_atomic_owner(self):
        lock,c=controls();t=lock.accept(c)
        self.assertEqual(lock.live[t[0]]['read_pairs'][2]['used_ports'],[True,False])
        self.assertFalse(lock.contender_allowed(t[0]))
        compute(lock,t);write(lock,t)
        with self.assertRaises(ValueError):lock.retire(t)
        lock.consumer_accept(t);lock.reverse_grant(t,reverse(t));lock.retire(t)
        self.assertTrue(lock.contender_allowed(t[0]))
    def test_cross_model_same_physical_RF_excluded(self):
        lock,c=controls();lock.accept(c);c['model']='Qwen';c['owner_tag']=5
        with self.assertRaisesRegex(AdmissionError,'atomic owner busy'):lock.accept(c)
    def test_concurrent_accept_is_atomic(self):
        lock,c=controls();barrier=threading.Barrier(2)
        def attempt(tag):
            cmd=copy.deepcopy(c);cmd['owner_tag']=tag;barrier.wait()
            try:lock.accept(cmd);return True
            except AdmissionError:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(attempt,tag) for tag in (4,5)]
            self.assertEqual(sum(f.result() for f in futures),1)
        self.assertEqual(len(lock.live),1)
    def test_no_interleave_until_read_return_or_each_mirror_ACK(self):
        lock,c=controls();t=lock.accept(c);lock.read_accept(t,0)
        with self.assertRaises(AdmissionError):lock.read_accept(t,1)
        lock.read_return(t,0)
        for i in (1,2):lock.read_accept(t,i);lock.read_return(t,i)
        lock.compute_complete(t);lock.write_accept(t,0);lock.write_mirror_ACK(t,0,0)
        with self.assertRaises(AdmissionError):lock.write_accept(t,1)
        with self.assertRaises(AdmissionError):lock.consumer_accept(t)
        lock.write_mirror_ACK(t,0,1);lock.write_accept(t,1)
    def test_wrong_rank_SM_home_and_generation_rejected_without_owner(self):
        for field in ('rank','SM','generation','physical_RF_id'):
            lock,c=controls();c['source_version_home_refs'][0][field]='wrong'
            with self.assertRaises(AdmissionError):lock.accept(c)
            self.assertFalse(lock.live)
    def test_unmapped_SM_never_implicitly_uses_SM0(self):
        lock,c=controls();c['SM']=1
        with self.assertRaisesRegex(AdmissionError,'unmapped installed'):lock.accept(c)
    def test_wrong_tag_cannot_consume_or_retire(self):
        lock,c=controls();t=lock.accept(c);bad=(*t[:-1],8)
        with self.assertRaises(AdmissionError):lock.read_accept(bad,0)
        self.assertEqual(lock.live[t[0]]['lease'].live['reads'],0)
    def test_retired_tag_never_aliases_later_PC_command(self):
        lock,c=controls();t=lock.accept(c);compute(lock,t);write(lock,t)
        lock.consumer_accept(t);lock.reverse_grant(t,reverse(t));lock.retire(t)
        c['source_PC']=1
        with self.assertRaisesRegex(AdmissionError,'tag/generation replay'):lock.accept(c)
        c['owner_tag']=5;new=lock.accept(c)
        with self.assertRaises(AdmissionError):lock.read_accept(t,0)
        lock.read_accept(new,0)
    def test_refill_blocks_reads_until_matched_reverse(self):
        lock,c=controls();t=lock.accept(c);f=fragment(t);lock.provider_accept(t,f)
        with self.assertRaises(AdmissionError):lock.read_accept(t,0)
        fragment_events(lock,t,f);lock.read_accept(t,0)
        with self.assertRaises(AdmissionError):lock.provider_accept(t,f)
    def test_destination_writeback_requires_mirror_ACK_and_delays_consumer(self):
        lock,c=controls();t=lock.accept(c);f=fragment(t,'destination_writeback')
        with self.assertRaises(AdmissionError):lock.provider_accept(t,f)
        compute(lock,t);write(lock,t);lock.provider_accept(t,f)
        with self.assertRaises(AdmissionError):lock.consumer_accept(t)
        fragment_events(lock,t,f);lock.consumer_accept(t)
    def test_wrong_payload_address_event_does_not_drain(self):
        lock,c=controls();t=lock.accept(c);f=fragment(t);lock.provider_accept(t,f)
        e=dict(event='software_backing_store_read_return',identity=f['identity'],sequence=1,byte_address=f['byte_address']+32,payload_bytes=64,payload_sha256='d'*64)
        with self.assertRaises(AdmissionError):lock.provider_event(t,1,e)
        self.assertEqual(lock.live[t[0]]['provider_pending'][1]['phase'],0)
    def test_contract_exports_missing_physical_binding_honestly(self):
        c=export_contract();self.assertFalse(c['hardware_admitted']);self.assertFalse(c['installed_bindings'])
        self.assertIsNone(c['existing_hardware_instance']['logical_rank'])
        self.assertEqual(c['worst_case']['RF_read_pair_transactions'],3)
        self.assertEqual(c['worst_case']['RF_write_vectors'],2)
    def test_protocol_fixture_cannot_be_used_as_installed_inventory(self):
        lock,c=controls()
        with self.assertRaisesRegex(AdmissionError,'installed connection inventory path'):
            PhysicalBindings(lock.bindings.inventory)
    def test_composed_owner_ticket_and_no_RF_highword_double_charge(self):
        lock,c=controls();t=lock.accept(c);state=lock.owner(t)
        self.assertEqual(state['C0_ticket'],(7,0,4,0,0))
        compute(lock,t);write(lock,t)
        self.assertEqual(state['serialized'].time,13+state['cost']['native_only_replacement_ticks'])
    def test_composed_response_bound_failure_retains_owner(self):
        lock,c=controls();t=lock.accept(c);lock.read_accept(t,0)
        with self.assertRaises(ValueError):lock.read_return(t,0,stalls=11)
        self.assertEqual(lock.owner(t)['read_pending'],0)
        self.assertFalse(lock.contender_allowed(t[0]))
    def test_default_off(self):
        lock,c=controls()
        with self.assertRaises(AdmissionError):AtomicV1Owners(lock.bindings)

if __name__=='__main__':unittest.main()
