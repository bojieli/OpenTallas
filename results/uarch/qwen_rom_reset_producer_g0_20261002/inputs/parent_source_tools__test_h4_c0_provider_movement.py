"""Exercise immutable REAL r30 scratch/storage/journal, no trained job launch."""
import copy, hashlib, importlib.util, pathlib, sys, tempfile, types, unittest
from h4_c0_model import pinned
from h4_c0_provider_movement import AddressedMovement, prove_sector_span
from h4_c0_forward_observer_addressed import ProviderTap

PIN='f240f42fbeb67e402e922b4a4aae30b8a8873ce1'

def actual_provider(root,owner=(7,('v',),0,3,11)):
    pathlib.Path(root).mkdir(parents=True,exist_ok=True)
    # Preserve exact dependency bytecode, scoped imports only during construction.
    names=('hbm_provider_microvm_r21','hbm_bound_event_journal_r30','h3_ds_checkpoint_provider_r30')
    old={name:sys.modules.get(name) for name in names};modules={}
    try:
        for name in names:
            module=types.ModuleType(name);module.__file__=str(pathlib.Path(root)/(name+'.py'));sys.modules[name]=module
            raw=pinned('tools/'+name+'.py',PIN);pathlib.Path(module.__file__).write_bytes(raw);exec(compile(raw,module.__file__,'exec'),module.__dict__);modules[name]=module
        journal=modules[names[1]].JournalBudget(pathlib.Path(root)/'journal',8*1024*1024)
        b=modules[names[2]].AddressedScratch(owner,{'base':67108864,'AW':27,'bytes':33554432,'occupied_extents':[{'base':0,'bytes':67108864}]},journal)
        return b,journal
    finally:
        for name,value in old.items():
            if value is None:sys.modules.pop(name,None)
            else:sys.modules[name]=value

class MovementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.backend,self.journal=actual_provider(self.tmp.name)
        self.sha=hashlib.sha256(pinned('tools/h3_ds_checkpoint_provider_r30.py',PIN)).hexdigest()
        self.m=AddressedMovement(self.backend,source_sha256=self.sha);self.key=('native',*self.backend.owner,'block')
    def tearDown(self):self.journal.db.close();self.tmp.cleanup()
    def test_real_read_write_64B_beats_and_tag_reuse(self):
        raw=bytes(range(256))*2
        self.assertEqual(self.m.transact(self.key,write=True,payload=raw),b'')
        write=self.m.last_receipt;self.assertEqual(len(write['fragments']),8)
        self.assertEqual(self.m.transact(self.key),raw);read=self.m.last_receipt
        self.assertEqual(read['byte_address'],write['byte_address'])
        self.assertEqual(len(read['actual_transactions']),16)
        self.assertFalse(self.backend.p.live)
        self.assertGreater(read['actual_transactions'][0]['generation'],write['actual_transactions'][0]['generation'])
        self.assertFalse(read['hardware_qualified']);self.assertFalse(read['full_program_qualified'])
    def test_partial_beat_RMW_preserved(self):
        self.m.transact(self.key,write=True,payload=bytes(range(64)))
        self.m.transact(self.key,write=True,payload=b'0123456789')
        receipt=self.m.last_receipt
        self.assertEqual(receipt['fragments'][0]['valid_byte_mask'],'0x3ff')
        self.assertTrue(any(r['direction']=='read' for r in receipt['actual_transactions']))
        self.assertEqual(bytes(self.backend.p.backing[('DeepSeek',0,67108864//32)])[10:32],bytes(range(10,32)))
        self.assertEqual(self.m.transact(self.key),b'0123456789')
    def test_provider_tap_consumes_real_receipt(self):
        tap=ProviderTap(self.m);tap.transact(self.key,write=True,payload=b'x'*64);tap.transact(self.key)
        self.assertIsNotNone(tap.events[-1]['actual_address_receipt'])
        self.assertEqual(tap.events[-1]['matched_writeback_sequence'],0)
    def test_wrong_source_PC_fail_closed(self):
        self.m.transact(self.key,write=True,payload=b'x'*64)
        events=list(self.backend.p.events)
        with self.assertRaisesRegex(ValueError,'PC/rank/generation'):
            prove_sector_span(events,model='DeepSeek',rank=0,PC=8,generation=11)
    def test_missing_reverse_never_drained(self):
        self.m.transact(self.key,write=True,payload=b'x'*64)
        events=[e for e in self.backend.p.events if e['event']!='validated_reverse_grant']
        with self.assertRaisesRegex(ValueError,'reverse debt'):
            prove_sector_span(events,model='DeepSeek',rank=0,PC=7,generation=11)
    def test_stale_reverse_tag_generation_rejected(self):
        self.m.transact(self.key,write=True,payload=b'x'*64)
        events=copy.deepcopy(list(self.backend.p.events))
        next(e for e in events if e['event']=='validated_reverse_grant')['generation']+=100
        with self.assertRaisesRegex(ValueError,'without source acceptance'):
            prove_sector_span(events,model='DeepSeek',rank=0,PC=7,generation=11)
    def test_failure_retains_source_journal_and_quarantines(self):
        with self.assertRaises(ValueError):self.m.transact(self.key)
        self.assertEqual(self.m.last_receipt['status'],'FAILED_EVIDENCE_RETAINED')
        with self.assertRaisesRegex(ValueError,'quarantined'):self.m.transact(self.key,write=True,payload=b'x'*64)
    def test_actual_provider_refill_drives_atomic_owner_and_keeps_calendar(self):
        from test_h4_c0_v1_owner_lock_addressed import controls,fragment
        lock,c=controls();c.update(source_PC=7,generation=11,SM=3)
        # Explicit protocol-only connection for the parent scratch SM3.
        for binding in lock.bindings.mapping.values():binding['SM']=3
        lock.bindings.mapping={(m,0,3):b for (m,_,_),b in lock.bindings.mapping.items()}
        for home in c['source_version_home_refs']+[c['destination_version_home_ref']]:home.update(generation=11,SM=3)
        token=lock.accept(c)
        raw=b'x'*64;self.backend.preload(self.key,raw)
        f=fragment(token);f.update(workspace_extent=self.backend.workspace_extent,byte_address=67108864,
            observed_payload_sha256=hashlib.sha256(raw).hexdigest(),provider_source_sha256=self.sha)
        self.assertEqual(self.m.transfer_to_owner(lock,token,f,self.key),raw)
        self.assertFalse(lock.owner(token)['provider_pending'])
        self.assertFalse(lock.contender_allowed(token[0]))
        lock.read_accept(token,0)
    def test_actual_payload_mismatch_retains_atomic_provider_debt(self):
        from test_h4_c0_v1_owner_lock_addressed import controls,fragment
        lock,c=controls();c.update(source_PC=7,generation=11,SM=3)
        lock.bindings.mapping={(m,0,3):dict(b,SM=3) for (m,_,_),b in lock.bindings.mapping.items()}
        for home in c['source_version_home_refs']+[c['destination_version_home_ref']]:home.update(generation=11,SM=3)
        token=lock.accept(c);self.backend.preload(self.key,b'x'*64)
        f=fragment(token);f.update(workspace_extent=self.backend.workspace_extent,byte_address=67108864,provider_source_sha256=self.sha)
        with self.assertRaisesRegex(ValueError,'byte/address contract mismatch'):
            self.m.transfer_to_owner(lock,token,f,self.key)
        self.assertTrue(lock.owner(token)['provider_pending'])
        self.assertFalse(lock.contender_allowed(token[0]))
    def test_actual_DS_source_operand_provider_and_V1_owner_composition(self):
        from h4_c0_parent_provider_join import ParentProviderJoin
        from h4_c0_ordered_movement import strict_api
        from test_h4_c0_v1_owner_lock_addressed import controls,fragment
        join=ParentProviderJoin();api=strict_api();choice=None
        for pc in join.catalog['PC_bindings']:
            for binding in pc['bindings']:
                record=join.catalog['templates'][binding['template']]
                if not record['execution_path'].startswith('forward_'):continue
                for ci,call in enumerate(record['calls']):
                    if call['dynamic_source_parameters']:continue
                    leaf=join.catalog['leaves'][call['leaf']]
                    if 'program' not in leaf:continue
                    code=leaf['program']['code'];specs=api.native_value_specs({'templates':{call['leaf']:leaf['program']}},call['leaf'])
                    for index,node in enumerate(code):
                        if node['op']!='AND' or len(node['src'])!=2 or specs[node['src'][0]]['bytes']<64:continue
                        choice=(pc,binding,ci,call,node,index,specs);break
                    if choice:break
                if choice:break
            if choice:break
        self.assertIsNotNone(choice)
        pc,binding,ci,call,node,index,specs=choice
        context=join.context('DeepSeek',pc['pc'],binding['rank'],0,11)
        owner=(context['PC'],tuple(context['writes']),context['rank'],0,11)
        backend,journal=actual_provider(pathlib.Path(self.tmp.name)/'native',owner)
        try:
            movement=AddressedMovement(backend,source_sha256=self.sha)
            lock,command=controls()
            lock.bindings.mapping={('DeepSeek',context['rank'],0):dict(next(iter(lock.bindings.mapping.values())),model='DeepSeek',rank=context['rank'],SM=0)}
            slot=32
            def home(value):
                nonlocal slot
                vectors=list(range(slot,slot+specs[value]['width']//4));slot+=len(vectors)
                return dict(version=value,lease='SOURCE_CONTROL_'+value,rank=context['rank'],SM=0,generation=11,physical_RF_id='CONTROL_RF',RF_vectors=vectors)
            command.update(source_PC=context['PC'],rank=context['rank'],SM=0,generation=11,
                family=context['family'],program_sha256=context['program_sha256'],template_id=call['leaf'],ordered_step_index=index,
                opcode=node['op'],source_attrs_rounding=node['attrs'],source_bittypes=[specs[value]['width']*8 for value in node['src']],destination_bittype=specs[node['dst']]['width']*8,
                source_version_home_refs=[home(value) for value in node['src']],destination_version_home_ref=home(node['dst']))
            token=lock.accept(command);key=('native',*owner,'source_operand');raw=b'x'*64;backend.preload(key,raw)
            f=fragment(token);f['identity'].update(version=node['src'][0],lease=command['source_version_home_refs'][0]['lease'])
            f.update(workspace_extent=backend.workspace_extent,byte_address=67108864,observed_payload_sha256=hashlib.sha256(raw).hexdigest(),provider_source_sha256=self.sha)
            ref=dict(parent_template=binding['template'],call_index=ci,invocation_index=0,template=call['leaf'],code_index=index,opcode=node['op'],attrs=node['attrs'],result_shape=node['shape'],operand='src:0',value=node['src'][0],logical_byte_offset=0,payload_bytes=64)
            result,joined=join.transfer_DS_native_operand(context,ref,movement,lock,token,f,key)
            self.assertEqual(result,raw);self.assertTrue(joined['source_binding_verified'])
            self.assertFalse(joined['hardware_qualified']);self.assertFalse(lock.owner(token)['provider_pending'])
            self.assertFalse(lock.contender_allowed(token[0]))
        finally:journal.db.close()
    def test_qwen_boolean_ACK_not_promoted_to_addressed_receipt(self):
        with self.assertRaisesRegex(ValueError,'boolean ACK insufficient'):
            AddressedMovement(types.SimpleNamespace(reverse_grant_ACK=True),source_sha256=self.sha,model='Qwen')

if __name__=='__main__':unittest.main()
