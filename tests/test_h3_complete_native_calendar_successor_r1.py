"""Finite calendar controls: temporal, ownership, arithmetic-interface and replay."""
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Resolve the canonical dependency before legacy tests can leave another
# checkout on sys.path. Preserve the imported module and its runtime functions.
import sys
_collection_path=list(sys.path)
try:
    sys.path.insert(0,str(ROOT/'tools'))
    import h3_complete_native_calendar as _canonical_original
finally:
    sys.path[:]=_collection_path
if Path(_canonical_original.__file__).resolve()!=ROOT/'tools/h3_complete_native_calendar.py':
    raise ValueError('canonical original calendar imported from another checkout')
spec = importlib.util.spec_from_file_location('h3calendar', ROOT / 'tools/h3_complete_native_calendar_successor_r1.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class AdditiveFiniteCalendarTests(unittest.TestCase):
    def setUp(self):
        import sys
        saved_path=list(sys.path)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None),saved_path))

    def test_additive_module_has_own_executor_globals_and_preserves_original_pin(self):
        import hashlib,ast
        original=ROOT/'tools/h3_complete_native_calendar.py'
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),'c0370e63dba0eadcc06c5522c28a956ddebfd10af9b8765a61fe0e4fe025b817')
        self.assertIs(c.execute_ds_provider_group128.__globals__,vars(c))
        self.assertEqual(Path(c.execute_ds_provider_group128.__code__.co_filename).resolve(),ROOT/'tools/h3_complete_native_calendar_successor_r1.py')
        def executor(raw):
            return ast.dump(next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='execute_ds_provider_group128'),include_attributes=False)
        self.assertEqual(executor(original.read_bytes()),executor(Path(c.__file__).read_bytes()))

    def test_shared64_columns_use_real_strides_and_charge_entire_port(self):
        codes=c.qwen_shared64_layout(128,32,1)
        self.assertEqual(codes['fill64_transactions'],64)
        self.assertEqual(codes['column64_transactions'],2048)
        self.assertEqual(codes['old_packed128_read_transactions'],32)
        fp=c.qwen_shared64_layout(128,16,4)
        self.assertEqual(fp['fill64_transactions'],128)
        self.assertEqual(fp['column64_transactions'],2048)
        self.assertEqual(fp['old_packed128_read_transactions'],64)
        for n,k,w in [(3,5,1),(7,3,4),(128,1,4),(64,32,1)]:
            plan=c.qwen_shared64_layout(n,k,w,base=64)
            seen=set()
            for col in plan['column_reads']:
                for beat in col['beat_reads']:
                    self.assertEqual(beat['payload_bytes'],64)
                    for word in beat['selected_words']:
                        address=beat['byte_address']+word['byte_offset']
                        self.assertEqual(address,64+(word['row']*k+col['column'])*w)
                        seen.add((word['row'],col['column']))
            self.assertEqual(len(seen),n*k)
        with self.assertRaisesRegex(ValueError,'region exhausted'):
            c.qwen_shared64_layout(128,32,4,base=64)
        with self.assertRaisesRegex(ValueError,'bounded row-major'):
            c.qwen_shared64_layout(129,1,4)

    def test_program_constrained_owner_census_and_span_descriptor_repeats(self):
        b=ROOT/c.OUT/'c0_program_shared64_r1';a=c.read_json(b/'program_owner_admission.json.gz')
        self.assertFalse(a['unconstrained_H1_three_valid_starvation_is_actual_program_deadlock_proof'])
        self.assertTrue(a['source_context_excludes_simultaneous_three_valid_admission'])
        self.assertIsNone(a['installed_parent_owner_grant_producer'])
        self.assertEqual(a['incremental_fair_arbiter_gate_equivalents_adopted'],0)
        for name,n in [('DeepSeek',2213),('Qwen',1737)]:
            self.assertEqual(a['programs'][name]['PCs'],n)
            for row in a['programs'][name]['PC_DAG']:
                self.assertTrue(all(d<row['PC'] for d in row['dependencies']))
                self.assertTrue(row['future_version_readers_do_not_hold_RF_command_owner'])
        q=c.read_json(b/'Qwen_shared64_full_context.json.gz');fill=read=tiles=0
        self.assertEqual(q['shared_dot_PC_count'],434)
        for row in q['PCs']:
            for desc in row['dot_tiles']:
                layout=q['layouts'][desc['layout']];n=desc['tile_repeat']
                self.assertEqual(n,desc['head_repeat']*desc['row_repeat']*desc['column_chunk_repeat']*desc.get('split_repeat',1))
                fill+=n*layout['fill64_transactions'];read+=n*layout['column64_transactions'];tiles+=n
                self.assertIsNone(desc['actual_consumer_reverse_bound'])
        self.assertEqual((fill,read,tiles),(q['fill64_transactions'],q['column64_transactions'],q['total_tile_leases']))
        self.assertEqual(read,5067505664)
        self.assertFalse(q['installed_tile_gather_endpoint'])
        control=c.read_json(b/'Qwen_shared64_position17_control.json.gz')
        self.assertLess(control['column64_transactions'],read)
        with self.assertRaisesRegex(ValueError,'archive required'):
            c.compile_qwen_shared64_spans(b'forged',b'forged')

    def test_owner_reverse_wait_on_next_admission_is_detected_as_deadlock(self):
        legal=[{'id':'capture0','dependencies':[],'source_bound_edges':3},
            {'id':'reverse0','dependencies':['capture0']},
            {'id':'admit1','dependencies':['reverse0']}]
        result=c.verify_finite_owner_dependency_graph(legal)
        self.assertEqual(result['topological_order'],['capture0','reverse0','admit1'])
        self.assertEqual(result['missing_service_bounds'],['reverse0','admit1'])
        self.assertFalse(result['hardware_finite_wait_admitted'])
        forged=copy.deepcopy(legal);forged[1]['source_bound_edges']=0
        with self.assertRaisesRegex(ValueError,'cannot be zero'):c.verify_finite_owner_dependency_graph(forged)
        deadlock=copy.deepcopy(legal);deadlock[0]['dependencies']=['admit1']
        with self.assertRaisesRegex(ValueError,'owner/consumer/reverse dependency deadlock'):
            c.verify_finite_owner_dependency_graph(deadlock)
        deadlock[0]['dependencies']=['missing_installed_sink']
        with self.assertRaisesRegex(ValueError,'missing actual endpoint'):
            c.verify_finite_owner_dependency_graph(deadlock)

    def test_complete_first_tile_packet_controls_have_real_homes_and_one_atomic_lease(self):
        b=ROOT/c.OUT/'c0_program_shared64_r1';controls=c.read_json(b/'first_tile_packet_controls.json.gz')
        for family,x in controls.items():
            packets=x['packets']
            self.assertEqual(len({tuple(p['owner']) for p in packets}),1)
            self.assertEqual([p['sequence'] for p in packets],list(range(packets[0]['sequence'],packets[0]['sequence']+len(packets))))
            self.assertEqual(sum(p['eligible_for_tile_owner_release'] for p in packets),1)
            self.assertTrue(packets[-1]['eligible_for_tile_owner_release'])
            for p in packets:
                self.assertEqual(p['payload_bytes'],64)
                self.assertIsNone(p['actual_payload_sha256'])
                self.assertIsNone(p['actual_consumer_reverse_receipt'])
                self.assertFalse(p['actual_owner_released'])
                if p['phase']=='shared_fill64':
                    for v in p['sources']:
                        source=v['source'];self.assertTrue(source['provider_ref']);self.assertTrue(source['lease'])
                        if family=='MATRIX':self.assertGreaterEqual(source['byte_address'],0)
                        else:
                            self.assertIn(source['class_'],['RF','spill'])
                            self.assertLessEqual(x['PC'],source['retire_PC'])
        self.assertEqual(len(controls['MATRIX']['packets']),2112)
        self.assertEqual(len(controls['SCORES']['packets']),16)
        self.assertEqual(len(controls['PV']['packets']),2176)
        operand={'version':'source','birth_pc':0,'retire_pc':2,'lease':'lease',
            'homes':[{'rank':0,'SM':0,'word_count':256,'provider_ref':'retained',
                      'home':{'class':'RF','slot_first':32,'vectors':2}}]}
        h=c.qwen_source_word_home(operand,129,1)
        self.assertEqual((h['slot'],h['lane']),(33,1))
        self.assertEqual(h['mirror_byte_offsets'][1]-h['mirror_byte_offsets'][0],262144)
        with self.assertRaisesRegex(ValueError,'live actual'):c.qwen_source_word_home(operand,0,3)
        with self.assertRaisesRegex(ValueError,'coordinate exhausted'):c.qwen_source_word_home(operand,256,1)

    def test_source_sector_progress_has_positive_software_costs_and_unknown_hardware(self):
        b=ROOT/c.OUT/'c0_program_shared64_r1'
        raw=gzip.decompress((b/'hbm_provider_microvm_r21.py.gz').read_bytes())
        x=c.derive_source_sector_provider_progress(raw)
        self.assertEqual(x['conservative_accepted_owner_release_upper_software_ticks'],512)
        self.assertEqual(x['service_reservation_software_ticks'],dict(read_to_capture=83,write_to_visible=103,reverse_to_tag_release=25))
        self.assertIsNone(x['hardware_cycles_or_ns']);self.assertIsNone(x['asynchronous_held_consumer_upper'])
        self.assertFalse(x['current_full_program_every_provider_actor_connected'])
        with self.assertRaisesRegex(ValueError,'source pin'):c.derive_source_sector_provider_progress(raw+b'\n')

    def test_compact_installer_preserves_exact_constructor_and_actual_payload_replay(self):
        import sys,tempfile,hashlib
        sys.path.insert(0,str(ROOT/'tools'))
        import hbm_bound_event_journal_r30 as original
        from hbm_provider_microvm_r21 import Identity
        saved={name:getattr(original,name) for name in ['BoundSectorProvider','DiskEvents','JournalBudget']}
        try:
            ctor=original.BoundSectorProvider.__init__
            proof=c.install_compact_provider_journals_preserving_constructor([original])
            self.assertIs(original.BoundSectorProvider.__init__,ctor)
            self.assertTrue(proof['production_factory_constructor_guard_preserved'])
            with tempfile.TemporaryDirectory() as tmp:
                budget=original.JournalBudget(Path(tmp)/'journal',1<<22)
                provider=original.BoundSectorProvider({('DeepSeek',95):[dict(base=0,bytes=32)]},journal_budget=budget,tags=1,
                    allocation_identity=dict(PC=10,rank=95,SM=31,generation=1,tile=63,template='f'*64,die=95,address_class='shared'))
                for serial,write in [(0,True),(1,False)]:
                    tx=provider.submit(Identity('DeepSeek',95,1,10,serial,0),write=write,payload=b'x'*32 if write else b'')
                    value=provider.wait(tx);provider.finish(tx)
                    if not write:self.assertEqual(value,b'x'*32)
                rows=list(provider.events)
                self.assertEqual(provider.events.validator.live,{})
                self.assertTrue(any(v.get('payload_sha256')==hashlib.sha256(b'x'*32).hexdigest() for v in rows))
                self.assertEqual(sum(v['event']=='validated_reverse_grant' for v in rows),2)
                provider.events.close();self.assertEqual(list(provider.events),rows);budget.db.close()
        finally:
            for name,value in saved.items():setattr(original,name,value)

    def test_r46_source_compact_bound_preserves_all_other_components_and_refuses_mutants(self):
        b=ROOT/c.OUT/'c0_program_shared64_r1'
        projection=c.read_json(b/'R46_conservative_projection.json.gz');union=c.read_json(b/'R46_shared_source_union.json')
        names=['tools/ds_hbm_pc10_projection_r46.py','tools/ds_hbm_pc10_journal_model_r44.py',
            'tools/h4_hbm_w19_pc10_endpoints.py','tools/hbm_provider_microvm_r21.py']
        sources={n:gzip.decompress((b/(Path(n).name+'.gz')).read_bytes()) for n in names}
        x=c.project_r46_compact_shared_journal(projection,union,sources)
        self.assertEqual(x['complete_disk_reservation_bytes'],819950818992)
        self.assertEqual(x['compact_shared_component_bytes'],3816210432)
        self.assertEqual(x['maximum_events'],1769472*8)
        for name,value in projection['components'].items():
            if name!='additional_PC10_shared_sector_journals':self.assertEqual(x['components'][name],value)
        self.assertFalse(x['sampled_compression_ratio_used']);self.assertFalse(x['actual_state_restored'])
        self.assertFalse(x['PC10_numerical_launch_performed'])
        bad=copy.deepcopy(union);bad['conservative_union_schema'].pop('allocation_identity')
        with self.assertRaisesRegex(ValueError,'source-derived shared union'):c.project_r46_compact_shared_journal(projection,bad,sources)
        bad=copy.deepcopy(projection);bad['components']['additional_PC10_shared_sector_journals']-=1
        with self.assertRaisesRegex(ValueError,'complete R46 projection'):c.project_r46_compact_shared_journal(bad,union,sources)
        sources[names[0]]+=b'\n'
        with self.assertRaisesRegex(ValueError,'source schema pin'):c.project_r46_compact_shared_journal(projection,union,sources)

    def test_actual_qwen_terminal_counts_do_not_admit_finite_hardware_service(self):
        b=ROOT/c.OUT/'c0_program_shared64_r1'
        x=c.read_json(b/'Qwen_actual_runtime_demand_join.json')
        self.assertFalse(x['hardware_qualified'])
        self.assertEqual(x['PCs'],1737)
        self.assertEqual(x['position'],0)
        self.assertEqual(x['compiler64B_dot_demand']['column_read'],3784205312)
        self.assertEqual(x['compiler64B_dot_demand']['fill'],118408192)
        raw=(b/'Qwen_actual_native_terminal.json').read_bytes()
        with self.assertRaises(ValueError):c.join_qwen_actual_terminal_demands(b'bad',b'bad',raw,raw)

    def test_sagan_collective_aliases_and_specialist_lease_gaps_are_not_zero(self):
        b=ROOT/c.OUT/'c0_program_shared64_r1';x=c.read_json(b/'DS_fullgraph_continuation_obligations.json.gz')
        self.assertEqual(x['alias_versions'],280);self.assertEqual(x['alias_rank_publications'],26880)
        self.assertEqual(x['alias_logical_32bit_words'],61931520)
        self.assertTrue(x['specialist_source_bindings'])
        for binding in x['specialist_source_bindings']:
            self.assertTrue(binding['leased_versions']);self.assertIsNone(binding['exact_acquired_fragment_transaction_count'])
        self.assertIsNone(x['complete_continuation_journal_disk_reservation'])
        self.assertIsNone(x['actual_payload_checkpoint_disk_reservation'])
        self.assertFalse(x['prefix10_projection_includes_PC11_2212'])

    def test_actual_provider_checkpoint_preserves_payload_masks_identity_and_atomic_disk(self):
        import tempfile,sys
        sys.path.insert(0,str(ROOT/'tools'))
        from hbm_provider_microvm_r21 import SectorProvider,Identity
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.bin';p=SectorProvider({('DeepSeek',95):[dict(base=0,bytes=64)]},tags=1)
            p.seed('DeepSeek',95,0,b'abc')
            tx=p.submit(Identity('DeepSeek',95,1,9,0,1),write=True,payload=bytes(range(32)));p.wait(tx);p.finish(tx)
            owners=dict(published=[dict(version='actual.PC9',rank=95,sha256='retained_actual_digest')],leases=['future.PC10.read'])
            header,raw,size=c._actual_provider_checkpoint_plan([('RF95',p)],owners)
            self.assertEqual(size,16+len(raw)+120+32)
            with self.assertRaises(BufferError):c.write_actual_provider_checkpoint(path,[('RF95',p)],owners,size-1)
            self.assertFalse(path.exists())
            receipt=c.write_actual_provider_checkpoint(path,[('RF95',p)],owners,size)
            self.assertEqual(path.stat().st_size,size);self.assertEqual(receipt['atomic_peak_bytes'],size)
            fresh=SectorProvider(p.extents,tags=1)
            restored=c.restore_actual_provider_checkpoint(path,[('RF95',fresh)])
            self.assertEqual(fresh.backing,p.backing);self.assertEqual(fresh.generations,p.generations)
            self.assertEqual(restored['owner_state'],owners)
            self.assertFalse(restored['complete_runtime_resume_qualified'])
            again=c.write_actual_provider_checkpoint(path,[('RF95',p)],owners,size)
            self.assertEqual(again['atomic_peak_bytes'],2*size)
            changed=bytearray(path.read_bytes());changed[-33]^=1;path.write_bytes(changed)
            empty=SectorProvider(p.extents,tags=1)
            with self.assertRaisesRegex(ValueError,'payload digest'):c.restore_actual_provider_checkpoint(path,[('RF95',empty)])
            self.assertFalse(empty.backing)

    def test_actual_provider_checkpoint_refuses_live_owner_without_clearing_debt(self):
        import sys,tempfile
        sys.path.insert(0,str(ROOT/'tools'))
        from hbm_provider_microvm_r21 import SectorProvider,Identity
        p=SectorProvider({('DeepSeek',0):[dict(base=0,bytes=32)]})
        tx=p.submit(Identity('DeepSeek',0,1,9,0,0),write=True,payload=bytes(32))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'drained fault-free'):c.write_actual_provider_checkpoint(Path(tmp)/'state.bin',[('RF0',p)],{},1<<20)
            self.assertIn(tx.tag,p.live);self.assertFalse(list(Path(tmp).iterdir()))

    def test_selected_r4_every_command_and_parent_wait_is_finite_DAG_but_unknown_service(self):
        b=ROOT/c.OUT/'c0_program_shared64_r1';x=c.read_json(b/'selected_r4_owner_wait_calendar.json.gz')
        self.assertEqual((x['RMW_commands'],x['shared64_children']),(288,9216))
        self.assertEqual(len(x['calendar_rows']),9504)
        self.assertEqual(x['known_local_reference_edge_terms']['both_copy_write'],576)
        self.assertEqual(x['known_local_reference_edge_terms']['shared_read64'],13824)
        self.assertEqual(x['known_local_reference_edge_terms']['shared_write64'],9216)
        self.assertEqual(sum(p['children'] for p in x['shared_parent_rows']),9216)
        nodes=[phase for row in x['calendar_rows'] for phase in row['phases']]
        nodes.extend(phase for row in x['shared_parent_rows'] for phase in row['phases'])
        proof=c.verify_finite_owner_dependency_graph(nodes)
        self.assertTrue(proof['missing_service_bounds'])
        self.assertFalse(proof['hardware_finite_wait_admitted']);self.assertIsNone(x['whole_token_latency'])
        self.assertEqual(x['additional_C0_V1_I64_provider_cost'],0)
        self.assertEqual(x['independent_mirror_ACK_cost_added'],0)

    def test_actual_storage_join_refuses_unknown_checkpoint_and_insufficient_atomic_peak(self):
        journal={'complete_disk_reservation_bytes':1000}
        x=c.compose_actual_checkpoint_storage_admission(journal,None,available_bytes=5000,additional_new_bytes=0)
        self.assertIsNone(x['required_new_disk_bytes']);self.assertFalse(x['actual_runtime_GO'])
        checkpoint=dict(payload_bytes=200,typed_state_metadata_bytes=100,filesystem_reservation_bytes=400,old_journal_bytes=50)
        x=c.compose_actual_checkpoint_storage_admission(journal,checkpoint,available_bytes=1500,additional_new_bytes=200)
        self.assertEqual(x['required_new_disk_bytes'],1600);self.assertEqual(x['atomic_temporary_peak_bytes'],400)
        self.assertEqual(x['status'],'REFUSE_ACTUAL_STORAGE_HEADROOM')
        checkpoint['filesystem_reservation_bytes']=299
        with self.assertRaisesRegex(ValueError,'payload/metadata'):c.compose_actual_checkpoint_storage_admission(journal,checkpoint,available_bytes=5000,additional_new_bytes=0)


if __name__ == '__main__': unittest.main()
