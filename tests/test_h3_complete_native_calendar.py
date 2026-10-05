"""Finite calendar controls: temporal, ownership, arithmetic-interface and replay."""
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('h3calendar', ROOT / 'tools/h3_complete_native_calendar.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class FiniteCalendarTests(unittest.TestCase):
    def test_both_pinned_program_demand_inventory_keeps_units_and_unknowns(self):
        base=ROOT/c.OUT/'h1_matched_execution_publication_r1'
        inventory=c.read_json(base/'both_program_demand_inventory.json.gz')
        self.assertEqual((inventory['DeepSeek']['PCs'],inventory['Qwen']['PCs']),(2213,1737))
        self.assertEqual((inventory['DeepSeek']['families'],inventory['Qwen']['families']),(30,21))
        for name in ['DeepSeek','Qwen']:
            rows=inventory[name]['PC_inventory']
            self.assertEqual([r['PC'] for r in rows],list(range(inventory[name]['PCs'])))
        from collections import Counter
        totals=Counter()
        for r in inventory['Qwen']['PC_inventory']:
            totals.update(r['native_primitive_commands'])
            self.assertEqual(r['source_shared_beat_bytes'],128)
            self.assertEqual(r['physical_shared_beat_bytes'],64)
            self.assertIsNone(r['physical_shared_transactions'])
        self.assertEqual(dict(totals),inventory['Qwen']['native_primitive_commands'])
        totals=Counter()
        for r in inventory['DeepSeek']['PC_inventory']:
            totals.update(r['source_instruction_instances'])
            for tid in r['source_template_calls']:self.assertIn(tid,inventory['DeepSeek']['templates'])
            self.assertIsNone(r['physical_RF_command_count'])
        self.assertEqual(dict(totals),inventory['DeepSeek']['source_instruction_instances'])
        self.assertFalse(inventory['complete_dynamic_movement_join'])
        self.assertIsNone(inventory['whole_token_latency'])
        with self.assertRaisesRegex(ValueError,'artifact pin'):
            c.inventory_h1_program_demands(b'forged opcode counts',b'forged export')

    def test_actual_CDC_finite_storage_retains_backpressure_and_reverse_unknown(self):
        base=ROOT/c.OUT/'h1_matched_execution_publication_r1'
        pins=json.loads((base/'CDC_source_pins.json').read_bytes())
        sources={n:gzip.decompress((base/(Path(n).name+'.gz')).read_bytes()) for n in pins}
        proof=c.h1_clock_crossing_obligations(sources,pins)
        self.assertEqual(proof['in_flight_storage_bits'],2355)
        self.assertEqual(proof['route_hold_fast_edges'],38)
        self.assertTrue(proof['route_counterexample']['identity_unchanged'])
        self.assertIsNone(proof['route_counterexample']['maximum_sink_wait'])
        self.assertIsNone(proof['source_H1_C0_V1_bridge_instantiation_mapping'])
        self.assertIsNone(proof['hardware_cycles_or_ns'])
        bad=dict(sources);name=next(iter(bad));bad[name]+=b'forged'
        with self.assertRaisesRegex(ValueError,'pin mismatch'):c.h1_clock_crossing_obligations(bad,pins)
        with self.assertRaisesRegex(ValueError,'complete actual'):
            c.h1_clock_crossing_obligations({},pins)

    def calibrated_H1(self):
        base=ROOT/c.OUT/'h1_matched_execution_publication_r1'
        sources={name:gzip.decompress((base/(Path(name).name+'.gz')).read_bytes()) for name in [
            'rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_scratch_service.sv','rtl/gpu/ot_gpu_full_sm_service.sv',
            'rtl/test/full_sm_service/tb_full_service_exact.sv','rtl/test/full_sm_service/tb_storage.sv']}
        verdict=json.loads((base/'verdict.json').read_bytes());review=json.loads((base/'review.json').read_bytes())
        logs={n:(base/n).read_bytes() for n in ['actual_sim.log','storage_sim.log']}
        return base,verdict,review,logs,sources,c.h1_calibrated_service_contract(verdict,review,logs,sources)

    def test_matched_executed_H1_contract_rejects_receipt_log_and_source_mutants(self):
        base,v,r,logs,sources,contract=self.calibrated_H1()
        self.assertEqual(contract['SIMD_done_after_accept_edges'],12)
        self.assertEqual(contract['SIMD_accept_through_sink_release_edges'],14)
        self.assertFalse(contract['SS_FF_verified']);self.assertIsNone(contract['hardware_clock_ns'])
        altered=copy.deepcopy(v);altered['source_commit']='forged'
        with self.assertRaisesRegex(ValueError,'immutable'):c.h1_calibrated_service_contract(altered,r,logs,sources)
        with self.assertRaisesRegex(ValueError,'log source pin'):c.h1_calibrated_service_contract(v,r,dict(logs,**{'actual_sim.log':logs['actual_sim.log']+b'\n'}),sources)
        with self.assertRaisesRegex(ValueError,'bench source pin'):c.h1_calibrated_service_contract(v,r,logs,dict(sources,**{'rtl/gpu/ot_gpu_rf_service.sv':b'wrong'}))

    def test_source_nested_arbitration_starves_write_without_sink_stalls_and_policy_fixes_it(self):
        base,v,r,logs,sources,contract=self.calibrated_H1();proof=c.prove_reserved_h1_fair_owner(contract)
        self.assertTrue(proof['baseline_starvation_state_repeats'])
        self.assertEqual(proof['baseline_starvation_reachable_prefix_from_reset'][-1]['state'],proof['baseline_nested_starvation_cycle'][-1]['state'])
        self.assertFalse(any(t['grant']['host_write'] for t in proof['baseline_nested_starvation_cycle']))
        self.assertEqual(proof['all_persistent_ports_granted'],{'host_read':3,'host_write':3,'SIMD':3})
        self.assertEqual(proof['local_wait_bounds']['host_write']['arrival_at_drained_boundary_wait_upper'],17)
        self.assertEqual(proof['local_wait_bounds']['host_read']['arrival_at_drained_boundary_wait_upper'],16)
        self.assertEqual(proof['local_wait_bounds']['SIMD']['arrival_at_drained_boundary_wait_upper'],5)
        self.assertFalse(proof['complete_production_wait_admission']);self.assertFalse(proof['hardware_policy_installed'])
        self.assertTrue(proof['unfinished_atomic_command_may_not_release_on_local_RF_idle'])
        bad=copy.deepcopy(contract);bad['service_edges']['SIMD']=1
        with self.assertRaisesRegex(ValueError,'actual H1'):c.prove_reserved_h1_fair_owner(bad)

    def test_actual96_publication_packets_bind_real_homes_and_pay_partial_RMW(self):
        base,v,r,logs,sources,contract=self.calibrated_H1()
        projection=json.loads(gzip.decompress((base/'PC0_projection.json.gz').read_bytes()))
        homes={int(k):v for k,v in json.loads(gzip.decompress((base/'PC0_home_subset.json.gz').read_bytes())).items()}
        cal=c.compile_reserved_h1_publications(projection,homes,contract)
        self.assertEqual(cal['registered_version_home_clients'],2208)
        self.assertEqual(cal['packet_counts'],{'partial_vector_RMW_read':288,'both_mirror_write':15648,'actual_publication_readback':15648})
        self.assertEqual(cal['max_one_SM_reference_edges'],64)
        self.assertEqual(cal['serialized_per_die_reference_edge_upper'],824)
        self.assertFalse(cal['partial_RMW_assembly']['physical_merge_endpoint_bound'])
        self.assertFalse(cal['partial_RMW_assembly']['merge_delay_credited_as_zero'])
        self.assertEqual(cal['existing_V1_C0_I64_provider_cost_added'],0)
        self.assertIsNone(cal['whole_token_latency_ns'])
        parent_owners={}
        for packet in cal['packets']:
            h=homes[packet['provider_reference']];self.assertEqual(h['version'],packet['version'])
            self.assertIn(packet['rank'],h['rank_group']);self.assertEqual(packet['SM'],h['SM'])
            key=(packet['rank'],packet['SM'],packet['provider_reference'])
            parent_owners.setdefault(key,packet['source_owner']);self.assertEqual(parent_owners[key],packet['source_owner'])
            self.assertTrue(packet['C0_owner_must_hold_across_all_home_packets'])
            if packet['port']=='host_write':self.assertEqual(packet['physical_mirror_write_bytes'],1024)
            else:
                self.assertEqual(packet['read_pair_response_bytes'],1024)
                self.assertEqual(packet['RF_read_addresses'],[packet['RF_slot'],packet['RF_slot']])
        corrupt=copy.deepcopy(projection);corrupt['publications'][0]['terminal_events'].pop()
        with self.assertRaisesRegex(ValueError,'source pin'):c.compile_reserved_h1_publications(corrupt,homes,contract)
        broken=dict(homes);index=projection['publications'][0]['identity']['home_indices'][0]
        broken[index]=dict(homes[index],version='foreign')
        with self.assertRaisesRegex(ValueError,'source pin'):c.compile_reserved_h1_publications(projection,broken,contract)

    def test_actual_H1_leaf_edges_and_nonfinite_hold_source_proof(self):
        base=ROOT/c.OUT/'pc10_exact_home_lineage_r1'
        sources={p.name[:-3]:gzip.decompress(p.read_bytes()) for p in base.glob('ot_gpu*.sv.gz')}
        inventory=[dict(rank=r,die=r,SM=s) for r in range(96) for s in range(32)]
        proof=c.derive_h1_production_wait_obligations(sources,inventory)
        self.assertEqual(proof['inventory']['SM_instances'],3072)
        self.assertEqual(proof['inventory']['RF_external_request_ports_total'],9216)
        self.assertEqual(len(proof['all_ready_positive_control']['read']),3)
        self.assertEqual(len(proof['all_ready_positive_control']['write']),2)
        self.assertFalse(proof['finite_contender_count_alone_sufficient']);self.assertFalse(proof['software_ticks_converted'])
        for row in proof['unbounded_reachable_credit_hold_witnesses']:
            after,accepted=c.h1_rf_control_step(tuple(row['reachable_state']),**row['inputs'])
            self.assertEqual(list(after),row['reachable_state']);self.assertFalse(any(accepted.values()))
        with self.assertRaisesRegex(ValueError,'inventory'):c.derive_h1_production_wait_obligations(sources,inventory[:-1])
        with self.assertRaisesRegex(ValueError,'actual H1'):c.derive_h1_production_wait_obligations(dict(sources,**{'ot_gpu_rf_service.sv':b'fake'}),inventory)

    def test_actual_H1_persistent_read_write_alternate_only_when_sinks_drain(self):
        state=(False,False,False,False);grants=[]
        for edge in range(20):
            state,events=c.h1_rf_control_step(state,read=True,write=True,response_ready=True,ack_ready=True)
            if events['read_accept']:grants.append('read')
            if events['write_accept']:grants.append('write')
        self.assertEqual(grants,['read','write']*4)
        held=(False,True,False,True)
        self.assertEqual(c.h1_rf_control_step(held,read=True,write=True)[0],held)

    def lineage_fixture(self):
        base=ROOT/c.OUT/'pc10_exact_home_lineage_r1'
        state=gzip.decompress((base/'ds_hbm_finite_state_homes_r30.py.gz').read_bytes())
        binding=gzip.decompress((base/'ds_hbm_storage_home_binding_r41.py.gz').read_bytes())
        native={'templates':{'t':{'code':[{'op':'CONST','src':[],'dst':'v','shape':[4],'attrs':{'dtype':'F32'}}],
            'outputs':{'data':'v'}}},'instructions':[{'pc':0,'rank_bindings':[{'rank':0,'template':'t'}],
            'writes':[{'version':'produced','home_indices':[],'native_result_binding':{'result':'data'}}]}]}
        homes=[{'version':'original','rank_group':[0],'home':{'class':'RF','slot_first':7}}]
        manifest={'native_program_sha256':'a'*64,'initial_versions':[], 'query_field_homes':{'rows':[]}}
        ns={'__name__':'retained_fixture'};exec(state,ns)
        directory=ns['compile_directory'](native,manifest['native_program_sha256'])
        bound,bound_homes=ns['patch_homes'](copy.deepcopy(native),copy.deepcopy(homes),directory)
        for h in bound_homes[len(homes):]:h['word_count']=h['binding']['bytes']//4
        return native,homes,manifest,bound,bound_homes,state,binding

    def test_exact_lineage_regenerates_extension_without_mutating_input(self):
        n,h,m,b,bh,s,t=self.lineage_fixture();original=copy.deepcopy((n,h,m,b,bh))
        proof=c.join_ds_pc10_home_lineage(n,h,m,b,bh,state_source=s,binding_source=t)
        self.assertEqual((n,h,m,b,bh),original)
        self.assertEqual(proof['appended_state_homes'],1)
        self.assertFalse(proof['production_PC9_bytes_verified']);self.assertIsNone(proof['physical_endpoint_waits'])
        self.assertFalse(proof['hardware_qualified']);self.assertFalse(proof['selected_L2_reservation_installed'])

    def test_exact_lineage_refuses_prefix_extension_native_and_source_mutants(self):
        n,h,m,b,bh,s,t=self.lineage_fixture()
        for target,key,value in [('prefix','slot_first',8),('extension','base',33554944),('native','home_indices',[])]:
            bn=copy.deepcopy(b);hh=copy.deepcopy(bh)
            if target=='prefix':hh[0]['home'][key]=value
            elif target=='extension':hh[1]['home'][key]=value
            else:bn['instructions'][0]['writes'][0][key]=value
            with self.assertRaisesRegex(ValueError,'prefix changed|extension mismatch|write lineage mismatch'):
                c.join_ds_pc10_home_lineage(n,h,m,bn,hh,state_source=s,binding_source=t)
        with self.assertRaisesRegex(ValueError,'immutable state'):
            c.join_ds_pc10_home_lineage(n,h,m,b,bh,state_source=s+b'\n',binding_source=t)
        with self.assertRaises(ValueError):c.join_ds_pc10_home_lineage(n,h,m,b,bh[:-1],state_source=s,binding_source=t)

    def test_compact_typed_journal_roundtrip_digest_index_and_online_drain(self):
        import tempfile,hashlib,sys
        sys.path.insert(0,'/home/ubuntu/OpenTallas/tools')
        import hbm_bound_event_journal_r30 as original
        from hbm_provider_microvm_r21 import Identity
        with tempfile.TemporaryDirectory() as tmp:
            budget=c.CompactJournalBudget(Path(tmp)/'journal',1<<24)
            provider=c.compact_sector_provider_class(original.BoundSectorProvider)(
                {('DeepSeek',95):[dict(base=0,bytes=32)]},journal_budget=budget,tags=1,
                allocation_identity=dict(address_class='scratch',native_owner=[0,['DeepSeek.0.attn_pre.50'],95,0,1]))
            expected=[];digest=hashlib.sha256()
            for serial in range(40):
                write=serial%2==0;payload=bytes([serial])*32 if write else b''
                begin=len(provider.events)
                t=provider.submit(Identity('DeepSeek',95,1,0,serial,0),write=write,payload=payload)
                returned=provider.wait(t)
                if not write:self.assertEqual(returned,bytes([serial-1])*32)
                provider.finish(t)
                chunk=list(provider.events[begin:]);expected.extend(chunk)
                for event in chunk:
                    raw=json.dumps(event,sort_keys=True,separators=(',',':')).encode();digest.update(len(raw).to_bytes(8,'little')+raw)
            self.assertEqual(list(provider.events),expected)
            span=provider.events[127:139]
            self.assertEqual(list(span),expected[127:139]);self.assertEqual(list(span),expected[127:139])
            self.assertEqual(len(span),12)
            from h3_ds_query_provider_r36 import SizedSlice
            self.assertEqual(len(SizedSlice(span)),12);self.assertEqual(list(SizedSlice(span)),expected[127:139])
            self.assertEqual(provider.events[-1],expected[-1])
            self.assertEqual(provider.events.digest.hexdigest(),digest.hexdigest())
            self.assertEqual(provider.events.validator.live,{})
            self.assertLess(provider.events.path.stat().st_size,300*160)
            self.assertTrue(any('payload_sha256' in event for event in expected))
            provider.events.close();self.assertEqual(list(provider.events[:7]),expected[:7]);budget.db.close()

    def test_compact_actual_source_RF_publish_and_write_checksum_fault(self):
        import tempfile,sys,hashlib
        import numpy as np
        sys.path.insert(0,'/home/ubuntu/OpenTallas/tools')
        import hbm_bound_event_journal_r30 as original
        from h3_ds_checkpoint_provider_r30 import Provider,RF_BYTES
        from h3_ds_query_provider_r36 import SizedRF
        from hbm_provider_microvm_r21 import Identity
        actual=c.compact_sector_provider_class(original.BoundSectorProvider)
        with tempfile.TemporaryDirectory() as tmp:
            budget=c.CompactJournalBudget(Path(tmp)/'journal',1<<24)
            writer=Provider.__new__(Provider)
            writer.__dict__.update(generation=1,published={},views={},locations={},rf=SizedRF({}),seq=0,trace=[],journal_budget=budget,
                homes=[dict(version='source-v',rank_group=[0],SM=0,partition='linear',word_count=16,home=dict(slot_first=0,vectors=1,**{'class':'RF'}))])
            writer.rf[0]=actual({('DeepSeek',0):[dict(base=0,bytes=RF_BYTES)]},journal_budget=budget,allocation_identity=dict(address_class='RF',rank=0))
            values=np.arange(16,dtype=np.float32);identity=dict(PC=0,rank=0,generation=1,version='source-v',home_indices=[0])
            receipt=writer.publish(identity,{'data':values},{'result':'out'})
            self.assertEqual(receipt['payload_sha256']['data'],hashlib.sha256(values.tobytes()).hexdigest())
            self.assertEqual(receipt['pending_obligations'],0);np.testing.assert_array_equal(writer.published['source-v',0],values)
            self.assertEqual(writer.rf[0].events.counts['software_backing_visible'],4)
            writer.rf[0].events.close();budget.db.close()
        with tempfile.TemporaryDirectory() as tmp:
            budget=c.CompactJournalBudget(Path(tmp)/'journal',1<<20)
            provider=actual({('DeepSeek',0):[dict(base=0,bytes=32)]},journal_budget=budget,tags=1)
            tx=provider.submit(Identity('DeepSeek',0,1,0,0,0),write=True,payload=bytes(32))
            tx.payload=bytes([1])*32
            with self.assertRaisesRegex(ValueError,'payload checksum changed'):provider.wait(tx)
            self.assertEqual(provider.events[-1]['event'],'software_backing_visible')
            self.assertTrue(provider.events.validator.live)
            provider.events.file.close();provider.events.index.close();budget.db.close()

    def test_compact_source_receipt_shapes_null_signed_and_archived_span_reader(self):
        import tempfile
        event=dict(event='actual_native_metadata',allocation_identity=None,phase_costs=None,
                   record=dict(shape=[-1,2],generation=2**63,source_versions=['DeepSeek.-1.h.0'],payload_sha256={'data':'a'*64}))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'journal';budget=c.CompactJournalBudget(root,1<<20);journal=c.CompactDiskEvents(budget)
            journal.append(event);journal.close()
            self.assertEqual(list(journal),[event])
            reader=c.open_compact_journal_reader(root,journal.id)
            self.assertEqual(list(reader[:1]),[event]);reader.budget.db.close()
            self.assertTrue(journal.file.closed)
            budget.db.close()

    def test_source_sized_compact_pc0_is_full96_and_never_sample_ratio(self):
        base=ROOT/c.OUT/'compact_provider_journal_r1'
        source=json.loads(gzip.decompress((base/'source_projection.json.gz').read_bytes()))
        homes={int(k):v for k,v in source['homes'].items()}
        model=c.size_compact_pc0_journals(source['packet'],source['phase_events'],source['native_PC0'],homes)
        self.assertEqual(model['ranks'],96);self.assertFalse(model['sampled_ratio_used'])
        self.assertEqual(model['provider_phase_disk_reservation_bytes'],140850600720)
        self.assertEqual(model['source_publication_events'],5664000)
        self.assertTrue(all((r['read_sector32'],r['write_sector32'])==(2568,5128) for r in model['source_publication_per_rank']))
        bad=copy.deepcopy(source['native_PC0']);bad['rank_bindings'].pop()
        with self.assertRaisesRegex(ValueError,'actual96rank'):c.size_compact_pc0_journals(source['packet'],source['phase_events'],bad,homes)
        badhomes=copy.deepcopy(homes);first=source['native_PC0']['writes'][0]['home_indices'][0];badhomes[first]['version']='wrong'
        with self.assertRaisesRegex(ValueError,'writer home'):c.size_compact_pc0_journals(source['packet'],source['phase_events'],source['native_PC0'],badhomes)

    def test_compact_fault_records_stale_reverse_and_refuses_premature_reuse(self):
        import tempfile
        event=dict(event='request_accept',identity=dict(target='DeepSeek',rank=0,epoch=1,pc=0,serial=1,sector=0),tag=0,generation=1,tick=0,hardware=False)
        with tempfile.TemporaryDirectory() as tmp:
            budget=c.CompactJournalBudget(Path(tmp)/'journal',1<<20);journal=c.CompactDiskEvents(budget)
            journal.append(event)
            with self.assertRaisesRegex(ValueError,'before actual lifecycle drain'):journal.close()
            with self.assertRaisesRegex(ValueError,'premature tag reuse'):journal.append(dict(event,generation=2))
            self.assertEqual(len(journal),2);self.assertEqual(journal[-1]['generation'],2)
            self.assertEqual(len(journal.validator.live),1)
            with self.assertRaisesRegex(ValueError,'faulted'):journal.append(event)
            journal.file.close();journal.index.close();budget.db.close()
        validator=c.CompactLifecycle();validator.accept(event)
        with self.assertRaisesRegex(ValueError,'stale identity'):validator.accept(dict(event,event='validated_reverse_grant',generation=2))
        for value in (-1,2**64):
            with self.assertRaisesRegex(ValueError,'width'):c.compact_uint(value)
        import io
        for encoded in (b'\x80',b'\x80\x00',b'\xff'*10+b'\x01'):
            with self.assertRaises(ValueError):c.compact_read_uint(io.BytesIO(encoded))

    def test_pc0_projection_preserves_phase_padding_and96rank_scope(self):
        base=ROOT/c.OUT/'provider_shared_driver_join_r2'
        inputs=json.loads((base/'pc0_projection_inputs.json').read_text())
        actual=c.project_pc0_provider_journal(**inputs)
        self.assertEqual(actual,json.loads((base/'pc0_96rank_projection.json').read_text()))
        self.assertEqual(actual['sector_transactions_upper_all_ranks'],149409408)
        self.assertEqual(actual['provider_events_upper_all_ranks'],1097372832)
        self.assertIsNone(actual['exact_full_PC0_event_count'])
        self.assertFalse(actual['production_96rank_prefix_completed'])
        bad=copy.deepcopy(inputs);bad['phase_schema']['write'].remove('write_residence_reserved')
        with self.assertRaisesRegex(ValueError,'phase schema'):c.project_pc0_provider_journal(**bad)
        bad=copy.deepcopy(inputs);bad['packet']['sector_transactions_upper_per_rank']=1
        with self.assertRaisesRegex(ValueError,'below byte floor'):c.project_pc0_provider_journal(**bad)

    def test_pc0_phase_row_upper_does_not_use_sample_density_for_admission(self):
        base=ROOT/c.OUT/'provider_shared_driver_join_r2'
        record=json.loads((base/'pc0_phase_row_upper.json').read_text())
        self.assertFalse(record['empirical_event_density_used_for_this_bound'])
        self.assertIsNone(record['actual_sqlite_footprint'])
        self.assertIsNone(record['actual_PC0_runtime_seconds'])
        self.assertEqual(len(record['phase_rows']['read']),7)
        self.assertEqual(len(record['phase_rows']['write']),8)
        for rows in record['phase_rows'].values():
            for row in rows:
                self.assertGreater(row['zlib_bytes_upper'],row['json_bytes_upper'])
                self.assertEqual(row['journal_reserve_bytes_upper'],8*(row['zlib_bytes_upper']+64))
        self.assertFalse(record['full_prefix_executed'])

    def test_actual_provider_shared_join_retains_both_mirror_and_source_journal_evidence(self):
        base=ROOT/c.OUT/'provider_shared_driver_join_r2'
        result=json.loads(gzip.decompress((base/'execution.json.gz').read_bytes()))
        self.assertEqual(len(result['actual_source_receipts']),512)
        self.assertEqual(result['actual_shared_movements']['scratch64'],9216)
        self.assertEqual(len(result['actual_movement_calls']),1152)
        mirror=result['actual_RF_mirror_journal']
        self.assertEqual(mirror['actual_RF_mirrors'],2);self.assertEqual(mirror['required_write_sectors'],2048)
        self.assertTrue(mirror['all_required_mirror_sectors_reverse_drained'])
        self.assertTrue(result['source_global_view_released']);self.assertFalse(result['source_version_retired'])
        self.assertEqual(result['total_operand_and_staging_bound_bytes'],41472)
        for receipt in result['actual_source_receipts']:
            self.assertTrue(receipt['source_operand_proof']['matching_reverse_drained'])
            self.assertTrue(receipt['source_operand_proof']['dispatch_binding_checked'])
        self.assertEqual(result['production_calls_closed'],0);self.assertFalse(result['full_program_executed'])

    def test_full_driver_and_provider_join_refuse_unpinned_family_callbacks(self):
        class Callback:
            def run(self):return 'golden operator'
            def run_buffer(self):return 'golden operator'
        with self.assertRaisesRegex(ValueError,'exact df6'):
            c.execute_ds_provider_group128(Callback(),10,0,generation=1,identity={},source_store_view={},shared_factory=None,primitive_sources={})
        with self.assertRaisesRegex(ValueError,'exact retained'):
            c.execute_ds_driver_with_group128(Callback(),None,shared_factory=None,primitive_sources={})

    def group_execution_fixture(self, *, failure=None, capture_journals=False):
        import ast,hashlib,sys,tempfile
        import numpy as np
        from collections import Counter
        base=ROOT/'results/uarch/h3_complete_native_calendar_20261002/group128_execution_join_r1'
        pins=json.loads((base/'source_pins.json').read_text());raws={}
        for name,pin in pins.items():
            if pin.get('archive_is_projection'):continue
            raw=gzip.decompress((base/'source_inputs'/pin['archive']).read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(),pin['sha256']);raws[name]=raw
        vm_tree=ast.parse(raws['tools/h3_qwen_bounded_native.py']);nodes=[]
        nodes.extend(n for n in vm_tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='COMMON_NATIVE' for x in n.targets))
        nodes.append(next(n for n in vm_tree.body if isinstance(n,ast.ClassDef) and n.name=='NativePrimitiveVM'))
        nodes.append(next(n for n in ast.parse(raws['tools/h3_qwen_complete_native.py']).body if isinstance(n,ast.FunctionDef) and n.name=='poszero'))
        ns=dict(np=np,F=np.float32,Counter=Counter)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned-generic-primitive-VM','exec'),ns)
        VM=ns['NativePrimitiveVM'];inventory_raw=(ROOT/c.OUT/'portable_input_closure_r1/r34_portable_r4/source_inventory.json.gz').read_bytes()
        def pinned(path,commit):
            self.assertEqual(commit,'ba0c1ba0625b58add3216d77a91e010a1daece6f')
            self.assertTrue(path.endswith('r34_portable_r4/source_inventory.json.gz'));return inventory_raw
        ns.update(gzip=gzip,json=json,hashlib=hashlib,pinned=pinned,NativePrimitiveVM=VM)
        tree=ast.parse(raws['tools/h4_c0_group_operand_tiles.py'])
        nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.Assign))]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'Sagan-2d05-current-group-plan','exec'),ns)
        plan=ns['GroupOperandTiles']();pc=next(iter(plan.parents));data=np.random.default_rng(29).standard_normal((8,8,1024)).astype(np.float32)
        data[:,0,0]=[1e20,1,-1e20,1,1,1,1,1]
        if failure=='tile_source':
            original_tile=plan.tile
            def bad_tile(*args):
                tile=original_tile(*args);tile['source_spans'][0]['source_rank']+=1;return tile
            plan.tile=bad_tile
        class Source:
            def __init__(self):self.live={};self.acquired=0;self.released=0
            def acquire(self,span,owner):
                self.acquired+=1;key=(owner['tile'],span['source_rank']);self.live[key]=span
                group,j=divmod(span['source_rank'],8);raw=data[j,group,span['local_word_first']:span['local_word_first']+128].tobytes()
                return dict(lease=key,state='visible',version=span['source_version'],rank=span['source_rank'],generation=owner['generation']+(failure=='source_generation'),
                    first=span['local_word_first'],words=128,data=raw,payload_sha256=hashlib.sha256(raw).hexdigest())
            def release(self,record,owner):self.live.pop(record['lease']);self.released+=1
        class Output:
            def __init__(self):self.data=np.empty(8192,np.uint32);self.spans=0
            def write_span(self,tile,owner,raw):
                first=tile['output_flat_word_first'];self.data[first:first+128]=np.frombuffer(raw,np.uint32);self.spans+=1
                return dict(version=tile['destination_version'],rank=owner['rank'],generation=owner['generation'],first=first,bytes=512,
                    payload_sha256=hashlib.sha256(raw).hexdigest(),pending_obligations=int(failure=='output_debt'))
        snapshots=ROOT/c.OUT/'ordered_operand_journal_r1/source_inputs'
        saved=sys.modules.get('hbm_provider_microvm_r21');spec=importlib.util.spec_from_file_location('hbm_provider_microvm_r21',snapshots/'hbm_provider_microvm_r21.py')
        P=importlib.util.module_from_spec(spec);sys.modules[spec.name]=P;spec.loader.exec_module(P)
        try:
            spec=importlib.util.spec_from_file_location('group_disk_journal',snapshots/'hbm_bound_event_journal_r30.py');J=importlib.util.module_from_spec(spec);spec.loader.exec_module(J)
            source=Source();output=Output();memories={}
            with tempfile.TemporaryDirectory() as tmp:
                budget=J.JournalBudget(Path(tmp)/'actual',536870912)
                class Memory:
                    def __init__(self,owner):
                        self.owner=owner;self.base=16777216+owner['SM']*65536;self.extent=dict(base=self.base,bytes=65536,rank=0,SM=owner['SM'])
                        if failure=='shared_capacity':self.extent['bytes']=524288
                        self.p=J.BoundSectorProvider({('DeepSeek',0):[dict(base=self.base,bytes=65536)]},journal_budget=budget,tags=1,allocation_identity=owner)
                        self.serial=0
                    def transact(self,offset,*,write,payload,length):
                        out=[]
                        for first in range(0,length,32):
                            identity=P.Identity('DeepSeek',0,1,pc,self.serial,(self.base+offset+first)//32);self.serial+=1
                            tx=self.p.submit(identity,write=write,payload=payload[first:first+32] if write else b'');out.append(self.p.wait(tx));self.p.finish(tx)
                        return b''.join(out)
                def factory(owner):
                    if owner['SM'] not in memories:memories[owner['SM']]=Memory(owner)
                    memory=memories[owner['SM']]
                    if memory.p.live:raise ValueError('tile owner reused before reverse drain')
                    memory.owner=owner;memory.p.allocation_identity=owner
                    return memory
                try:
                    calls=[]
                    result=c.execute_ds_group128_tiles(plan,pc,0,1,source,factory,dict(bounded_native=raws['tools/h3_qwen_bounded_native.py'],arithmetic_helpers=raws['tools/h3_qwen_complete_native.py']),output,movement_observer=calls.append if capture_journals else None)
                    if capture_journals:result['control_movement_calls']=calls
                    summaries=[m.p.events.summary() for m in memories.values()]
                    if capture_journals:result['control_disk_journal_events']=[dict(SM=sm,journal_id=m.p.events.id,events=list(m.p.events)) for sm,m in memories.items()]
                except ValueError as error:
                    return dict(error=str(error),source_live=len(source.live),source_released=source.released,output_spans=output.spans)
                finally:budget.db.close()
                result['control_source_leases']=dict(acquired=source.acquired,released=source.released,live=len(source.live))
                result['control_disk_journals']=[{k:v for k,v in x.items() if k!='path'} for x in summaries]
                result['control_output_bits']=output.data.tolist()
                # Numerical oracle is a TEST only, not a calendar cost source.
                expected=((data[0]+data[1])+(data[2]+data[3]))+((data[4]+data[5])+(data[6]+data[7]))
                bits=expected.view(np.uint32);expected=(bits+np.uint32(32767)+((bits>>16)&np.uint32(1)))&np.uint32(0xffff0000)
                np.testing.assert_array_equal(output.data,expected.reshape(-1))
                return result
        finally:
            if saved is None:sys.modules.pop('hbm_provider_microvm_r21',None)
            else:sys.modules['hbm_provider_microvm_r21']=saved

    def test_executable_all64_group_tiles_use_real_finite_shared_journals(self):
        result=self.group_execution_fixture()
        self.assertNotIn('error',result);self.assertEqual(result['tiles_executed'],64)
        self.assertEqual(result['actual_shared_movements'],dict(sector32=18432,scratch64=9216,write512=576,read512=576))
        self.assertEqual(result['control_source_leases'],dict(acquired=512,released=512,live=0))
        self.assertEqual(result['executed_primitive_scalars']['CONST'],4)
        self.assertEqual(result['peak_RF_vectors'],16)
        self.assertFalse(result['full_program_executed']);self.assertIsNone(result['whole_token_latency'])

    def test_actual_group_journal_binds_selected_interval_and_rejects_unknown_waits(self):
        base=ROOT/c.OUT/'group128_execution_join_r1'
        control=json.loads(gzip.decompress((base/'actual_group128_execution.json.gz').read_bytes()))
        inventory=json.loads(gzip.decompress((ROOT/c.OUT/'portable_input_closure_r1/r34_portable_r4/source_inventory.json.gz').read_bytes()))
        program=dict(templates=inventory['native_templates'],instructions=[dict(pc=r['pc'],rank_bindings=r['actual_rank_template_bindings']) for r in inventory['corrected_PC_bindings']])
        row=json.loads(gzip.decompress((base/'source_inputs/selected_group_call.json.gz').read_bytes()))['calls'][0]
        bounds=dict(backend_bound_edges=1,consumer_bound_edges=1,reverse_bound_edges=1)
        result=c.bind_executed_group_shared64(control,program,row,'reviewed-r34-interval',bounds)
        commands=result['calls'][row['call_id']]['commands']
        self.assertEqual(len(commands),9216);self.assertEqual({x['SM'] for x in commands},set(range(32)))
        self.assertEqual(result['production_calls_closed'],0)
        with self.assertRaises(ValueError):c.bind_executed_group_shared64(control,program,row,'reviewed-r34-interval',dict(bounds,reverse_bound_edges=None))
        bad=dict(row,rank=95)
        with self.assertRaisesRegex(ValueError,'owner'):c.bind_executed_group_shared64(control,program,bad,'reviewed-r34-interval',bounds)
        small=dict(control,control_movement_calls=[copy.deepcopy(control['control_movement_calls'][0])])
        small['control_movement_calls'][0]['source_reference']['attrs']['name']='unresolved'
        with self.assertRaisesRegex(ValueError,'opcode attrs'):c.bind_executed_group_shared64(small,program,row,'reviewed-r34-interval',bounds)

    def test_group_execution_rejects_unresolved_source_contributor_mapping(self):
        result=self.group_execution_fixture(failure='tile_source')
        self.assertIn('span mapping mismatch',result['error']);self.assertEqual(result['source_live'],0)

    def test_group_execution_rejects_arithmetic_callback_or_changed_source(self):
        with self.assertRaisesRegex(ValueError,'closure'):
            c.load_group_native_primitive_factory({'golden':lambda:None})
        with self.assertRaisesRegex(ValueError,'pin mismatch'):
            c.load_group_native_primitive_factory(dict(bounded_native=b'changed',arithmetic_helpers=b'changed'))

    def test_executable_group_failure_retains_source_lease_and_no_successful_commit(self):
        for failure in ('source_generation','output_debt'):
            result=self.group_execution_fixture(failure=failure)
            self.assertIn('error',result);self.assertGreater(result['source_live'],0);self.assertEqual(result['source_released'],0)
        result=self.group_execution_fixture(failure='shared_capacity')
        self.assertIn('error',result);self.assertEqual(result['source_live'],0)

    def actual_operand_journal_fixture(self):
        import sys,tempfile
        snapshots=ROOT/'results/uarch/h3_complete_native_calendar_20261002/ordered_operand_journal_r1/source_inputs'
        import hashlib
        pins=json.loads((snapshots.parent/'journal_path_and_join_handoff.json').read_text())['source_pins']
        for name in ('hbm_provider_microvm_r21.py','hbm_bound_event_journal_r30.py'):
            self.assertEqual(hashlib.sha256((snapshots/name).read_bytes()).hexdigest(),pins[name]['sha256'])
        saved=sys.modules.get('hbm_provider_microvm_r21')
        spec=importlib.util.spec_from_file_location('hbm_provider_microvm_r21',snapshots/'hbm_provider_microvm_r21.py')
        provider=importlib.util.module_from_spec(spec);sys.modules[spec.name]=provider;spec.loader.exec_module(provider)
        try:
            spec=importlib.util.spec_from_file_location('test_disk_journal',snapshots/'hbm_bound_event_journal_r30.py')
            journal=importlib.util.module_from_spec(spec);spec.loader.exec_module(journal)
            with tempfile.TemporaryDirectory() as tmp:
                budget=journal.JournalBudget(Path(tmp)/'actual',1048576)
                backend=journal.BoundSectorProvider({('DeepSeek',0):[dict(base=67108864,bytes=512)]},journal_budget=budget,tags=1)
                for serial in range(16):
                    identity=provider.Identity('DeepSeek',0,1,18,serial,67108864//32+serial)
                    tx=backend.submit(identity,write=True,payload=bytes(range(32)))
                    backend.wait(tx);backend.finish(tx)
                events=list(backend.events);summary=backend.events.summary();budget.db.close()
        finally:
            if saved is None:sys.modules.pop('hbm_provider_microvm_r21',None)
            else:sys.modules['hbm_provider_microvm_r21']=saved
        node=dict(op='LOAD',dst='v0',src=[],shape=[128],attrs={'name':'x','dtype':'F32'})
        program=dict(templates={'template':{'code':[node],'providers':{'x':dict(shape=[128],dtype='F32')}}},
            instructions=[dict(pc=18,rank_bindings=[dict(rank=0,template='template')])])
        ref=dict(template='template',code_index=0,opcode='LOAD',attrs=node['attrs'],result_shape=[128],
            operand='dst',value='v0',logical_byte_offset=0,payload_bytes=512)
        binding=dict(PC=18,rank=0,SM=0,generation=1,lease='actual-control-lease',lease_state='active',
            version='native.v0',native_SSA_value='v0',logical_base=67108864,allocation_bytes=512,
            operand_base_offset=0,shared_tile_offset=0,shared_capacity_bytes=65536,provider_tag_capacity=1)
        translation=dict(rank=0,SM=0,generation=1,version='native.v0',lease='actual-control-lease',
            logical_base=67108864,physical_base=1048576,bytes=512,AW=34)
        return program,ref,binding,events,translation,summary

    def test_actual_disk_operand_journal_source_span_and_explicit_translation(self):
        program,ref,binding,events,translation,_=self.actual_operand_journal_fixture()
        result=c.verify_ds_operand_journal(program,'template',ref,binding,iter(events),translation=translation)
        self.assertEqual((result['sector32_transactions'],result['scratch64_transactions'],result['physical_byte_address']),(16,8,1048576))
        self.assertTrue(result['matching_reverse_drained']);self.assertEqual(result['additional_provider_RF_C0_I64_charge'],0)
        self.assertIsNone(result['actual_lease_acquisition_and_release_journal'])
        unknown=c.verify_ds_operand_journal(program,'template',ref,binding,iter(events))
        self.assertIsNone(unknown['physical_byte_address']);self.assertFalse(unknown['whole_program_movement_complete'])

    def test_actual_journal_rejects_partial_or_stale_reverse_source_span(self):
        program,ref,binding,events,translation,_=self.actual_operand_journal_fixture()
        for rows in (events[:-1],events[1:]):
            with self.assertRaises(ValueError):c.verify_ds_operand_journal(program,'template',ref,binding,rows)
        wrong=copy.deepcopy(events);wrong[-1]['generation']+=1
        with self.assertRaisesRegex(ValueError,'matching live'):c.verify_ds_operand_journal(program,'template',ref,binding,wrong)
        wrong=copy.deepcopy(events)
        for event in wrong:
            if event['tag']==0 and event['generation']==2:event['generation']=1
        with self.assertRaisesRegex(ValueError,'did not advance'):c.verify_ds_operand_journal(program,'template',ref,binding,wrong)
        wrong=copy.deepcopy(ref);wrong['logical_byte_offset']=4
        with self.assertRaisesRegex(ValueError,'typed span'):c.verify_ds_operand_journal(program,'template',wrong,binding,events)
        wrong=copy.deepcopy(ref);wrong['attrs']['name']='unresolved'
        with self.assertRaisesRegex(ValueError,'opcode attrs'):c.verify_ds_operand_journal(program,'template',wrong,binding,events)

    def test_actual_journal_rejects_capacity_lease_and_physical_translation_gaps(self):
        program,ref,binding,events,translation,_=self.actual_operand_journal_fixture()
        for field,value in [('shared_tile_offset',65535),('allocation_bytes',256),('lease_state','released'),('PC',19),('provider_tag_capacity',0)]:
            wrong=dict(binding);wrong[field]=value
            with self.assertRaises(ValueError):c.verify_ds_operand_journal(program,'template',ref,wrong,events)
        for field,value in [('lease','stale'),('bytes',256),('AW',10),('physical_base',None)]:
            wrong=dict(translation);wrong[field]=value
            with self.assertRaises(ValueError):c.verify_ds_operand_journal(program,'template',ref,binding,events,translation=wrong)

    def test_portable_pin_lookup_has_no_historical_git_or_current_model_dependency(self):
        import tempfile,hashlib
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'archive';(archive/'blobs').mkdir(parents=True)
            raw=b'original immutable analytical model';sha=hashlib.sha256(raw).hexdigest();commit='f'*40
            (archive/'blobs'/(sha+'.gz')).write_bytes(gzip.compress(raw,mtime=0))
            index={'inputs':[dict(path='tools/model.py',commit=commit,sha256=sha,storage='hash_blob_gzip')]}
            (archive/'index.json').write_text(json.dumps(index))
            (root/'tools').mkdir();(root/'tools/model.py').write_bytes(b'current additive successor differs')
            with patch.object(c,'ROOT',root),patch.object(c,'PORTABLE_INPUTS',archive),patch.object(c.subprocess,'check_output',side_effect=AssertionError('historical Git forbidden')):
                self.assertEqual(c.source_bytes('tools/model.py',commit[:8]),raw)
                with self.assertRaisesRegex(ValueError,'missing'):c.source_bytes('tools/absent.py',commit)
                (archive/'blobs'/(sha+'.gz')).write_bytes(gzip.compress(b'altered',mtime=0))
                with self.assertRaisesRegex(ValueError,'hash mismatch'):c.source_bytes('tools/model.py',commit)

    def test_portable_canonical_archive_is_required_and_not_duplicated(self):
        import tempfile,hashlib
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'inputs';archive.mkdir();raw=b'canonical native producer bytes';sha=hashlib.sha256(raw).hexdigest()
            row=dict(path='canonical.json.gz',commit='a'*40,sha256=sha,storage='canonical_tracked_path')
            (archive/'index.json').write_text(json.dumps({'inputs':[row]}))
            with patch.object(c,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'canonical committed'):c.portable_calendar_blob(row['path'],row['commit'],archive)
                (root/'canonical.json.gz').write_bytes(raw)
                self.assertEqual(c.portable_calendar_blob(row['path'],row['commit'][:7],archive),raw)
                (root/'canonical.json.gz').write_bytes(b'wrong')
                with self.assertRaisesRegex(ValueError,'hash mismatch'):c.portable_calendar_blob(row['path'],row['commit'],archive)
                with self.assertRaisesRegex(ValueError,'escape'):c.portable_calendar_blob('../canonical.json.gz',row['commit'],archive)

    def r34_fixture(self):
        import ast,hashlib,subprocess
        before=dict(family='all_reduce',providers={'parts':{'shape':[8,1024],'dtype':'F32'}},outputs={'out':'v34'},
            shape_parameters={},resources={'materialized_tensor_workspace_bytes':65536,'peak_interpreter_live_words':16384},
            code=[dict(op='LOAD',dst='v0',src=[],shape=[8,1024],attrs={'name':'parts','dtype':'F32'}),
                dict(op='SLICE',dst='v1',src=['v0'],shape=[1024],attrs={'axis':0,'start':0}),
                dict(op='FADD',dst='v34',src=['v1','v1'],shape=[1024],attrs={'round':'FP32_RNE'})])
        original=dict(templates={'old':before},instructions=[dict(pc=0,family='all_reduce',dependencies=[],
            source_op={'groups':8,'per_group':8,'elems':8192},rank_bindings=[{'rank':r,'template':'old'} for r in (0,1)],
            reads=[{'version':'parts'}],writes=[{'version':'out'}],provider_bindings={'old':{'parts':{'version':'parts'}}})])
        raw=subprocess.check_output(['git','show','0b4ab421b:tools/ds_hbm_group_provider_r34.py'],cwd=ROOT)
        ns={'copy':copy,'math':__import__('math'),'Counter':__import__('collections').Counter}
        node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='lower_template')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'pinned-test-metadata','exec'),ns)
        after=ns['lower_template'](before);key=hashlib.sha256(json.dumps(after,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        inventory=c.compile_ds_r34_group_source(original,raw,[dict(PC=0,old_template='old',new_template=key)])
        source=inventory['corrected_PC_bindings'][0];c0=sum(source['old_batches128'].values())*22
        previous=dict(r33_reprice_applied=True,Qwen_full_program={'PCs':1737},DeepSeek=dict(PCs=1,
            known_native_only_successor_software_ticks=10000000,unknown_shared_template_calls=7,
            PC_intervals=[dict(pc=0,family='all_reduce',dependencies=[],start=0,end=10000000,
                rank_groups=[dict(ranks=[0,1],C0_retained_ticks=c0,shared_retained_ticks=800,RF_additional_cost_after_existing_ledger=None)])]))
        return previous,inventory,{'typed_cost_bounds':{}},32,22

    def test_r34_actual_source_groups_preserve_rounding_and_replace_native_C0_once(self):
        args=self.r34_fixture();result,summary=c.reprice_ds_r34_groups(*args)
        self.assertEqual(summary['changed_rank_calls'],2)
        self.assertEqual(summary['shared_unknown_calls'],9)
        self.assertGreater(summary['critical_rank_software_tick_delta'],0)
        self.assertEqual(result['Qwen_full_program'],args[0]['Qwen_full_program'])
        row=result['DeepSeek']['PC_intervals'][0]['rank_groups'][0]
        self.assertEqual(row['shared_retained_ticks'],800)
        self.assertIsNone(row['r34_additional_RF_debit']);self.assertIsNone(row['r34_additional_provider_transfer_cost'])
        self.assertIsNone(summary['full_service_software_ticks'])
        bad=list(args);bad[0]=result
        with self.assertRaisesRegex(ValueError,'already applied'):c.reprice_ds_r34_groups(*bad)
        bad=copy.deepcopy(args);bad[0]['DeepSeek']['PC_intervals'][0]['rank_groups'][0]['C0_retained_ticks']+=1
        with self.assertRaisesRegex(ValueError,'C0 source ledger'):c.reprice_ds_r34_groups(*bad)
        bad=copy.deepcopy(args);bad[0]['r33_reprice_applied']=False
        with self.assertRaisesRegex(ValueError,'current'):c.reprice_ds_r34_groups(*bad)

    def test_r34_rejects_source_hash_and_rank_coverage_forgery(self):
        args=self.r34_fixture();bad=copy.deepcopy(args)
        bad[1]['corrected_PC_bindings'][0]['ranks']=[0]
        with self.assertRaisesRegex(ValueError,'rank coverage'):c.reprice_ds_r34_groups(*bad)
        bad=copy.deepcopy(args);bad[1]['corrected_PC_bindings'][0]['dependencies']=[9]
        with self.assertRaisesRegex(ValueError,'dependency'):c.reprice_ds_r34_groups(*bad)
        # Inventory itself records actual ordered opcodes/attrs, not exporter strings.
        t=next(iter(args[1]['native_templates'].values()))
        self.assertEqual(t['code'][0]['shape'],[8,8,1024])
        self.assertEqual(t['code'][2]['attrs'],{'round':'FP32_RNE'})
        self.assertEqual(t['code'][-1]['shape'],[8192])
        row=args[1]['corrected_PC_bindings'][0]
        self.assertEqual(set(row['provider_bindings']),{row['new_template']})
        self.assertIn('source rank=8*group+contributor',row['provider_bindings'][row['new_template']]['parts']['view'])

    def r33_pair(self):
        import hashlib,subprocess,math
        from collections import Counter
        code=[{'op':'LOAD','dst':'w','src':[],'shape':[128,512],'attrs':{'name':'window','dtype':'F32'}},
            {'op':'SLICE','dst':'trim','src':['w'],'shape':[127,512],'attrs':{'axis':0,'start':1,'step':1,'stop':None}},
            {'op':'LOAD','dst':'row','src':[],'shape':[1,512],'attrs':{'name':'kv','dtype':'F32'}},
            {'op':'FADD','dst':'arithmetic','src':['row','row'],'shape':[1,512],'attrs':{}},
            {'op':'CONCAT','dst':'out','src':['trim','row'],'shape':[128,512],'attrs':{'axis':0}},
            {'op':'PACKET_COMMIT','dst':'commit','src':['out'],'shape':[128,512],'attrs':{}}]
        t={'code':code,'family':'q_norm_kv_row','providers':{'window':{'shape':[128,512],'dtype':'F32'}},'shape_parameters':{'window':128}}
        tid='old';binding={'version':'input_window','view':'original128'}
        op={'pc':0,'family':'q_norm_kv_row','reads':[{'version':'input_window'}],
            'writes':[{'version':'output_window','native_result_binding':{'result':'window'}}],'dependencies':[],
            'provider_bindings':{tid:{'window':binding}},'rank_bindings':[{'rank':r,'template':tid} for r in range(2)]}
        native={'templates':{tid:t},'instructions':[op]};native_sha=hashlib.sha256(gzip.compress(json.dumps(native,sort_keys=True,separators=(',',':')).encode(),mtime=0)).hexdigest()
        counts=Counter();batches=Counter()
        for n in code:
            elements=math.prod(n['shape']);counts[n['op']]+=elements;batches[n['op']]+=c.ceil(elements,128)
        calls=[{'rank':r,'template':tid,'SM_partition':'bounded'} for r in range(2)]
        dispatch={'source_program_sha256':native_sha,'templates':{tid:{'execution_path':'source_order_live_range_stages'}},
            'PC_dispatch':[{'pc':0,'calls':calls,'rank_bindings':op['rank_bindings'],'provider_bindings':op['provider_bindings'],
                'baseline_once_scalars':{k:v*2 for k,v in counts.items()},'projected_executed_primitive_scalars':{k:v*2 for k,v in counts.items()}}]}
        catalog={'source_program_sha256':native_sha,'templates':{tid:{'calls':[{'leaf':'old_leaf','repetitions':1}],
            'execution_path':'source_order_live_range_stages','native_scalars':dict(counts),'native_batches128':dict(batches),
            'source_loop_plan':{'primitive_scalars':sum(counts.values())}}},'leaves':{},
            'PC_bindings':[{'pc':0,'bindings':calls,'native_scalars':{k:v*2 for k,v in counts.items()},'native_batches128':{k:v*2 for k,v in batches.items()}}],
            'native_scalars':{k:v*2 for k,v in counts.items()},'native_batches128':{k:v*2 for k,v in batches.items()}}
        contract=subprocess.check_output(['git','show','ca99e5d04:tools/ds_hbm_window_contract_r33.py'],cwd=ROOT)
        prepare=subprocess.check_output(['git','show','ca99e5d04:tools/ds_hbm_window_rope_prepare_r33.py'],cwd=ROOT)
        current,current_dispatch,witness,_,_=c.derive_ds_r33_source_pair(native,dispatch,contract,prepare,1048575)
        homes={'rows':[{'PC_first_consumer':0,'rank':r,'version':'input_window','shape':[127,512],
            'bytes':127*2048,'reservation_bytes':127*2048,'base':33554432,'generation':1,'source_payload_required':True} for r in range(2)]}
        return [native,dispatch,current,current_dispatch,witness,catalog,homes]

    def r33_current_cost_fixture(self):
        import hashlib
        args=self.r33_pair()
        args[5]['PC_bindings'][0].update(family='q_norm_kv_row',dependencies=[])
        a,cat,overlay=c.adapt_ds_r33_calendar(*args)
        produced={'rows':[{'PC':0,'rank':r,'version':'output_window','source_template':'old','shape':[128,512],
            'bytes':128*2048,'reservation_bytes':128*2048,'base':33554432+262144,'dtype':'F32'} for r in range(2)]}
        provider=c.bind_ds_r33_window_provider_homes(a,produced,args[-1])
        digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        parent=dict(schema='H4_C0_R33_SOURCE_ADAPTER_V1',hardware_qualified=False,
            inputs=dict(native=a['source_context']['native_sha256'],dispatch='d'*64),
            source_catalog_sha256=digest(cat),actual_scalar_count_delta={'LOAD':-1024})
        group=dict(ranks=[0,1],provider_nonV1_retained_ticks=60000,C0_retained_ticks=64,
            shared_retained_ticks=0,RF_additional_cost_after_existing_ledger=None,native_new_ticks=100)
        previous=dict(V1_native_replacement_applied=True,Qwen_full_program={'PCs':1737},
            DeepSeek=dict(PCs=1,unknown_shared_template_calls=2,known_native_only_successor_software_ticks=100000,
                PC_intervals=[dict(pc=0,family='q_norm_kv_row',dependencies=[],start=0,end=100000,rank_groups=[group])]))
        return a,cat,overlay,provider,parent,cat,previous,32

    def test_r33_reprice_critical_rank_once_preserves_unknown_and_other_charges(self):
        args=self.r33_current_cost_fixture();successor,receipt=c.compose_ds_r33_once_reprice(*args)
        self.assertEqual(receipt['actual_scalar_count_delta'],{'LOAD':-1024})
        self.assertEqual(receipt['critical_path_software_tick_delta'],-16384)
        self.assertEqual(successor['DeepSeek']['known_native_only_successor_software_ticks'],83616)
        old=args[-2]['DeepSeek']['PC_intervals'][0]['rank_groups'][0]
        new=successor['DeepSeek']['PC_intervals'][0]['rank_groups'][0]
        for k,v in old.items():self.assertEqual(new[k],v)
        self.assertEqual(successor['Qwen_full_program'],args[-2]['Qwen_full_program'])
        self.assertIsNone(receipt['complete_service_software_ticks'])
        self.assertEqual(successor['DeepSeek']['unknown_shared_template_calls'],2)
        again=list(args);again[-2]=successor
        with self.assertRaisesRegex(ValueError,'once'):c.compose_ds_r33_once_reprice(*again)

    def test_r33_receipt_matches_actual_parent_once_admission_method(self):
        import ast,hashlib,subprocess,types
        args=self.r33_current_cost_fixture();_,receipt=c.compose_ds_r33_once_reprice(*args)
        raw=subprocess.check_output(['git','show','ce132ffea:tools/h4_c0_r33_source_adapter.py'],cwd=ROOT)
        cls=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='R33SourceJoin')
        fn=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='accept_Dewey_reprice'))
        ns={'json':json,'pinned':lambda path,commit:json.dumps(receipt).encode()}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'source-pinned-parent-once-admission','exec'),ns)
        owner=types.SimpleNamespace(r33_inputs=dict(native=receipt['native_sha256'],dispatch=receipt['dispatch_sha256']),
            catalog_digest=receipt['catalog_sha256'],count_delta=receipt['actual_scalar_count_delta'],calendar_admitted=False)
        ns['accept_Dewey_reprice'](owner,'source-pin','receipt.json')
        self.assertTrue(owner.calendar_admitted)
        with self.assertRaisesRegex(ValueError,'already admitted once'):ns['accept_Dewey_reprice'](owner,'source-pin','receipt.json')
        owner.calendar_admitted=False;receipt['RF_highword_RMW_recharged']=True
        with self.assertRaisesRegex(ValueError,'exact source-bound'):ns['accept_Dewey_reprice'](owner,'source-pin','receipt.json')

    def test_r33_reprice_rejects_current_catalog_code_rank_and_count_forgery(self):
        args=self.r33_current_cost_fixture()
        bad=copy.deepcopy(args);bad[4]['source_catalog_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'identity'):c.compose_ds_r33_once_reprice(*bad)
        bad=copy.deepcopy(args);bad[4]['actual_scalar_count_delta']['LOAD']=-512
        with self.assertRaisesRegex(ValueError,'delta'):c.compose_ds_r33_once_reprice(*bad)
        bad=copy.deepcopy(args);tid=next(iter(bad[2]['native_templates']));bad[2]['native_templates'][tid]['code'][0]['attrs']['name']='forged'
        with self.assertRaisesRegex(ValueError,'source LOAD'):c.compose_ds_r33_once_reprice(*bad)
        bad=copy.deepcopy(args);bad[-2]['DeepSeek']['PC_intervals'][0]['rank_groups'][0]['ranks']=[0,0]
        with self.assertRaisesRegex(ValueError,'rank coverage'):c.compose_ds_r33_once_reprice(*bad)

    def test_r33_initial_boundary_exact64B_mirrors_and_finite_credit_positive(self):
        a,cat,o,p,*_=self.r33_current_cost_fixture()
        costs={k:2 for k in ('owner_accept','HBM32_read_return','scratch64_write_ACK',
            'scratch64_read_return','RF512_both_mirror_ACK','consumer_capture','validated_reverse')}
        result=c.reserve_ds_r33_initial_loads(a,cat,o,p,costs)
        self.assertEqual(len(result['events']),2)
        self.assertEqual(result['phase_unit_totals']['HBM32_read_return'],2*508*16)
        self.assertEqual(result['phase_unit_totals']['scratch64_write_ACK'],2*508*8)
        self.assertEqual(result['phase_unit_totals']['RF512_both_mirror_ACK'],2*508)
        self.assertEqual(result['events'][0]['RF_write_mirror_mask'],3)
        self.assertEqual(result['events'][0]['end'],result['events'][1]['start'])
        self.assertIsNone(result['all_PC_runtime_calendar'])
        self.assertFalse(result['added_to_existing_cost_ledger'])
        overlap=copy.deepcopy(result['events']);overlap[1]['start']=0;overlap[1]['end']=overlap[0]['end']
        with self.assertRaisesRegex(ValueError,'premature|overlapping'):c.verify_calendar(overlap,result['capacities'])
        costs['HBM32_read_return']=0
        with self.assertRaisesRegex(ValueError,'positive'):c.reserve_ds_r33_initial_loads(a,cat,o,p,costs)

    def test_r33_boundary_rejects_alias_home_old_source_and_duplicate_calls(self):
        a,cat,o,p,*_=self.r33_current_cost_fixture()
        costs={k:1 for k in ('owner_accept','HBM32_read_return','scratch64_write_ACK',
            'scratch64_read_return','RF512_both_mirror_ACK','consumer_capture','validated_reverse')}
        bad=copy.deepcopy(p);bad['bindings'][0]['input']['base']+=512
        with self.assertRaisesRegex(ValueError,'immutable'):c.reserve_ds_r33_initial_loads(a,cat,o,bad,costs)
        bad=copy.deepcopy(p);bad['source_context']['native_sha256']='old'
        with self.assertRaisesRegex(ValueError,'context'):c.reserve_ds_r33_initial_loads(a,cat,o,bad,costs)
        bad=copy.deepcopy(p);bad['bindings'].append(bad['bindings'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'):c.reserve_ds_r33_initial_loads(a,cat,o,bad,costs)

    def test_r33_adapter_changes_only_source_LOAD_count_and_keeps128row_cost_fit(self):
        args=self.r33_pair();adapter,catalog,overlay=c.adapt_ds_r33_calendar(*args)
        self.assertEqual(adapter['primitive_scalar_delta']['LOAD'],-1024)
        self.assertEqual(adapter['native_batches128_delta']['LOAD'],-8)
        self.assertEqual(adapter['primitive_scalar_delta']['FADD'],0)
        self.assertTrue(adapter['original128row_cost_reservations_retained'])
        self.assertFalse(adapter['physical_cost_replacement_applied'])
        self.assertIsNone(adapter['matching_current_movement_bridge'])
        ctx=adapter['source_context'];c.require_ds_calendar_source_context(adapter,ctx['native_sha256'],ctx['dispatch_content_sha256'],ctx['catalog_content_sha256'])
        with self.assertRaisesRegex(ValueError,'mixed'):c.require_ds_calendar_source_context(adapter,args[1]['source_program_sha256'],ctx['dispatch_content_sha256'],ctx['catalog_content_sha256'])
        tid=args[4][0]['new_template'];load=overlay['native_templates'][tid]['code'][0]
        ref={'source_context':ctx,'pc':0,'rank':0,'parent_template':tid,'call_index':0,'invocation_index':0,
            'template':tid,'code_index':0,'opcode':'LOAD','attrs':load['attrs'],'result_shape':load['shape'],
            'operand':'dst','value':'w','logical_byte_offset':0,'payload_bytes':127*2048}
        resolved=c.resolve_ds_r33_window_reference(adapter,catalog,overlay,ref)
        self.assertEqual(resolved[2],127*2048)
        bad=copy.deepcopy(ref);bad['payload_bytes']=128*2048
        with self.assertRaises(ValueError):c.resolve_ds_r33_window_reference(adapter,catalog,overlay,bad)
        bad=copy.deepcopy(ref);bad['source_context']['native_sha256']=args[1]['source_program_sha256']
        with self.assertRaisesRegex(ValueError,'mixed'):c.resolve_ds_r33_window_reference(adapter,catalog,overlay,bad)

    def test_r33_adapter_rejects_old_dispatch_catalog_counts_and_home_views(self):
        args=self.r33_pair()
        for index in (3,):
            bad=copy.deepcopy(args);bad[index]=copy.deepcopy(args[1])
            with self.assertRaisesRegex(ValueError,'dispatch/native'):c.adapt_ds_r33_calendar(*bad)
        bad=copy.deepcopy(args);bad[3]['PC_dispatch'][0]['calls'][0]['template']='old'
        with self.assertRaisesRegex(ValueError,'mixes old'):c.adapt_ds_r33_calendar(*bad)
        bad=copy.deepcopy(args);bad[3]['PC_dispatch'][0]['projected_executed_primitive_scalars']['LOAD']+=512
        with self.assertRaisesRegex(ValueError,'perPC dispatch'):c.adapt_ds_r33_calendar(*bad)
        bad=copy.deepcopy(args);bad[5]['source_program_sha256']='forged'
        with self.assertRaisesRegex(ValueError,'baseline catalog'):c.adapt_ds_r33_calendar(*bad)
        bad=copy.deepcopy(args);bad[6]['rows'][0]['bytes']=128*2048
        with self.assertRaisesRegex(ValueError,'home span'):c.adapt_ds_r33_calendar(*bad)

    def test_r33_adapter_rejects_unrelated_arithmetic_and_provider_alias_mutations(self):
        import hashlib
        args=self.r33_pair();bad=copy.deepcopy(args);tid=bad[4][0]['new_template']
        bad[2]['templates'][tid]['code'][3]['op']='FMUL'
        bad[3]['source_program_sha256']=hashlib.sha256(gzip.compress(json.dumps(bad[2],sort_keys=True,separators=(',',':')).encode(),mtime=0)).hexdigest()
        with self.assertRaisesRegex(ValueError,'template source identity'):c.adapt_ds_r33_calendar(*bad)
        bad=copy.deepcopy(args);bad[2]['instructions'][0]['provider_bindings'][tid]['window']['version']='aliased_window'
        bad[3]['source_program_sha256']=hashlib.sha256(gzip.compress(json.dumps(bad[2],sort_keys=True,separators=(',',':')).encode(),mtime=0)).hexdigest()
        with self.assertRaisesRegex(ValueError,'source version/position'):c.adapt_ds_r33_calendar(*bad)

    def test_r33_provider_home_join_proves_disjoint_spans_without_inventing_ACKs(self):
        args=self.r33_pair();adapter,_,_=c.adapt_ds_r33_calendar(*args)
        produced={'rows':[{'PC':0,'rank':r,'version':'output_window','source_template':'old','shape':[128,512],
            'bytes':128*2048,'reservation_bytes':128*2048,'base':33554432+262144,'dtype':'F32'} for r in range(2)]}
        joined=c.bind_ds_r33_window_provider_homes(adapter,produced,args[-1])
        self.assertEqual(joined['rank_window_pairs'],2)
        self.assertTrue(all(r['output_shape_source_equivalence_proved'] for r in joined['bindings']))
        self.assertTrue(all(r['actual_refill_visible_ACK_reverse_receipt'] is None for r in joined['bindings']))
        self.assertFalse(joined['source_payloads_supplied'])
        bad=copy.deepcopy(produced);bad['rows'][0]['base']=33554432
        with self.assertRaisesRegex(ValueError,'alias'):c.bind_ds_r33_window_provider_homes(adapter,bad,args[-1])
        bad=copy.deepcopy(produced);bad['rows'][0]['shape']=[127,512]
        with self.assertRaisesRegex(ValueError,'output source shape'):c.bind_ds_r33_window_provider_homes(adapter,bad,args[-1])
        bad=copy.deepcopy(produced);bad['rows'].pop()
        with self.assertRaisesRegex(ValueError,'home missing'):c.bind_ds_r33_window_provider_homes(adapter,bad,args[-1])

    def tp96_inputs(self):
        folder=ROOT/c.OUT/'tp96_literal_collective_join_r1/inputs'
        return (json.loads((folder/'normal_record.json').read_bytes()),
            json.loads((folder/'preflight.json').read_bytes()),
            json.loads((folder/'fixture_manifest.json').read_bytes()),
            (folder/'normal.log').read_text(),
            c.read_json(ROOT/c.LOWERING/'DeepSeek.json.gz')['operations'],
            c.read_json(folder.parent/'endpoint_cycles.json')['cycles'])

    def test_TP96_full_PC_literal_word_calendar_preserves_failed_bound_and_shape_gap(self):
        result=c.reconcile_tp96_literal_collectives(*self.tp96_inputs())
        self.assertEqual(result['PCs'],2213);self.assertEqual(result['collective_PCs'],270)
        cases={r['name']:r for r in result['case_reconciliation']}
        self.assertEqual(cases['expert_intermediate']['bound_verdict'],'FAIL_NORMAL_EXCEEDS_PREFLIGHT')
        self.assertEqual(cases['expert_intermediate']['normal_minus_preflight_cycles'],3234)
        self.assertEqual(cases['index_candidates']['consumer_floor_cycles'],6144)
        self.assertEqual(cases['index_candidates']['normal_cycles'],42861)
        rows={r['pc']:r for r in result['endpoint_reservations']}
        self.assertEqual(rows[42]['literal_words_per_rank'],6)
        self.assertEqual(rows[42]['payload_bytes_per_rank_upper'],336)
        self.assertFalse(rows[42]['normal_fixture_shape_match'])
        self.assertEqual(rows[127]['literal_words_per_rank'],64)
        self.assertEqual(rows[127]['consumer_records_per_endpoint'],6144)
        previous=0
        for r in result['endpoint_reservations']:
            self.assertEqual(r['start_endpoint_cycles'],previous)
            self.assertLessEqual(r['landing_records_reserved_each'],r['landing_capacity_each'])
            self.assertEqual(r['end_endpoint_cycles']-previous,r['word_repetitions']*sum(p['cycles'] for p in r['word_phase_order']))
            previous=r['end_endpoint_cycles']
        self.assertFalse(result['native_software_ticks_changed'])
        self.assertFalse(result['physical_timings_changed'])
        self.assertIsNone(result['complete_program_latency']);self.assertIsNone(result['headline_delta'])

    def test_TP96_rejects_missing_endpoints_spans_and_landing_exhaustion(self):
        args=list(self.tp96_inputs());original=args[3]
        import hashlib
        for changed,reason in [('\n'.join(original.splitlines()[2:]),'incomplete'),
            (original.replace('landing_peak=1','landing_peak=129',1),'landing/consumer'),
            (original.replace('words=512','words=511',1),'descriptor/endpoint')]:
            bad=copy.deepcopy(args);bad[3]=changed;bad[0]['cases']['normal']['log_sha256']=hashlib.sha256(changed.encode()).hexdigest()
            with self.assertRaisesRegex(ValueError,reason):c.reconcile_tp96_literal_collectives(*bad)

    def test_TP96_rejects_implicit_zero_latency_and_source_deadlock(self):
        args=list(self.tp96_inputs());bad=copy.deepcopy(args);bad[-1]['gather_word_route']=0
        with self.assertRaises(ValueError):c.reconcile_tp96_literal_collectives(*bad)
        bad=copy.deepcopy(args);bad[4][42]['dependencies']=[42]
        with self.assertRaisesRegex(ValueError,'dependency/deadlock'):c.reconcile_tp96_literal_collectives(*bad)
        bad=copy.deepcopy(args);bad[0]['cases']['normal']['cycles']['expert_intermediate']=5001
        with self.assertRaisesRegex(ValueError,'cycle extraction'):c.reconcile_tp96_literal_collectives(*bad)

    def test_V1_physical_join_retains_finite_owner_mirrors_and_slot_failure(self):
        import subprocess
        raw=subprocess.check_output(['git','show','620c078de78cc55ddb5562b1d5d7171d8ef944ca:results/uarch/h4_v1_g0_model_20261002/physical_join_r1/final/model.json'],cwd=ROOT)
        model=json.loads(raw);joined=c.join_v1_physical_capacity(model)
        self.assertEqual(joined['models']['DeepSeek']['replicas'],3072)
        self.assertEqual(joined['models']['Qwen']['replicas'],64)
        self.assertEqual(joined['RF_contract']['physical_write_mirrors'],2)
        self.assertEqual(joined['RF_contract']['RF_transaction_credit'],1)
        self.assertFalse(joined['additional_C0_or_RF_cost_applied'])
        self.assertIsNone(joined['dynamic_RF_ledger'])
        for name in ('Qwen','DeepSeek'):
            self.assertFalse(joined['models'][name]['slot']['physical_slot_admitted'])
            self.assertFalse(joined['models'][name]['routing']['shared_channel_fits'])
        bad=copy.deepcopy(model);bad['models']['DeepSeek']['rank_to_die_SM'][-1]=bad['models']['DeepSeek']['rank_to_die_SM'][0]
        with self.assertRaisesRegex(ValueError,'incomplete or duplicate'):c.join_v1_physical_capacity(bad)
        bad=copy.deepcopy(model);bad['RF_contract']['physical_write_mirrors']=1
        with self.assertRaisesRegex(ValueError,'mirror/credit'):c.join_v1_physical_capacity(bad)
        bad=copy.deepcopy(model);bad['models']['Qwen']['calendar']['RF_read_II']=0
        with self.assertRaisesRegex(ValueError,'serialized service'):c.join_v1_physical_capacity(bad)

    def test_MTP_contract_keeps_AR_and_local_acceptance_separate_from_agentic_headline(self):
        acceptance={'results':{'overall':{'prompts':36,'walk':{'tau':3.648676}},
            'per_class':{'chat':{'walk':{'tau':2.457711}},'reasoning':{'walk':{'tau':3.607}}}},
            'headline':{'tau':3.649},'caveats':['different GEMM order; short context']}
        isa='def run_mtp():\n    return compile_layer, compile_head, tokens[1:], pos0 + j, hists[j]\n'
        record=c.audit_ds_mtp_source_contract({'instructions':[{}],'coverage':{'families':{'x':1}}},acceptance,
            isa,'DRAFTS = [1,2,3,4,5]','HBM_W19 = dict(ar_us=442.14,mtp_pass_us=715.82,drafter_us=49.9,unrelated=source_runtime())')
        self.assertEqual(record['AR_native_program']['PCs'],1)
        self.assertEqual(record['acceptance']['pooled_prompts'],36)
        self.assertIsNone(record['acceptance']['headline_agentic_median_rate'])
        self.assertIn('sensitivity only',record['acceptance']['local_chat_role'])
        self.assertFalse(record['accepted_token_rate_qualified'])
        self.assertIn('unprocessed bonus',record['causal_KV_successor_contract']['bonus_token'])
        self.assertTrue(all(v is None for v in record['missing_complete_iteration_costs'].values()))

    def test_agentic_median_request_rate_is_not_pooled_token_ratio(self):
        rows=[]
        for i,(n,v,cost) in enumerate([(10,2,500),(10,5,1000),(100,20,5000)]):
            rows.append({'request_id':str(i),'workload_class':'agentic','gamma':5,'model':'DeepSeek-V4.1-Flash',
                'acceptance_mode':'actual','includes_committed_bonus':True,'source_receipt_sha256':'a'*64,
                'committed_tokens':n,'verify_iterations':v,'complete_iteration_costs_us':[cost]*v})
        result=c.agentic_request_rate_summary(rows)
        self.assertEqual(result['median_request_tokens_s'],2000)
        self.assertAlmostEqual(result['pooled_tokens_s'],120*1e6/106000)
        self.assertNotEqual(result['median_request_tokens_s'],result['pooled_tokens_s'])
        self.assertFalse(result['qualified_headline'])
        self.assertIsNone(c.agentic_request_rate_summary([])['median_request_tokens_s'])
        bad=copy.deepcopy(rows);bad[0]['acceptance_mode']='synthetic'
        with self.assertRaisesRegex(ValueError,'synthetic acceptance rejected'):c.agentic_request_rate_summary(bad)
        bad=copy.deepcopy(rows);bad[0]['complete_iteration_costs_us']=[500]
        with self.assertRaisesRegex(ValueError,'matching complete'):c.agentic_request_rate_summary(bad)
        bad=copy.deepcopy(rows);bad[0]['gamma']=3
        with self.assertRaisesRegex(ValueError,'gamma5'):c.agentic_request_rate_summary(bad)

    def test_V1_native_replacement_serial_RF_keeps_C0_and_rejects_second_charge(self):
        api=c.load_v1_cost_api('f7fa8e290d419f6de3356385c0b55ded768c2090')
        code=[{'op':'LOAD','src':[],'dst':'mask','shape':[128],'attrs':{'dtype':'U32'}},
            {'op':'LOAD','src':[],'dst':'a','shape':[128],'attrs':{'dtype':'I64'}},
            {'op':'LOAD','src':[],'dst':'b','shape':[128],'attrs':{'dtype':'I64'}},
            {'op':'SELECT','src':['mask','a','b'],'dst':'out','shape':[128],'attrs':{}}]
        program={'templates':{'t':{'code':code}}}
        ref={'template':'t','code_index':3,'opcode':'SELECT','attrs':{},'result_shape':[128],
            'operand':'dst','value':'out','logical_byte_offset':0,'payload_bytes':1024}
        phases=[{'kind':'C0_accept','ticks':2},{'kind':'RF_read_pair','ticks':3,'transactions':1},
            {'kind':'native','opcode':'SELECT','ticks':32},{'kind':'RF_write_vector_ACK','ticks':2,'transactions':1},
            {'kind':'provider_RMW','ticks':2},{'kind':'C0_complete','ticks':2},{'kind':'C0_reverse_retire','ticks':2}]
        r={'owner':{'PC':0,'rank':0,'SM':0,'tag':1,'generation':1},'native_instruction_ref':ref,
            'baseline_phases':phases,'RF_ledger':{'RF_read_pair_transactions':1,'RF_write_vectors':1,
                'native_ticks_per_command':32,'I64_RMW_already_charged':True,'C0_already_charged':True}}
        joined=c.reconcile_v1_ordered_phases(program,'t',r,api)
        self.assertEqual(joined['reconciliation']['native_only_replacement_ticks'],4)
        self.assertEqual(joined['reconciliation']['additional_RF_read_pairs'],2)
        self.assertEqual(joined['reconciliation']['additional_RF_write_vectors'],1)
        self.assertEqual(joined['software_ticks_after'],25)
        self.assertEqual([x for x in joined['ordered_phases'] if x['kind'].startswith('C0_')],
                         [x for x in phases if x['kind'].startswith('C0_')])
        self.assertEqual(joined['reconciliation']['additional_I64_RMW_charge'],0)
        for mutation,error in [('again','already applied'),('missing','UNKNOWN'),('RF','baseline phases'),('opcode','opcode attrs')]:
            bad=copy.deepcopy(r)
            if mutation=='again':bad['native_replacement_applied']=True
            elif mutation=='missing':bad.pop('RF_ledger')
            elif mutation=='RF':bad['RF_ledger']['RF_read_pair_transactions']=2
            else:bad['native_instruction_ref']['opcode']='FADD'
            with self.assertRaisesRegex(ValueError,error):c.reconcile_v1_ordered_phases(program,'t',bad,api)

    def test_Kepler_source_allocator_resolves_fragment_not_history_tensor(self):
        raw=c.source_bytes('tools/ds_hbm_finite_state_homes_r30.py','f240f42fbeb67e402e922b4a4aae30b8a8873ce1')
        producer={'code':[{'op':'LOAD','dst':'v0','src':[],'shape':[128],'attrs':{'dtype':'F32'}}],
            'outputs':{'new_ik':'v0'},'providers':{}}
        consumer={'code':[],'outputs':{},'providers':{'keys':{'shape':[8,128],'dtype':'F32'}}}
        native={'templates':{'t':producer,'c':consumer},'instructions':[
            {'pc':0,'writes':[{'version':'index_keys.L2','home_indices':[], 'native_result_binding':{'result':'new_ik'}}],
             'rank_bindings':[{'rank':63,'template':'t'}],'provider_bindings':{}},
            {'pc':1,'writes':[],'rank_bindings':[], 'provider_bindings':{'c':{'keys':{'version':'index_keys.L2','native_address_view':'full history'}}}}]}
        row={'PC':0,'version':'index_keys.L2','rank':63,'base':33554432,'bytes':512,'reservation_bytes':512,
             'shape':[128],'dtype':'F32','source_template':'t','source_result':'new_ik','home_class':'HBM_NATIVE_STATE',
             'semantic_scope':'exact produced output fragment only; full-history append/aux consumption remains source-bound separately'}
        directory={'source_native_sha256':'source','rows':[row],'per_rank_reserved_bytes':{'63':512},
            'extent':{'AW':27,'base':33554432,'bytes':33554432,'address_class':'native software service plane; GPU physical AW34 translation NOT supplied'},
            'capacity_charged_bytes_all96_ranks':33554432*96,'source_operator_or_rounding_changes':0,'actual_initial_context_supplied':False,'hardware_qualified':False}
        result=c.bind_kepler_state_directory(native,directory,raw,'source')
        key=result['index_key_bindings'][0];self.assertTrue(key['produced_fragment_address_bound'])
        self.assertFalse(key['complete_index_history_home_bound'])
        self.assertEqual(key['source_consumer_views'][0]['requested_bytes'],4096)
        bad=copy.deepcopy(directory);bad['rows'][0]['base']+=512
        with self.assertRaisesRegex(ValueError,'retained source allocator'):c.bind_kepler_state_directory(native,bad,raw,'source')

    def test_Kepler_state_terminal_receipt_is_source_bound_but_not_full_journal(self):
        binding={'PC':121,'version':'index_keys.L2','rank':63,'base':33554432,'bytes':512}
        owner={'PC':121,'version':'index_keys.L2','rank':63,'generation':1,'home_indices':[0]}
        fragment={'target':'DeepSeek','rank':63,'epoch':1,'pc':121,'serial':16,'sector':(33554432+511)//32}
        events=[{'event':e,'identity':owner,'sequence':i+1,'source_tick':10+i,
            'source_fragment_identity':fragment,'source_tag':1,'source_tag_generation':2}
            for i,e in enumerate(['software_backing_visible','consumer_accept','validated_reverse_grant'])]
        receipt={'identity':owner,'payload_sha256':{'data':'a'*64},'events':events,'pending_obligations':0}
        result=c.validate_kepler_state_publication(receipt,binding)
        self.assertFalse(result['whole_fragment_sector_journal_bound']);self.assertIsNone(result['RF_phase_cost_debit'])
        for mutation,error in [('generation','tag/generation'),('debt','outstanding debt'),('sector','sector/source'),('event','order')]:
            bad=copy.deepcopy(receipt)
            if mutation=='generation':bad['events'][-1]['source_tag_generation']=3
            elif mutation=='debt':bad['pending_obligations']=1
            elif mutation=='sector':bad['events'][-1]['source_fragment_identity']['sector']+=1
            else:bad['events'][0]['event']='consumer_accept'
            with self.assertRaisesRegex(ValueError,error):c.validate_kepler_state_publication(bad,binding)

    def test_V1_all_PC_component_replacement_keeps_source_units_C0_shared_and_provider(self):
        api=c.load_v1_cost_api('f7fa8e290d419f6de3356385c0b55ded768c2090')
        profile=api.command_cost('I2F',[64],32)
        model={'typed_cost_bounds':{'I2F':{'upper':profile}},'area':{},'routing':{},'resource_contract':{}}
        ds={'retained_baseline_provisional_costs':{'primitive_scalar':32},'known_service_software_ticks':88,
            'unknown_shared_template_calls':1,'PC_intervals':[{'pc':0,'family':'x','dependencies':[],
            'additional_atomic_admission_ticks':0,'atomic_collective_participants':[],
            'ranks':[{'rank':0,'start':0,'end':88,'C0_ticks':22,'shared_known_ticks':8,
            'baseline_provider_and_native_ticks_charged_once':58,'native_scalar_command_upper_by_opcode':{'I2F':1}}]}]}
        qfix={'software_ticks':88,'ordered_PC_intervals':[{'pc':0,'opcode':'x','position':0,'start':0,'end':88,
            'native_commands':{'I2F':1},'cost_units':{'native_batch':1},'C0_service_ticks':22,'provider_service_ticks':26}]}
        q={'operations':[{'pc':0,'opcode':'x','dependencies':[],
            'calendar_export':{'physical_primitives':{'native_primitive_commands':{'I2F':1}}}}]}
        result=c.compose_v1_native_component_successor(ds,qfix,q,model)
        row=result['DeepSeek']['PC_intervals'][0]['rank_groups'][0]
        self.assertEqual(row['C0_retained_ticks'],22);self.assertEqual(row['shared_retained_ticks'],8)
        self.assertEqual(row['provider_nonV1_retained_ticks'],26)
        self.assertEqual(result['DeepSeek']['known_native_only_successor_software_ticks'],66)
        self.assertIsNone(row['RF_additional_cost_after_existing_ledger'])
        bad=copy.deepcopy(ds);bad['V1_native_replacement_applied']=True
        with self.assertRaisesRegex(ValueError,'already replaced'):c.compose_v1_native_component_successor(bad,qfix,q,model)

    def test_forward_leaf_source_counts_dynamic_refs_and_G0_interface(self):
        N,S=c.load_ds_forward_builders();native={'templates':{},'instructions':[]};dispatch={'templates':{},'PC_dispatch':[],
            'source_program_sha256':'a'*64}
        cases=[('linear_q',{'rows':3,'k':32},{'fmt':'fp8'},'forward_streaming_Q8_matvec',S.model(3,32,'fp8')),
            ('mv',{'rows':3,'k':8},{},'forward_streaming_float_matvec',S.float_model(3,8,False)),
            ('linear_bf16',{'rows':2,'k':24},{},'forward_streaming_float_matvec',S.float_model(2,24,True)),
            ('index_scores',{'rows':2,'heads':2,'width':32},{},'forward_streaming_index_rows',S.index_model(2,2,32)),
            ('all_gather',{'n':3,'ranks':2},{},'forward_streaming_gather_columns',S.gather_model(2,3))]
        for pc,(family,shape,attrs,path,plan) in enumerate(cases):
            tid='template'+str(pc);program=N.recipe(family,shape,attrs)
            program.update(family=family,shape_parameters=shape,source_attributes=attrs);native['templates'][tid]=program
            counts=plan['opcode_scalar_evaluations'];dispatch['templates'][tid]={'family':family,'execution_path':path,'plan':plan,
                'executed_primitive_scalar_projection':counts}
            native['instructions'].append({'pc':pc,'family':family,'dependencies':[],'rank_bindings':[{'rank':0,'template':tid,'buffer_programs':[]}]})
            dispatch['PC_dispatch'].append({'pc':pc,'family':family,'dependencies':[],
                'calls':[{'rank':0,'template':tid,'SM_partition':'block256%32'}],'projected_executed_primitive_scalars':counts})
        catalog=c.compile_ds_forward_leaf_catalog(dispatch,native,N,S)
        self.assertEqual(catalog['PCs'],5);self.assertEqual(len(catalog['execution_paths']),4)
        self.assertLess(sum(catalog['native_batches128'].values()),sum(catalog['native_scalars'].values()))
        bad=copy.deepcopy(dispatch);bad['templates']['template0']['plan']['weight_format']='fp4'
        with self.assertRaisesRegex(ValueError,'format source mismatch'):c.compile_ds_forward_leaf_catalog(bad,native,N,S)
        bad=copy.deepcopy(dispatch);bad['PC_dispatch'][0]['calls'][0]['rank']=1
        with self.assertRaisesRegex(ValueError,'PC/rank/template source mismatch'):c.compile_ds_forward_leaf_catalog(bad,native,N,S)
        call=catalog['templates']['template3']['calls'][1];leaf=catalog['leaves'][call['leaf']]
        actual=S.index_program(2,32,1,1,3)
        index=next(i for i,n in enumerate(actual['code']) if n['attrs']!=leaf['program']['code'][i]['attrs'])
        node=actual['code'][index]
        ref={'parent_template':'template3','call_index':1,'invocation_index':1,'template':call['leaf'],
            'source_parameters':{'first':1,'rank':3},'code_index':index,'opcode':node['op'],'attrs':node['attrs'],
            'result_shape':node['shape'],'operand':'dst','value':node['dst'],'logical_byte_offset':0,'payload_bytes':8}
        self.assertEqual(c.resolve_ds_forward_leaf_reference(catalog,N,S,ref,expected_rank=3)[1],node['dst'])
        with self.assertRaisesRegex(ValueError,'row/rank source binding mismatch'):
            c.resolve_ds_forward_leaf_reference(catalog,N,S,ref,expected_rank=4)
        bad=copy.deepcopy(ref);bad['attrs']=leaf['program']['code'][index]['attrs']
        with self.assertRaisesRegex(ValueError,'attrs shape mismatch'):c.resolve_ds_forward_leaf_reference(catalog,N,S,bad,expected_rank=3)
        q={'operations':[{'pc':0,'opcode':'EMBED','calendar_export':{'physical_primitives':{
            'native_primitive_commands':{'I2F':2},'kernel_invocations':{'convert':2}}}}]}
        g=c.compile_g0_source_interface(q,catalog)
        self.assertEqual(g['Qwen']['native_commands']['I2F'],2);self.assertEqual(g['DeepSeek']['PCs'],5)
        self.assertEqual(g['RF_port_contract']['port_bits'],4096)
        self.assertTrue(all(x['measured_cycles'] is None for x in g['opcode_cost_contract'].values()))
        self.assertFalse(g['hardware_full_native_claim'])

    def test_forward_parent_provider_home_resolves_source_and_preserves_missing_receipts(self):
        cat={'source_program_sha256':'source','templates':{'t':{'execution_path':'forward_streaming_Q8_matvec'}},
            'PC_bindings':[{'pc':0,'family':'linear_q','dependencies':[], 'bindings':[{'rank':3,'template':'t'}]}]}
        native={'residence_archive':'canonical.json.gz','instructions':[{'reads':[{'version':'x'}],'writes':[{'version':'y'}],
            'provider_bindings':{'t':{'activation':{'kind':'versioned_operand','version':'x'},
                'weight':{'kind':'immutable_parameter_provider','logical_tensor':'weight'}}}}]}
        residence={'homes':[{'version':'x','rank_group':[3],'SM':0,'home':{'class':'RF','slot_first':32,'vectors':1},
            'birth_pc':-1,'retire_pc':0}]}
        interface=c.compile_ds_forward_parent_interface(cat,native,residence)
        self.assertEqual(interface['missing_version_home_refs'],['y'])
        self.assertEqual(c.resolve_ds_forward_parent_home(interface,residence,pc=0,version='x',rank=3,SM=0)[1]['home']['slot_first'],32)
        self.assertFalse(interface['physical_admission'])
        self.assertEqual(interface['PC_bindings'][0]['provider_refill_writeback_ACK_reverse'],'UNKNOWN_NO_DYNAMIC_PARENT_PROVIDER_RECEIPT')
        with self.assertRaisesRegex(ValueError,'rank missing'):c.resolve_ds_forward_parent_home(interface,residence,pc=0,version='x',rank=4,SM=0)
        with self.assertRaisesRegex(ValueError,'UNKNOWN actual parent physical home'):c.resolve_ds_forward_parent_home(interface,residence,pc=0,version='y',rank=3,SM=0)
        with self.assertRaisesRegex(ValueError,'version missing'):c.resolve_ds_forward_parent_home(interface,residence,pc=0,version='forged',rank=3,SM=0)
        bad=copy.deepcopy(residence);bad['homes'][0]['birth_pc']=1
        with self.assertRaisesRegex(ValueError,'UNKNOWN actual parent physical home'):c.resolve_ds_forward_parent_home(interface,bad,pc=0,version='x',rank=3,SM=0)

    def test_C0_source_join_resolves_instructions_versions_and_rank_intervals(self):
        digest=lambda x:c.hashlib.sha256(c.json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        code=[{'op':'LOAD','src':[],'dst':'v0','shape':[1],'attrs':{'provider':'input','dtype':'F32'}}]
        q={'microcode':{'convert':[{'op':'ITOF','dst':'out','src':['a']}]},'operations':[
            {'pc':0,'opcode':'EMBED','reads':['token'],'writes':['x'],'dependencies':[],
             'calendar_export':{'physical_primitives':{'kernel_invocations':{'convert':2},'native_primitive_commands':{'I2F':2}}}}]}
        d={'templates':{'t':{'code':code}},'instructions':[{'pc':0,'family':'embed','reads':[{'version':'token'}],
            'writes':[{'version':'x'}],'dependencies':[], 'rank_bindings':[{'rank':0,'template':'t','SM_partition':'block256%32'}]}]}
        catalog={'source_program_sha256':'ds','templates':{'t':{'execution_path':'source_order_live_range_stages'}},
            'leaves':{'t':{}},'native_batches128':{'LOAD':1}}
        transition=['accepted','complete','mirrored_visible_ACK','consumer_accept','reverse_grant','retire']
        common={'source_PC':0,'dependency_completed_PC_ids':[],'source_version_refs':['token'],'destination_version_refs':['x'],
            'family_hardware_admitted':False,'source_numeric_payload_executed':False,'state_transition_order':transition}
        qr=dict(common,model='Qwen',program_sha256='q',family='EMBED',native_command_counts={'I2F':2},
            ordered_leaf_bindings=[{'kernel':'convert','invocations':2,'ordered_lowered_leaf_opcodes':['I2F'],
                'source_order_sha256':digest(q['microcode']['convert'])}])
        dr=dict(common,model='DeepSeek',program_sha256='ds',family='embed',rank_template_calls=[{'rank':0,'template_refs':['t'],
            'buffer_programs':[],'row_interval':None,'empty_owned_extent':False,'SM_partition':'block256%32'}])
        lowering={'schema':'H4_C0_FULL_PC_STATIC_DISPATCH_LOWERING_V1','RTL_admission':False,
            'complete_dynamic_numeric_execution':False,'dispatch':[qr,dr],'DS_template_catalog':{'t':{
                'ordered_source_code_sha256':digest(code),'ordered_steps':1,'opcode_records':{'LOAD':1},
                'bounded_emitter':'source_order_live_range_stages'}}}
        call=lambda x:c.join_c0_source_lowering(x,q,d,catalog,{'ITOF':'I2F'},qwen_sha256='q')
        self.assertEqual(call(lowering)['programs']['DeepSeek']['PCs'],1)
        self.assertIsNone(call(lowering)['shared64_movements'])
        for change,message in [('sequence','instruction sequence'),('version','identity/version'),('rank','rank/template'),('source','code/continuation'),('claim','qualify dynamic')]:
            bad=copy.deepcopy(lowering)
            if change=='sequence':bad['dispatch'][0]['ordered_leaf_bindings'][0]['ordered_lowered_leaf_opcodes']=['FADD']
            elif change=='version':bad['dispatch'][1]['destination_version_refs']=['wrong']
            elif change=='rank':bad['dispatch'][1]['rank_template_calls'][0]['rank']=1
            elif change=='source':bad['DS_template_catalog']['t']['ordered_source_code_sha256']='wrong'
            else:bad['complete_dynamic_numeric_execution']=True
            with self.assertRaisesRegex(ValueError,message):call(bad)

    def test_H4_reprice_64B_transactions_and_dispatch_preserves_provider_charge(self):
        e={'explicit_provisional_latency':{'shared_beat128':8,'native_batch':32},
            'ordered_PC_ticks':90,'ordered_PC_intervals':[{'pc':0,'start':0,'end':90,
            'provider_service_ticks':10,'cost_units':{'shared_beat128':2,'native_batch':2},
            'all_provider_grants_before_PC_retire':True}]}
        r=c.reprice_h4_intervals(e)
        self.assertEqual(r['scratch64_transactions'],4)
        self.assertEqual(r['ordered_PC_intervals'][0]['provider_service_ticks'],10)
        self.assertEqual(r['software_ticks'],150)
        self.assertFalse(r['hardware_clock_admission']);self.assertFalse(r['r22_augmentation_applied'])
        bad=copy.deepcopy(e);bad['ordered_PC_intervals'][0]['end']=89
        with self.assertRaisesRegex(ValueError,'cost mismatch'):c.reprice_h4_intervals(bad)
        bad=copy.deepcopy(r['explicit_provisional_costs']);bad['C0_decode']=0
        with self.assertRaisesRegex(ValueError,'positive explicit'):c.reprice_h4_intervals(e,costs=bad)

    def test_C0_scoreboard_credit_ACK_reverse_alias_and_generation(self):
        s=c.C0VersionScoreboard(entries=3)
        a=(0,0,'a',1);b=(0,0,'b',1);d=(0,0,'d',1)
        s.publish(a,('RF',0,512));s.publish(b,('RF',512,512),visible=False)
        s.publish(d,('RF',1024,512),visible=False)
        s.accept('add',[a],b)
        with self.assertRaisesRegex(ValueError,'credit exhausted'):s.accept('mul',[a],d)
        with self.assertRaisesRegex(ValueError,'retained lease'):s.release(a)
        with self.assertRaisesRegex(ValueError,'transition order'):s.transition('add','consumer_accept')
        s.transition('add','complete');s.transition('add','mirrored_visible_ACK')
        s.accept('mul',[b],d)
        for phase in ['consumer_accept','reverse_grant','retire']:s.transition('add',phase)
        s.release(a)
        with self.assertRaisesRegex(ValueError,'live home alias'):s.publish((0,0,'x',2),('RF',512,512))
        with self.assertRaisesRegex(ValueError,'stale home generation'):s.publish(a,('RF',0,512))
        s.publish((0,0,'next',2),('RF',0,512))
        with self.assertRaisesRegex(ValueError,'scoreboard exhausted'):s.publish((0,1,'other',1),('RF',0,512))
        for phase in ['complete','mirrored_visible_ACK','consumer_accept','reverse_grant','retire']:s.transition('mul',phase)
        s.release(b);s.release(d);s.release((0,0,'next',2))
        self.assertFalse(s.live);self.assertFalse(s.commands);self.assertFalse(s.RF_owner)

    def test_H4_source_pinned_unified_configuration_and_32SM_RF_footprint(self):
        d=ROOT/'results/uarch/h3_complete_native_calendar_20261002/h4_actual_config_e844/inputs'
        r=c.compose_h4_uarch((d/'uarch_model.py.source').read_text(),c.read_json(d/'uarch_parameters.json'),
                            c.read_json(d/'hardware_inventory.json'))
        ds=r['designs']['DeepSeek'];q=r['designs']['Qwen']
        self.assertEqual(ds['reconciled_model_element']['stack_levels'],4)
        self.assertFalse(ds['reconciled_model_element']['group_slot'])
        self.assertEqual(ds['formula_drain_cycles_actual_config']-ds['formula_drain_cycles_before'],7)
        self.assertEqual(q['RF']['physical_bytes_per_rank'],16777216)
        self.assertEqual(ds['ports_bytes_per_accepted_transaction']['scratch'],64)
        self.assertEqual(ds['ports_bytes_per_accepted_transaction']['matrix_ingest'],128)
        self.assertGreater(ds['matvec_issue_comparison'][0]['actual_row_slot_cycles'],
                           ds['matvec_issue_comparison'][0]['previous_group_slot_cycles'])
        self.assertIsNone(ds['routing']['channel_capacity_tracks']);self.assertFalse(ds['hardware_admission'])
        pins=c.read_json(d/'family_coverage.json')
        self.assertEqual(pins['DeepSeek']['unique_PCs'],2213);self.assertEqual(pins['Qwen']['unique_PCs'],1737)

    def test_H4_DS_actual_stage_C0_completion_after_native_visible_commit(self):
        d=ROOT/'results/uarch/h3_complete_native_calendar_20261002/h4_actual_config_e844/inputs'
        calendar=c.read_json(d/'DS_PC127_calendar.json.gz');program=c.read_json(d/'DS_PC127_template.json.gz')
        costs=c.reprice_h4_intervals(c.read_json(d/'Qwen_provider_execution.json.gz'))['explicit_provisional_costs']
        r=c.reprice_h4_native_stages(calendar,program,costs)
        self.assertEqual(r['C0_commands'],1189792);self.assertEqual(r['C0_added_software_ticks'],26175424)
        self.assertIsNone(r['scratch64_transaction_count']);self.assertFalse(r['payload_executed'])
        for row in r['stages']:
            names=[p['phase'] for p in row['phases']]
            self.assertEqual(names[:4],['C0_fetch','C0_decode','C0_home_scoreboard','C0_accept'])
            self.assertEqual(names[-3:-1],['C0_complete','C0_reverse_retire'])
            self.assertEqual(row['phases'][-1]['end'],row['batch_stride'])

    def test_C0_global_HBM_alias_and_declared_future_consumer_are_not_free(self):
        s=c.C0VersionScoreboard();a=(0,0,'a',1);b=(0,0,'b',1)
        s.publish(a,('HBM',4096,512),future_readers=['add'])
        with self.assertRaisesRegex(ValueError,'live home alias'):s.publish((0,1,'other',2),('HBM',4096,512))
        with self.assertRaisesRegex(ValueError,'future consumer'):s.release(a)
        s.publish(b,('RF',0,512),visible=False);s.accept('add',[a,a],b)
        for phase in ['complete','mirrored_visible_ACK','consumer_accept','reverse_grant','retire']:s.transition('add',phase)
        s.release(a);s.release(b);self.assertFalse(s.live)

    def test_DS_shared_bridge_positive_counts_and_negative_capacity_alias_empty(self):
        t={'execution_path':'source_order_live_range_stages','reference_scalar_fallback_admitted':False,
            'no_recomputed_dependency_scalars':True,'plan':{'workspace_upper_bytes':512},
            'executed_primitive_scalar_projection':{'LOAD':2,'FADD':2},
            'provider_transfer_projection':{'read_512B_fragments_upper':1,'write_512B_fragments_upper':1}}
        d={'schema':'H3_DS_FORWARD_BOUNDED_POLYNOMIAL_DISPATCH_V2','automatic_scalar_fallback_templates':0,
            'workspace':{'rank_cap_bytes':33554432,'base':None},'source_program_sha256':'a'*64,'templates':{'kernel':t},
            'PC_dispatch':[{'pc':0,'family':'test','dependencies':[],
                'calls':[{'rank':0,'template':'kernel','SM_partition':'block256%32'}],
                'projected_executed_primitive_scalars':t['executed_primitive_scalar_projection'],
                'provider_transfer_projection':t['provider_transfer_projection']}]}
        program={'templates':{'kernel':{'code':[
            {'op':'LOAD','dst':'x','src':[],'shape':[2],'attrs':{'dtype':'F32','name':'input'}},
            {'op':'FADD','dst':'y','src':['x','x'],'shape':[2],'attrs':{}}],'outputs':{'out':'y'}}}}
        def ref(index,operand,value):
            node=program['templates']['kernel']['code'][index]
            return {'template':'kernel','code_index':index,'opcode':node['op'],'attrs':node['attrs'],
                'result_shape':node['shape'],'operand':operand,'value':value,'logical_byte_offset':0,'payload_bytes':8}
        b={'schema':'H4_DS_NATIVE_SHARED_MOVEMENT_BRIDGE_V1','source_program_sha256':'a'*64,
            'source_dispatch_sha256':c.hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'scratch_beat_bytes':64,'scratch_capacity_bytes':65536,'bridge_source_sha256':'b'*64,
            'templates':{'kernel':{'execution_path':t['execution_path'],'native_primitive_scalars':t['executed_primitive_scalar_projection'],
            'ordered_movements':[{'source_step':0,'event':'acquire','lease':'v','base':0,'bytes':64,'value':'x','logical_byte_offset':0,'payload_bytes':8},
                {'source_step':0,'event':'write64_ACK','lease':'v','byte_address':0,'span_bytes':64,'repetitions':1,'native_instruction_ref':ref(0,'dst','x')},
                {'source_step':1,'event':'read64','lease':'v','byte_address':0,'span_bytes':64,'repetitions':1,'native_instruction_ref':ref(1,'src:0','x')},
                {'source_step':1,'event':'read64','lease':'v','byte_address':0,'span_bytes':64,'repetitions':1,'native_instruction_ref':ref(1,'src:1','x')},
                {'source_step':1,'event':'acquire','lease':'out','base':64,'bytes':64,'value':'y','logical_byte_offset':0,'payload_bytes':8},
                {'source_step':1,'event':'write64_ACK','lease':'out','byte_address':64,'span_bytes':64,'repetitions':1,'native_instruction_ref':ref(1,'dst','y')},
                {'source_step':1,'event':'release_after_ACK_reverse','lease':'v'},
                {'source_step':1,'event':'release_after_ACK_reverse','lease':'out'}]}}}
        def run(bridge):return c.compose_ds_full_program_services(d,bridge=bridge,native_program=program)
        unknown=c.compose_ds_full_program_services(d);self.assertIsNone(unknown['scratch64_read_transactions'])
        bound=run(b)
        self.assertEqual(bound['scratch64_read_transactions'],2);self.assertEqual(bound['scratch64_write_ACK_transactions'],2)
        self.assertEqual(bound['known_service_software_ticks']-unknown['known_service_software_ticks'],32)
        self.assertIsNone(bound['complete_service_software_ticks']);self.assertFalse(bound['hardware_full_native_claim'])
        bad=copy.deepcopy(b);bad['templates']['kernel']['ordered_movements'][0]['bytes']=65537
        with self.assertRaisesRegex(ValueError,'lease extent'):run(bad)
        bad=copy.deepcopy(b);bad['templates']['kernel']['ordered_movements'].insert(1,
            {'source_step':0,'event':'acquire','lease':'other','base':0,'bytes':64})
        with self.assertRaisesRegex(ValueError,'live alias'):run(bad)
        bad=copy.deepcopy(b);bad['templates']['kernel']['ordered_movements']=[]
        with self.assertRaisesRegex(ValueError,'incomplete native movement'):run(bad)
        bad=copy.deepcopy(b);bad['templates']['kernel']['ordered_movements'][1]['repetitions']=0
        with self.assertRaisesRegex(ValueError,'positive explicit'):run(bad)
        bad=copy.deepcopy(b);bad['source_program_sha256']='c'*64
        with self.assertRaisesRegex(ValueError,'source mismatch'):run(bad)
        for field,value,error in [('native_instruction_ref','kernel/code/1','structured retained'),
                                  ('native_instruction_ref',ref(1,'dst','y'),'read-write role mismatch')]:
            bad=copy.deepcopy(b);bad['templates']['kernel']['ordered_movements'][2][field]=value
            with self.assertRaisesRegex(ValueError,error):run(bad)
        for field,value,error in [('code_index',999,'out of range'),('value','y','value mismatch'),
                                  ('payload_bytes',12,'span out of range'),('opcode','FMUL','opcode attrs shape mismatch')]:
            bad=copy.deepcopy(b);bad['templates']['kernel']['ordered_movements'][2]['native_instruction_ref'][field]=value
            with self.assertRaisesRegex(ValueError,error):run(bad)
        bad=copy.deepcopy(b);del bad['templates']['kernel']['ordered_movements'][3]
        with self.assertRaisesRegex(ValueError,'incomplete native movement'):run(bad)
        bad=copy.deepcopy(b);bad['templates']['kernel']['ordered_movements'].insert(4,copy.deepcopy(b['templates']['kernel']['ordered_movements'][3]))
        with self.assertRaisesRegex(ValueError,'duplicate native movement'):run(bad)

    def test_ordered_native_SM_services_reject_alias_missing_read_and_RTL_credit(self):
        p={'providers':{'input':{'shape':[256],'dtype':'F32'}},'code':[
            {'op':'LOAD','dst':'x','src':[],'shape':[256],'attrs':{'name':'input','dtype':'F32'}},
            {'op':'FADD','dst':'y','src':['x','x'],'shape':[256],'attrs':{}},
            {'op':'FMUL','dst':'z','src':['y','x'],'shape':[256],'attrs':{}}], 'outputs':{'out':'z'}}
        binding={'input':{'kind':'versioned_operand','version':'source.x'}}
        r=c.compile_ssa_finite_sm_services(p,rank=0,provider_bindings=binding)
        self.assertEqual(c.verify_ssa_finite_sm_services(r,p)['source_stages'],3)
        self.assertEqual(r['stages'][1]['repetitions'],2)
        self.assertFalse(r['hardware_or_clock_admission']);self.assertEqual(len(r['constrained_extent_successor_demand']),1)
        bad=copy.deepcopy(r);bad['stages'][1]['destination_home']['offset']=0
        bad['stages'][1]['destination_home']['generation']=2
        with self.assertRaisesRegex(ValueError,'workspace alias'):c.verify_ssa_finite_sm_services(bad,p)
        bad=copy.deepcopy(r);bad['stages'][1]['phases'][1]['units']=0
        with self.assertRaisesRegex(ValueError,'obligations mismatch'):c.verify_ssa_finite_sm_services(bad,p)
        bad=copy.deepcopy(r);bad['hardware_or_clock_admission']=True
        with self.assertRaisesRegex(ValueError,'cannot qualify RTL'):c.verify_ssa_finite_sm_services(bad,p)
        with self.assertRaisesRegex(ValueError,'provider live alias'):
            c.compile_ssa_finite_sm_services(p,rank=0,provider_bindings=binding,
                workspace={'AW':27,'base':0,'bytes':33554432,'occupied_extents':[{'base':0,'bytes':512}]})

    def test_actual_retained_PC127_refs_resolve_typed_source_operands_and_canonical_blob(self):
        base=ROOT/c.OUT/'ds_finite_sm_services_fd722'
        template=c.read_json(base/'PC127_rank0_template.json.gz');tid='7b7fc026294cd82667b919531738f73d9fcf810922fc9041c707f12eb78d2f9b'
        p={'templates':{tid:template}};node=template['code'][0]
        ref={'template':tid,'code_index':0,'opcode':node['op'],'attrs':node['attrs'],'result_shape':node['shape'],
             'operand':'dst','value':node['dst'],'logical_byte_offset':0,'payload_bytes':64}
        role,symbol,size,offset,payload=c.resolve_ds_movement_reference(p,tid,ref)
        self.assertEqual(role,(0,'dst'));self.assertEqual(size,196608);self.assertEqual(payload,64)
        bad=copy.deepcopy(ref);bad['attrs']['name']='fabricated'
        with self.assertRaisesRegex(ValueError,'attrs shape mismatch'):c.resolve_ds_movement_reference(p,tid,bad)
        bad=copy.deepcopy(ref);bad['logical_byte_offset']=196608
        with self.assertRaisesRegex(ValueError,'span out of range'):c.resolve_ds_movement_reference(p,tid,bad)
        raw=c.source_bytes(Path('results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'),'91e3b8cc2791fa3fe1322df3d72b3f76dbd184f6')
        self.assertEqual(c.hashlib.sha256(raw).hexdigest(),'c7ae6baf3f57d3b8d23b3532dad9d1fa921ac86736b5e8b5a229f644a1994313')
        with self.assertRaisesRegex(ValueError,'immutable source commit'):c.source_bytes(Path('unused'),'main')

    def test_native_workspace_exhaustion_returns_precise_successor(self):
        p={'providers':{'input':{'shape':[4194305],'dtype':'I64'}},'code':[
            {'op':'LOAD','dst':'x','src':[],'shape':[4194305],'attrs':{'name':'input','dtype':'I64'}}],
           'outputs':{'out':'x'}}
        r=c.compile_ssa_finite_sm_services(p,rank=0,provider_bindings={'input':{'kind':'versioned_operand','version':'x'}})
        self.assertEqual(r['status'],'CONSTRAINED_NATIVE_WORKSPACE_SUCCESSOR_REQUIRED')
        self.assertEqual(r['requested_definition_bytes'],33554944)
        self.assertEqual(r['largest_free_span_bytes'],33554432)
        self.assertEqual(r['source_order_stages_completed'],0)

    def test_actual_PC127_ordered_SM_issue_and_workspace_lifetimes(self):
        base=ROOT/c.OUT/'ds_finite_sm_services_fd722'
        program=c.read_json(base/'PC127_rank0_template.json.gz')
        bindings=c.read_json(base/'PC127_rank0_provider_bindings.json')
        r=c.compile_ssa_finite_sm_services(program,rank=0,provider_bindings=bindings)
        proof=c.verify_ssa_finite_sm_services(r,program)
        self.assertEqual(proof['source_stages'],3999)
        self.assertEqual(sum(r['primitive_scalars'].values()),152178060)
        self.assertEqual(proof['primitive_batches128'],1189792)
        self.assertLessEqual(r['workspace_peak_bytes'],33554432)
        self.assertFalse(r['payload_executed']);self.assertFalse(proof['native_RTL_cost_credit'])

    def bounded_fixture(self, layers=1):
        base=ROOT / c.OUT / 'bounded_provider_milestone'
        N,K=c.load_bounded_provider_sources(base)
        config=dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,
            intermediate_size=16,vocab_size=16,num_hidden_layers=layers,rms_norm_eps=1e-6,rope_theta=1000000)
        return N,K,N.compile_tiled(N.compile_program(config,context=32,groups=16))

    def test_bounded_actual_all_PC_counts_and_mutant_kernel_rejected(self):
        base=ROOT / c.OUT / 'bounded_provider_milestone'
        native=c.read_json(base/'Qwen_tiled.json.gz')
        graph=c.read_json(base/'sources/results/uarch/h3_versioned_lowering_20261002/Qwen.json.gz')
        proof=c.audit_bounded_export(native,graph)
        self.assertEqual((proof['PCs'],proof['classes']),(1737,21))
        self.assertEqual(proof['workspace']['temporary_HBM_bytes'],0)
        self.assertFalse(proof['fullshape_ordered_runtime_trace_executed'])
        native['tile_kernel_ABI']['add']['native_counts_per_invocation']['FADD']+=1
        with self.assertRaisesRegex(ValueError,'kernel primitive count mismatch'):c.audit_bounded_export(native,graph)

    def test_separate_entrypoint_preserves_baseline_and_U32_SELECT_width(self):
        import numpy as np
        import hashlib
        N,K,native=self.bounded_fixture()
        self.assertEqual(Path(N.__file__).name,'bounded_entrypoint.py.source')
        baseline=ROOT/c.OUT/'bounded_provider_milestone/baseline.py.source'
        self.assertEqual(hashlib.sha256(baseline.read_bytes()).hexdigest(),
            '9a231227d3d605cd34aec0629300bf24ff561b14d0b65364a696f9c5be4a6c76')
        vm=N.NativePrimitiveVM();out=vm.run_qwen([{'op':'SELECT','dst':'out','src':['condition','left','right']}],
            {'condition':np.array([1,0],np.uint32),'left':np.array([0xffffffff,1],np.int64),
             'right':np.array([2,0x80000000],np.int64)})
        self.assertEqual(out.dtype,np.uint32)
        np.testing.assert_array_equal(out,[0xffffffff,0x80000000])

    def test_bounded_provider_execution_all_snapshot_bits_and_counts(self):
        import numpy as np
        N,K,native=self.bounded_fixture(); expected=N.TiledMachine(native); snapshots={}
        def record(op,store):
            snapshots[op['pc']]={v:store.debug_snapshot(v) for v in op['writes']}
        expected_results=[expected.run(3,0,record),expected.run(5,1,record)]
        # Collect separate references for both token positions.
        expected=N.TiledMachine(native); records=[]
        for token,pos in [(3,0),(5,1)]:
            snapshots={}; expected.run(token,pos,record); records.append(copy.deepcopy(snapshots))
        backend=c.AddressedTileByteBackend(K,native);c.seed_bounded_fixture(N,backend,native,[0,1])
        observed=[]
        def compare(op,store):
            position=len(observed)//len(native['operations'])
            for v in op['writes']:
                actual=store.debug_snapshot(v); ref=records[position][op['pc']][v]
                if isinstance(ref,dict):self.assertEqual(actual,ref)
                elif isinstance(ref,tuple):self.assertEqual(actual,ref)
                else:
                    a,b=np.asarray(actual),np.asarray(ref)
                    np.testing.assert_array_equal(a.view(np.uint32) if a.dtype.kind=='f' else a,
                        b.view(np.uint32) if b.dtype.kind=='f' else b)
            observed.append(op['pc'])
        result=c.execute_bounded_provider_program(N,K,native,backend,positions=[(3,0),(5,1)],observer=compare)
        self.assertEqual([x['next_token'] for x in result['executions']],[x['next_token'] for x in expected_results])
        self.assertEqual(len(observed),114)
        self.assertTrue(result['all_provider_owners_drained']);self.assertTrue(result['source_transport']['all_owners_drained'])
        self.assertGreater(result['source_transport']['events']['software_backing_visible'],0)
        self.assertFalse(result['r22_augmentation_applied']);self.assertFalse(result['existing_calendar_cost_mutated'])
        self.assertEqual(result['R20_sidecar_PC_uses'],{})
        for a,b in zip(result['ordered_PC_intervals'],result['ordered_PC_intervals'][1:]):
            self.assertLessEqual(a['end'],b['start'])
        bad=copy.deepcopy(result);bad['ordered_PC_intervals'][1]['start']=0
        with self.assertRaisesRegex(ValueError,'overlap/cost'):c.verify_bounded_provider_execution(bad,native)
        bad=copy.deepcopy(result);bad['ordered_PC_intervals'][0]['all_provider_grants_before_PC_retire']=False
        with self.assertRaisesRegex(ValueError,'premature write reuse'):c.verify_bounded_provider_execution(bad,native)

    def test_raw_backend_missing_checkpoint_lease_and_extent_rejected(self):
        N,K,native=self.bounded_fixture();backend=c.AddressedTileByteBackend(K,native)
        ref='Qwen.rank0.extent.embedding';e=backend.extents[ref]
        request=dict(provider_ref=ref,lease='PC0.'+ref,lease_state='visible',
            byte_ranges=[dict(address=e['base'],bytes=1)])
        with self.assertRaisesRegex(ValueError,'checkpoint bytes missing'):backend.read_tile_bytes(request)
        backend.seed(ref,0,b'\x87');response=backend.read_tile_bytes(request)
        self.assertEqual(response['payloads'],[b'\x87']);self.assertTrue(response['reverse_grant_ACK'])
        bad=copy.deepcopy(request);bad['lease']='PC1.'+ref
        with self.assertRaisesRegex(ValueError,'lease/ref mismatch'):backend.read_tile_bytes(bad)
        bad=copy.deepcopy(request);bad['byte_ranges'][0]['address']=e['base']+e['bytes']
        with self.assertRaisesRegex(ValueError,'logical extent'):backend.read_tile_bytes(bad)
        p=backend.provider;identity=K.Identity('Qwen',0,0,0,100,e['base']//32);ticket=p.submit(identity)
        with self.assertRaises(K.Backpressure):p.submit(K.Identity('Qwen',0,0,0,101,e['base']//32))
        p.wait(ticket);p.consume(ticket)
        with self.assertRaises(K.OwnershipFault):p.reverse(ticket,identity,ticket.tag,ticket.generation+1)

    def test_real_PC14_codec_intervals_and_retained_reader_reuse_rejected(self):
        import numpy as np
        N,K,native=self.bounded_fixture()
        homes=c.read_json(ROOT/c.OUT/'workspace_r20_33b741b4e/temporary_provider_homes.json.gz')
        home=next(h for h in homes if h['pc']==14 and h.get('semantic_bits')==64)
        extents={('Qwen',home['rank']):[dict(base=home['base'],bytes=home['reserved_bytes']),
            dict(base=home['highword_base'],bytes=home['highword_reserved_bytes'])]}
        provider=K.SectorProvider(extents,tags=1,queue=1,write_residence=1)
        storage=K.Storage(provider,'Qwen',home['rank'],home['base'],home['reserved_bytes']);storage.pc=14
        tensor=K.tensor_from_native_binding(home,(4,))
        values=np.array([-(1<<63),-1,(1<<32)+7,(1<<63)-1],np.int64)
        storage.write(tensor,0,values);lease=storage.acquire_split64(tensor,np.arange(4))
        with self.assertRaises(K.Backpressure):storage.write(tensor,0,values)
        np.testing.assert_array_equal(storage.read(tensor,np.arange(4),lease),values)
        storage.release_split64(lease);storage.write(tensor,0,values[::-1])
        with self.assertRaises(K.OwnershipFault):storage.read(tensor,np.arange(4),lease)
        self.assertFalse(provider.live);self.assertFalse(storage.codec_leases)

    def test_DS_bounded_all_PC_finite_reservations_and_extent_gap(self):
        dispatch=c.read_json(ROOT/c.OUT/'bounded_provider_milestone/ds/forward_dispatch_milestone.json.gz')
        proof=c.audit_ds_bounded_dispatch(dispatch)
        full=c.compose_ds_full_program_services(dispatch)
        self.assertEqual(full['PCs'],2213);self.assertEqual(full['families'],30)
        self.assertEqual(full['native_scalar_commands_upper_by_opcode'],proof['primitive_scalars'])
        self.assertGreater(full['known_service_software_ticks'],proof['estimated_service_ticks'])
        self.assertIsNone(full['complete_service_software_ticks']);self.assertIsNone(full['scratch64_read_transactions'])
        self.assertTrue(all(not pc['shared_scope_complete'] for pc in full['PC_intervals']))
        self.assertEqual((proof['PCs'],proof['families']),(2213,30))
        self.assertFalse(proof['physical_admission']);self.assertFalse(proof['ordered_full_native_trace'])
        top=proof['PC_intervals'][127]['ranks'][0]
        self.assertEqual(top['workspace_peak_upper'],6790664)
        self.assertEqual(top['cost_units']['primitive_scalar'],152178060)
        self.assertEqual(top['cost_units']['fragment512_read']+top['cost_units']['fragment512_write'],6432848)
        self.assertEqual(len(proof['constrained_extent_successor_demand']),96)
        dispatch['PC_dispatch'][0]['projected_executed_primitive_scalars']['LOAD']+=1
        with self.assertRaisesRegex(ValueError,'count mismatch'):c.audit_ds_bounded_dispatch(dispatch)

    def test_final_ds_gather_buffers_and_exported_count_controls(self):
        def template(n):
            return {'code':[{'op':'IOTA','dst':'v0','src':[],'shape':[n],'attrs':{}}],
                'outputs':{'out':'v0'},'resources':{'instruction_batches128_by_opcode':{'IOTA':(n+127)//128}}}
        raw={'schema':'H3_DEEPSEEK_COMPLETE_NATIVE_V1','templates':{'preview':template(512),'a':template(129),'b':template(1)},
            'instructions':[{'pc':0,'family':'all_gather','reads':[],'writes':[],
                'provider_bindings':{'preview':{},'a':{},'b':{}},
                'rank_bindings':[{'rank':0,'template':'preview','buffer_programs':[{'template':'a'},{'template':'b'}]}]}]}
        native=c.normalize_bundle(raw);plan=native['operations'][0]
        self.assertEqual([n['dst'] for n in plan['programs'][0]['instructions']],['buffer0_v0','buffer1_v0'])
        self.assertEqual(plan['programs'][0]['source_templates'],['a','b'])
        table={'values':{k:2 for k in ['admit','RF_read','RF_write_ACK','consume','retire','HBM_read_sector',
            'HBM_write_sector','forward_CDC','reverse_CDC','visibility_fence','owner_lookup','owner_held_accept',
            'validated_reverse_grant','native:IOTA']}}
        program=c.bind_recipe(native,plan,{'reads':[],'opcode':'all_gather','golden_contract':'source ordered'},0,table)
        self.assertEqual(c.verify_native_program(program),{'IOTA':3})
        self.assertEqual(program['producer_vector_count_gate'],'PASS_EXACT_EXPORTED_NATIVE_COUNTS')
        plan['programs'][0]['expected_primitive_batches']['IOTA']=4
        with self.assertRaisesRegex(ValueError,'DS producer primitive count mismatch'):
            c.bind_recipe(native,plan,{'reads':[],'opcode':'all_gather','golden_contract':'source ordered'},0,table)

    def test_final_ds_portable_closure_and_iota_execution(self):
        import hashlib
        import shutil
        import tempfile
        import numpy as np
        archive=ROOT / 'results/uarch/h3_complete_native_calendar_20261002/final_ds_bed325f89'
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base=Path(temporary.name)/'portable'
        shutil.copytree(archive,base)
        # The native program has one canonical committed home. Reconstruct the
        # portable package for this check rather than rely on an untracked copy.
        canonical=ROOT/'results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
        pins=c.read_json(base/'producer_pins.json')
        self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(),
                         pins['files']['program_final.json.gz']['sha256'])
        shutil.copyfile(canonical,base/'program_final.json.gz')
        coverage=c.read_json(base/'coverage.json')
        sources=c.verify_portable_producer(base/'program_final.json.gz',coverage)
        self.assertEqual(len(sources),18)
        bad=copy.deepcopy(coverage);bad['source_sha256']['tools/h3_deepseek_complete_native.py']='0'*64
        with self.assertRaisesRegex(ValueError,'closure incomplete'):
            c.verify_portable_producer(base/'program_final.json.gz',bad)
        snapshot=base/'h3_deepseek_complete_native.py.source'
        program={'code':[{'op':'IOTA','dst':'v0','src':[],'shape':[129],'attrs':{}}],
                 'outputs':{'out':'v0'}}
        result=c.execute_primitive_vm('DeepSeek',program,{},snapshot=snapshot,
            source_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),scratch_bytes=129*8,instruction_limit=1)
        np.testing.assert_array_equal(result['outputs']['out'],np.arange(129,dtype=np.int64))
        self.assertEqual(result['events'][0]['batches128'],2)

    def test_r20_codec_counts_and_workspace_retire_intervals(self):
        import numpy as np
        values=np.array([-(1<<63),-1,0,(1<<32)+7,(1<<63)-1],np.int64)
        low,high=c.split_i64_words(values);identity=('session',3,0,'v','def',2)
        np.testing.assert_array_equal(c.join_i64_words(low,high,identity,identity),values)
        with self.assertRaisesRegex(ValueError,'mismatch'):c.join_i64_words(low,high,identity,identity[:-1])
        with self.assertRaisesRegex(ValueError,'extent'):c.join_i64_words(low,high[:1],identity,identity)
        alloc={'bytes':4,'version':'PC0.tmp.out','lease':'PC0.workspace','release_after':'PC0.retire',
            'home':{'class_':'spill','byte_offset':0,'base_by_rank':{'0':4096}}}
        home={'pc':0,'rank':0,'symbol':'out','bytes':4,'version':alloc['version'],'lease':alloc['lease'],
            'release_after':alloc['release_after'],'release_guard':'consumer+visible+reverse grant',
            'class_':'HBM_native_workspace','base':4096,'end_exclusive':4608,'semantic_bits':64,
            'highword_base':4608,'highword_reserved_bytes':512}
        workspace={'homes':{(0,0,'out'):home},'join':{'final_native_calendar_source_match':False,
            'rank_allocation':[{'rank':0,'extents':[{'name':'native_workspace','base':4096,'bytes':512},
                {'name':'native_I64_highword_codec_sidecar','base':4608,'bytes':512}]}]}}
        plan={'pc':0,'temporary_storage':{'allocations':{'out':alloc},'spill_bytes':512},
            'recipe':[{'op':'FTOI','dst':'out','src':['f32(7)']}]}
        events=[{'id':'a','start':0,'end':1},{'id':'r','start':10,'end':11}]
        pcs=[{'pc':0,'participants':[0],'admit':'a','retire':'r'}]
        intervals,proof=c.bind_workspace_intervals(workspace,events,pcs,{0:plan})
        self.assertEqual((intervals[0]['start'],intervals[0]['end']),(0,11))
        self.assertEqual(proof['status'],'PASS_CONCRETE_SOFTWARE_WORKSPACE_INTERVALS')
        table={'values':{k:2 for k in ['admit','RF_read','RF_write_ACK','consume','retire','HBM_read_sector',
            'HBM_write_sector','forward_CDC','reverse_CDC','visibility_fence','owner_lookup','owner_held_accept',
            'validated_reverse_grant','native:FTOI','I64_highword_read_sector','I64_highword_write_sector','I64_split_join','I64_RMW_merge']}}
        program=c.bind_recipe({'source_program':{},'operands':[]},plan,
            {'reads':[],'opcode':'test','golden_contract':'source I64'},0,table,workspace)
        node=program['primitive_tree'][0]
        self.assertEqual(node['I64_highword_write_sectors32'],1)
        self.assertEqual(node['stage_cycles']['I64_highword_write_visible'],2)
        self.assertEqual(node['stage_cycles']['I64_split'],2)
        home['highword_base']=4096
        with self.assertRaisesRegex(ValueError,'sidecar extent exhausted'):
            c.bind_workspace_intervals(workspace,events,pcs,{0:plan})

    def test_source_pinned_primitive_vms_and_finite_negative_controls(self):
        import hashlib
        import numpy as np
        base = ROOT / 'results/uarch/h3_complete_native_calendar_20261002'
        ds = base / 'inputs/h3_deepseek_complete_native.py.source'
        q = base / 'final_qwen_8fab95560/h3_qwen_complete_native.py.source'
        memory = {'x': np.array([16777216], np.float32), 'y': np.array([1], np.float32)}
        ssa = {'code': [
            {'op':'LOAD','dst':'a','src':[],'shape':[1],'attrs':{'name':'x','dtype':'F32'}},
            {'op':'LOAD','dst':'b','src':[],'shape':[1],'attrs':{'name':'y','dtype':'F32'}},
            {'op':'FADD','dst':'out','src':['a','b'],'shape':[1],'attrs':{}}], 'outputs':{'out':'out'}}
        kwargs = dict(snapshot=ds, source_sha256=hashlib.sha256(ds.read_bytes()).hexdigest(),
                      scratch_bytes=24, instruction_limit=10)
        result = c.execute_primitive_vm('DeepSeek', ssa, memory, **kwargs)
        np.testing.assert_array_equal(result['outputs']['out'], memory['x'])
        self.assertEqual([e['op'] for e in result['events']], ['LOAD','LOAD','FADD'])
        with self.assertRaisesRegex(ValueError, 'capacity exhausted'):
            c.execute_primitive_vm('DeepSeek', ssa, memory, **{**kwargs,'scratch_bytes':16})
        with self.assertRaisesRegex(ValueError, 'unbound native provider'):
            c.execute_primitive_vm('DeepSeek', ssa, {'x':memory['x']}, **kwargs)
        bad = copy.deepcopy(ssa); bad['code'][2]['op'] = 'DIV'
        with self.assertRaisesRegex(ValueError, 'exact DIV provider required'):
            c.execute_primitive_vm('DeepSeek', bad, memory, **kwargs)
        with self.assertRaisesRegex(ValueError, 'pin mismatch'):
            c.execute_primitive_vm('DeepSeek', ssa, memory, **{**kwargs,'source_sha256':'0'*64})
        recipe = {'recipe':[{'op':'FADD','dst':'out','src':['x','y']}], 'outputs':['out']}
        kwargs = dict(snapshot=q, source_sha256=hashlib.sha256(q.read_bytes()).hexdigest(),
                      scratch_bytes=12, instruction_limit=10)
        result = c.execute_primitive_vm('Qwen', recipe, memory, **kwargs)
        np.testing.assert_array_equal(result['outputs']['out'], memory['x'])
        self.assertEqual(result['primitive_counts'], {'FADD':1})
        with self.assertRaisesRegex(ValueError, 'scratch capacity exhausted'):
            c.execute_primitive_vm('Qwen', recipe, memory, **{**kwargs,'scratch_bytes':8})
        load = {'recipe':[{'op':'LOAD_WEIGHT','dst':'out','key':'w'}], 'outputs':['out']}
        with self.assertRaisesRegex(ValueError, 'unbound native weight provider'):
            c.execute_primitive_vm('Qwen', load, memory, **kwargs)
        loop = {'recipe':[{'op':'FOR','var':'i','start':'0','stop':'100','step':'1','body':[]}], 'outputs':[]}
        with self.assertRaisesRegex(ValueError, 'loop capacity exhausted'):
            c.execute_primitive_vm('Qwen', loop, {}, **kwargs)

    def test_parallel_positive_and_shared_serialization(self):
        cal = c.Calendar({'r0': 1, 'r1': 1, 'link': 1})
        cal.add('a', [], 7, {'r0': 1})
        cal.add('b', [], 11, {'r1': 1})
        cal.add('gather', ['a', 'b'], 3, {'r0': 1, 'r1': 1, 'link': 1})
        self.assertEqual([e['start'] for e in cal.events], [0, 0, 11])
        self.assertEqual(cal.ends['gather'], 14)
        self.assertEqual(c.verify_calendar(cal.events, cal.capacities)['status'], 'PASS_FINITE_INTERVAL_PROOF')

    def test_atomic_admission_does_not_take_partial_credit(self):
        cal = c.Calendar({'a': 1, 'b': 1})
        cal.add('first', [], 12, {'b': 1})
        cal.add('rendezvous', [], 4, {'a': 1, 'b': 1})
        self.assertEqual(cal.events[-1]['start'], 12)
        self.assertEqual(cal.events[-1]['resources'], {'a': [0], 'b': [0]})

    def test_exhaustion_and_zero_cost_rejected(self):
        cal = c.Calendar({'credit': 1})
        for duration, demand in [(0, 1), (2, 2)]:
            with self.assertRaises(ValueError):
                cal.add('x', [], duration, {'credit': demand})
        self.assertEqual(cal.events, [])

    def test_topological_cycle_and_unknown_dependencies_rejected(self):
        for tasks in [
            [{'id': 'a', 'deps': ['b'], 'duration': 1, 'resources': {}},
             {'id': 'b', 'deps': ['a'], 'duration': 1, 'resources': {}}],
            [{'id': 'a', 'deps': ['absent'], 'duration': 1, 'resources': {}}]]:
            with self.assertRaises(ValueError): c.Calendar({}).dag(tasks)

    def test_nonordered_input_dag_schedules(self):
        tasks = [{'id': 'b', 'deps': ['a'], 'duration': 2, 'resources': {'p': 1}},
                 {'id': 'a', 'deps': [], 'duration': 3, 'resources': {'p': 1}}]
        cal = c.Calendar({'p': 1}); cal.dag(tasks)
        self.assertEqual(cal.ends['b'], 5)

    def test_proof_rejects_tampered_overlap_consume_and_credit(self):
        cal = c.Calendar({'p': 1}); cal.add('a', [], 5, {'p': 1}); cal.add('b', ['a'], 2, {'p': 1})
        for field, value in [('start', 4), ('resources', {'p': [1]})]:
            events = copy.deepcopy(cal.events); events[1][field] = value
            with self.assertRaises(ValueError): c.verify_calendar(events, cal.capacities)
        events = copy.deepcopy(cal.events); events[1]['deps'] = []; events[1]['start'] = 4
        with self.assertRaises(ValueError): c.verify_calendar(events, cal.capacities)

    def test_live_alias_and_inclusive_retirement_rejected(self):
        graph = {'operands': [{'id': 'a', 'birth_pc': 0, 'retire_pc': 3},
                              {'id': 'b', 'birth_pc': 3, 'retire_pc': 4}]}
        homes = {(v['id'], 0): [{'SM': 0, 'home': {'class': 'RF', 'slot_first': 32, 'vectors': 1}}]
                 for v in graph['operands']}
        with self.assertRaisesRegex(ValueError, 'alias'): c.check_homes(homes, graph)
        graph['operands'][1]['birth_pc'] = 4
        self.assertTrue(c.check_homes(homes, graph))

    def test_missing_provisional_cost_never_becomes_zero(self):
        table = {'unit': 'abstract_software_tick', 'hardware_clock_claim': False,
                 'calibration': 'PROVISIONAL_UNCALIBRATED', 'values': {'native:FADD': 9}}
        c.validate_cycles(table, ['native:FADD'])
        for costs in [{}, {'native:FADD': 0}, {'native:FADD': None}]:
            table['values'] = costs
            with self.assertRaises(ValueError): c.validate_cycles(table, ['native:FADD'])

    def test_finite_provisional_extent_demand_exact(self):
        layout = {'spill_resident_bindings': [{'rank_group': [0], 'fits': False,
            'source_extent': {'base': 4096, 'bytes': 512}, 'required_bytes': 4096,
            'provider_ABI': {'AW': 34}}]}
        demand = c.extent_demands(layout)[0]
        self.assertEqual(demand['additional_bytes'], 3584)
        self.assertEqual(demand['alignment_bytes'], 512)
        self.assertIn('NOT an allocated source address', demand['calendar_binding'])

    def test_shape_expression_never_evaluates_tensor_values(self):
        env = {'x': c.Shape((4, 16))}
        self.assertEqual(c.shape_expression('x[:,0::2]', env).shape, (4, 8))
        self.assertEqual(c.shape_expression('reshape(x, (-1,8))', env).shape, (8, 8))
        self.assertEqual(c.shape_expression('x[...,None]', env).shape, (4,16,1))
        with self.assertRaises(ValueError): c.shape_expression("__import__('os').system('false')", env)

    def test_nested_recipe_counts_are_instruction_dependent(self):
        native = {'source_program': {'context_capacity': 8}, 'operands': [
            {'version': 'a', 'shape': [8]}]}
        plan = {'recipe': [{'op': 'FOR', 'var': 'i', 'start': '0', 'stop': '8', 'step': '1',
            'body': [{'op': 'FMUL', 'dst': 'x', 'src': ['input0[i]', 'f32(2)'], 'round_point': 'FP32_RNE'}]}]}
        macro = {'reads': ['a'], 'opcode': 'SCALAR_MUL', 'golden_contract': 'separately rounded FMUL'}
        table = {'values': {k: 2 for k in ['admit','RF_read','RF_write_ACK','consume','retire',
            'HBM_read_sector','HBM_write_sector','forward_CDC','reverse_CDC','visibility_fence','native:FMUL','native:STAGE_OPERAND','owner_lookup','owner_held_accept','validated_reverse_grant']}}
        program = c.bind_recipe(native, plan, macro, 0, table)
        loop = program['primitive_tree'][-1]['body'][0]
        self.assertEqual(loop['count'], 8)
        self.assertEqual(loop['duration'], 8*loop['iteration_stride']+2)
        self.assertGreater(program['finite_scratch_bytes'], 0)
        table['values']['native:FMUL'] = 7
        slower = c.bind_recipe(native, plan, macro, 0, table)
        self.assertEqual(slower['duration']-program['duration'], 8*5)

    def test_complete_recipe_pipeline_and_replay_positive(self):
        graph = {'operands': [
            {'id':'a','name':'a','birth_pc':-1,'retire_pc':0,'elements_per_rank':[8,8],
             'bits_per_element':32,'external_source':True},
            {'id':'b','name':'b','birth_pc':0,'retire_pc':0,'elements_per_rank':[8,8],
             'bits_per_element':32,'external_source':False}],
            'operations':[{'pc':0,'opcode':'FMUL','participants':[0,1],'reads':['a'],'writes':['b'],
                'dependencies':[],'missing_native_endpoints':[],'golden_contract':'separate F32 product',
                'source':{'path':'fixture'}}]}
        layout = {'homes':[{'version':v,'name':v,'rank_group':[0,1],'SM':0,'word_count':8,
            'birth_pc':birth,'retire_pc':0,'home':{'class':'RF','slot_first':slot,'vectors':1}}
            for v,birth,slot in [('a',-1,32),('b',0,33)]],
            'spill_resident_bindings':[], 'selected_command_bindings':{'bindings':[], 'command_templates':{}}}
        native = {'schema':'opentallas.H3.qwen-complete-native-software.v1',
            'source_program':{'context_capacity':8},'operands':[{'version':'a','name':'a','shape':[8]}],
            'operations':[{'pc':0,'opcode':'FMUL','reads':['a'],'writes':['b'],
            'recipe':[{'op':'FMUL','dst':'out0','src':['input0','f32(2)'],'round_point':'FP32_RNE'}]}]}
        table = c.cycle_table({'Qwen':graph},{'Qwen':layout}); table['values']['native:FMUL']=7
        result = c.compile_target('Qwen',graph,layout,table,native)
        self.assertTrue(result['native_operator_lowering_complete'])
        self.assertEqual(result['native_primitive_batch_counts']['FMUL'],2)
        self.assertEqual(result['status'],'PASS_COMPLETE_NATIVE_SOFTWARE_CALENDAR')
        self.assertEqual(c.encode(result),c.encode(c.compile_target('Qwen',graph,layout,table,native)))
        byid = {e['id']:e for e in result['events']}
        pc = result['PCs'][0]
        self.assertLess(byid[pc['consume']]['end'],byid[pc['retire']]['end'])
        for program in result['native_programs'].values():
            c.verify_native_program(program)
            bad = copy.deepcopy(program); bad['primitive_tree'][-1]['duration']-=1
            with self.assertRaises(ValueError):c.verify_native_program(bad)
        native['operations'][0]['reads']=['wrong-version']
        with self.assertRaisesRegex(ValueError,'version mismatch'):
            c.compile_target('Qwen',graph,layout,table,native)

    def test_primitive_scratch_alias_and_loop_tampering_rejected(self):
        # Finite storage proof is independently replayable without a numerical VM.
        p = {'duration':2,'primitive_tree':[],'empty_owned_extent_control_cycles':2,
             'finite_scratch_bytes':1024,'scratch_homes':{
             'a':{'byte_offset':0,'buffer_bytes':512,'buffers':2}}}
        self.assertEqual(c.verify_native_program(p),{})
        p['scratch_homes']['b']={'byte_offset':0,'buffer_bytes':512,'buffers':1}
        with self.assertRaisesRegex(ValueError,'alias'):c.verify_native_program(p)

    def test_producer_temporary_allocations_and_exact_counts_gate(self):
        native={'source_program':{'context_capacity':8},'operands':[{'version':'a','shape':[8]}]}
        plan={'pc':0,'recipe':[{'op':'FMUL','dst':'out0','src':['input0','f32(2)'],'round_point':'FP32_RNE'}],
            'temporary_storage':{'spill_bytes':512,'allocations':{'out0':{'bytes':32,'version':'PC0.tmp.out0',
              'lease':'PC0.workspace','release_after':'PC0.retire',
              'home':{'class_':'spill','byte_offset':0,'base_by_rank':{'0':4096}}}}},
            'calendar_counts_full_context':{'by_primitive':{'FMUL':{'native_vector_beats':1}}}}
        macro={'reads':['a'],'opcode':'FMUL','golden_contract':'F32 product'}
        table={'values':{k:2 for k in ['admit','RF_read','RF_write_ACK','consume','retire','HBM_read_sector',
            'HBM_write_sector','forward_CDC','reverse_CDC','visibility_fence','owner_lookup','owner_held_accept',
            'validated_reverse_grant','native:STAGE_OPERAND','native:FMUL']}}
        result=c.bind_recipe(native,plan,macro,0,table)
        self.assertEqual(result['finite_scratch_bytes'],512)
        self.assertEqual(result['scratch_homes']['out0']['buffers'],1)
        self.assertEqual(result['producer_vector_count_gate'],'PASS_EXACT_EXPORTED_NATIVE_COUNTS')
        plan['calendar_counts_full_context']['by_primitive']['FMUL']['native_vector_beats']=2
        with self.assertRaisesRegex(ValueError,'vector count mismatch'):c.bind_recipe(native,plan,macro,0,table)

    def test_actual_r17_provider_homes_and_release_controls(self):
        path = ROOT / 'results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_provider_binding.json.gz'
        providers = c.read_json(path); graphs, layouts = c.load_inputs(); graph=graphs['Qwen']
        fallback = c.version_homes(graph,layouts['Qwen'],2)
        homes, reuse, releases, ops = c.bind_provider_homes(providers,graph,fallback)
        self.assertTrue(c.check_homes(homes,graph))
        self.assertEqual(len(ops),1737)
        self.assertTrue(reuse)
        self.assertEqual(sum(map(len,releases.values())),31232)
        spill = next(h for entries in homes.values() for h in entries if h['home']['class']=='spill')
        self.assertIn('global_byte_base',spill['home'])
        self.assertEqual(providers['resource_contract']['owner_lookup_bound']['serialized_lookup_edges'],12)
        bad = dict(providers); bad['reuse_dependencies']=[{'new_home':'absent','wait_release':'absent'}]
        with self.assertRaisesRegex(ValueError,'reuse dependency identity'):
            c.bind_provider_homes(bad,graph,fallback)

    def test_persistent_future_reader_prevents_generation_reuse(self):
        graph={'operands':[{'id':'old','birth_pc':-1,'retire_pc':4},
                           {'id':'new','birth_pc':3,'retire_pc':5}]}
        homes={(v['id'],0):[{'SM':0,'home':{'class':'persistent','object':'window.L0','bytes':512}}]
               for v in graph['operands']}
        with self.assertRaisesRegex(ValueError,'future readers'):c.check_homes(homes,graph)
        graph['operands'][0]['retire_pc']=3
        self.assertTrue(c.check_homes(homes,graph))

    def test_archived_source_graphs_have_exact_coverage(self):
        graphs, layouts = c.load_inputs()
        self.assertEqual({t: len(g['operations']) for t,g in graphs.items()}, {'Qwen':1737,'DeepSeek':2213})
        self.assertEqual({t:len({o['opcode'] for o in g['operations']}) for t,g in graphs.items()}, {'Qwen':21,'DeepSeek':30})
        for t,g in graphs.items():
            homes = c.version_homes(g, layouts[t], 2 if t=='Qwen' else 96)
            self.assertTrue(c.check_homes(homes,g))


if __name__ == '__main__': unittest.main()
