import copy
import gzip
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('causal_grants', ROOT / 'tools/h3_complete_native_calendar_grants_r1.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class CausalAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindings, cls.inventory = m.build_inventory()

    def setUp(self):
        self.ledger = m.CausalGrantLedger(self.bindings)
        self.parent = next(p for p in self.bindings['parents'].values() if p['scope'] == 'actual_all96_PC0_RMW')
        self.edge = 0

    def event(self, name, **extra):
        row = dict(parent=self.parent['id'], binding_sha256=self.parent['binding_sha256'],
                   owner=self.parent['owner'], lease=self.parent['lease'], domain='H1_streaming',
                   edge=self.edge, origin='directed_verifier_control', event=name, accepted=True)
        row.update(extra)
        return row

    def grant(self):
        self.ledger.observe(self.event('parent_grant'))

    def issue(self, child):
        d = self.bindings['children'][child]
        self.ledger.observe(self.event('child_issue', child=child, source_command_sha256=d['source_command_sha256'],
                                      provider_reference=d['provider_reference'], valid=True, ready=True))
        return d

    def complete(self, child):
        d = self.issue(child)
        for bank in d['expected_SRAMs']:
            self.ledger.observe(self.event('SRAM_accept', child=child, SRAM=bank, write=d['write']))
        self.edge += 1
        if not d['write']:
            for bank in d['expected_SRAMs']:
                self.ledger.observe(self.event('SRAM_capture', child=child, SRAM=bank))
            self.edge += 1
        self.ledger.observe(self.event('child_ACK', child=child, valid=True, ready=True))
        self.edge += 1
        self.ledger.observe(self.event('child_reverse', child=child))
        self.edge += 1

    def test_actual_RMW_parent_all_banks_common_ACK_and_reverse_control(self):
        self.grant()
        for child in self.parent['children']:
            self.complete(child)
        for name in ('visibility_fence', 'consumer', 'reverse'):
            self.ledger.observe(self.event(name)); self.edge += 1
        result = self.ledger.summary()
        self.assertEqual(result['events']['SRAM_accept'], 96)
        self.assertEqual(result['events']['SRAM_capture'], 64)
        self.assertEqual(result['events']['child_ACK'], 3)
        self.assertEqual(result['physical_credit_debt'], 0)
        self.assertFalse(result['hardware_qualified'])
        self.assertEqual(result['observation_origins'], ['directed_verifier_control'])

    def test_one_missing_bank_cannot_ACK_or_publish(self):
        self.grant(); child = self.parent['children'][0]; d = self.issue(child)
        for bank in d['expected_SRAMs'][:-1]:
            self.ledger.observe(self.event('SRAM_accept', child=child, SRAM=bank, write=False))
        self.edge += 2
        with self.assertRaisesRegex(ValueError, 'all SRAM'):
            self.ledger.observe(self.event('child_ACK', child=child, valid=True, ready=True))
        with self.assertRaisesRegex(ValueError, 'all source children'):
            self.ledger.observe(self.event('visibility_fence'))
        self.assertEqual(self.ledger.summary()['physical_credit_debt'], 1)

    def test_wrong_page_copy_row_or_write_not_source_acceptance(self):
        for change in ([0, 0, 1, 43], [2, 0, 0, 43], [0, 0, 0, 44]):
            self.setUp(); self.grant(); child = self.parent['children'][0]; self.issue(child)
            with self.assertRaisesRegex(ValueError, 'copy/bank/page/row'):
                self.ledger.observe(self.event('SRAM_accept', child=child, SRAM=change, write=False))
        with self.assertRaisesRegex(ValueError, 'same-go'):
            self.ledger.observe(self.event('SRAM_accept', child=child, SRAM=[0, 0, 0, 43], write=True))

    def test_held_ACK_and_reverse_cannot_free_parent_or_admit_contender(self):
        self.grant(); child = self.parent['children'][0]; d = self.issue(child)
        for bank in d['expected_SRAMs']:
            self.ledger.observe(self.event('SRAM_accept', child=child, SRAM=bank, write=False))
        self.edge += 1
        for bank in d['expected_SRAMs']:
            self.ledger.observe(self.event('SRAM_capture', child=child, SRAM=bank))
        self.edge += 1
        with self.assertRaisesRegex(ValueError, 'all SRAM'):
            self.ledger.observe(self.event('child_ACK', child=child, valid=True, ready=False))
        with self.assertRaisesRegex(ValueError, 'reverse lease'):
            self.ledger.observe(self.event('reverse'))
        with self.assertRaisesRegex(ValueError, 'credit exhausted'):
            self.ledger.observe(self.event('parent_grant'))
        self.assertEqual(self.ledger.summary()['physical_credit_debt'], 1)

    def test_source_owner_lease_reference_and_domain_required(self):
        for key, value in [('owner', [2, 0, 1, 0, 0]), ('lease', 'foreign'), ('binding_sha256', '0' * 64)]:
            with self.assertRaisesRegex(ValueError, 'source parent'):
                self.ledger.observe(self.event('parent_grant', **{key: value}))
        with self.assertRaisesRegex(ValueError, 'CDC'):
            self.ledger.observe(self.event('parent_grant', domain='serial_chain'))
        with self.assertRaisesRegex(ValueError, 'software ticks'):
            self.ledger.observe(self.event('parent_grant', origin='software_provider'))
        self.assertFalse(self.ledger.live)

    def test_duplicate_or_later_bank_event_rejected_without_new_credit(self):
        self.grant(); child = self.parent['children'][0]; self.issue(child)
        row = self.event('SRAM_accept', child=child, SRAM=[0, 0, 0, 43], write=False)
        self.ledger.observe(row)
        with self.assertRaisesRegex(ValueError, 'distinct bank'):
            self.ledger.observe(row)
        with self.assertRaisesRegex(ValueError, 'same-go'):
            self.ledger.observe(dict(row, SRAM=[0, 1, 0, 43], edge=1))
        self.assertEqual(self.ledger.summary()['physical_credit_debt'], 1)

    def test_actual_shared_two_banks_and144_children_are_parent_held(self):
        self.parent = next(p for p in self.bindings['parents'].values() if p['scope'].startswith('directed_PC10'))
        self.assertEqual(len(self.parent['children']), 144)
        self.grant()
        for child in self.parent['children']:
            self.complete(child)
        self.assertEqual(self.ledger.summary()['events']['SRAM_accept'], 288)
        self.assertEqual(self.ledger.summary()['physical_credit_debt'], 1)
        for name in ('visibility_fence', 'consumer', 'reverse'):
            self.ledger.observe(self.event(name)); self.edge += 1
        self.assertEqual(self.ledger.summary()['physical_credit_debt'], 0)

    def test_actual_journal_inventory_is_not_endpoint_timing(self):
        x = self.inventory
        self.assertEqual(x['actual_PC0_transactions'], 738816)
        self.assertEqual(x['actual_software_mirror_write_pairs'], 246144)
        self.assertEqual(x['physical_child_obligations'], 10080)
        self.assertEqual(x['demand']['RF:write'], 288)
        self.assertEqual(x['demand']['RF:read'], 576)
        self.assertEqual(x['demand']['shared64:write'], 4608)
        self.assertEqual(x['demand']['shared64:read'], 4608)
        self.assertEqual(x['production_endpoint_observations'], 0)
        self.assertIsNone(x['whole_token_latency'])
        self.assertEqual(x['additional_cost'], 0)
        self.assertFalse(x['all_program_physical_grants_complete'])

    def test_parent_order_dependency_blocks_future_child_source(self):
        first = self.parent
        second = next(p for p in self.bindings['parents'].values() if first['id'] in p['dependencies'])
        self.parent = second
        with self.assertRaisesRegex(ValueError, 'dependencies'):
            self.grant()
        self.assertFalse(self.ledger.live)

    def test_bad_actual_shared_address_fails_extent(self):
        commands = json.loads(gzip.decompress((ROOT / m.SOURCES[-2]).read_bytes()))
        commands['shared64'][0]['scratch_byte_address'] = 65536
        with self.assertRaisesRegex(ValueError, 'shared64 extent'):
            m.compile_commands(commands, 'a' * 64)



class KVFiniteDAGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory,cls.native=m.load_qwen_kv_inputs()
        cls.dag=m.compile_qwen_kv_extension(cls.directory,cls.native)

    def test_actual_all72_KV_groups_and1737_native_dependency_frontiers(self):
        x=self.dag
        self.assertEqual(x['native_PC_frontiers'],1737)
        self.assertEqual(x['phase_counts']['KV_sector_old_capture'],18432)
        self.assertEqual(x['phase_counts']['KV_sector_write_visible'],19584)
        self.assertEqual(x['phase_counts']['KV_sector_read_capture'],19584)
        self.assertEqual(x['phase_counts']['KV_sector_reverse'],39168)
        self.assertEqual(x['phase_counts']['KV_state_record_visible'],72)
        self.assertEqual(x['phase_counts']['KV_state_bitmap_visible'],72)
        self.assertFalse(x['existing_native_cost_recharged'])
        self.assertIsNone(x['HBM_command_count'])

    def test_missing_actual_service_costs_and_native_frontiers_remain_unknown(self):
        x=m.schedule_finite_extension(self.dag,{}, {})
        self.assertEqual(x['status'],'UNKNOWN_COMPLETE_SERVICE_INPUTS')
        self.assertIn('KV_sector_old_capture',x['missing_phase_costs'])
        self.assertEqual(len(x['missing_native_frontiers']),1737)
        self.assertEqual(x['scheduled_nodes'],0)
        self.assertIsNone(x['whole_token_latency'])

    def test_actual_group_finite_positive_provisional_control_all_banks_retired(self):
        directory=copy.deepcopy(self.directory);directory['groups']=directory['groups'][:1]
        dag=m.compile_qwen_kv_extension(directory,self.native)
        kinds=set(dag['phase_counts'])-{'structural_frontier','existing_native_calendar_frontier'}
        costs={k:dict(units=7,provenance='explicit directed verifier estimate',scope='explicit_provisional_software') for k in kinds}
        frontiers={n['id']:1000000*(n['PC']+1) for n in dag['nodes'] if n['phase']=='existing_native_calendar_frontier'}
        result=m.schedule_finite_extension(dag,costs,frontiers)
        self.assertEqual(result['scheduled_nodes'],len(dag['nodes']))
        self.assertTrue(result['resource_credits_retired'])
        self.assertFalse(result['hardware_qualified'])
        self.assertIsNone(result['whole_token_latency'])
        nodes={n['id']:n for n in dag['nodes']}
        byid={n['id']:n for n in result['schedule']}
        for n in result['schedule']:
            self.assertTrue(all(byid[d]['finish']<=n['start'] for d in nodes[n['id']]['dependencies']))

    def test_all72_actual_groups_complete_finite_extension_under_explicit_control_inputs(self):
        kinds=set(self.dag['phase_counts'])-{'structural_frontier','existing_native_calendar_frontier'}
        costs={k:dict(units=7,provenance='explicit directed verifier estimate; not hardware',scope='explicit_provisional_software') for k in kinds}
        frontiers={n['id']:1000000*(n['PC']+1) for n in self.dag['nodes'] if n['phase']=='existing_native_calendar_frontier'}
        result=m.schedule_finite_extension(self.dag,costs,frontiers)
        self.assertEqual(result['scheduled_nodes'],198594)
        self.assertTrue(result['resource_credits_retired'])
        self.assertIsNone(result['whole_token_latency'])
        self.assertFalse(result['hardware_qualified'])
        self.assertFalse(result['native_cost_recharged'])

    def test_missing_cost_never_becomes_zero_or_nominal_CPU_ticks(self):
        costs={'KV_sector_old_capture':dict(units=0,provenance='no measurement',scope='source_bound_endpoint_model')}
        with self.assertRaisesRegex(ValueError,'positive explicit'):
            m.schedule_finite_extension(self.dag,costs,{})
        costs['KV_sector_old_capture']['units']=7;costs['KV_sector_old_capture']['scope']='CPU_elapsed_cycles'
        with self.assertRaisesRegex(ValueError,'positive explicit'):
            m.schedule_finite_extension(self.dag,costs,{})

    def test_changed_actual_operation_dependency_rejects(self):
        native=copy.deepcopy(self.native)
        pc=self.directory['groups'][0]['source_operation_bindings'][0]['pc']
        native['operations'][pc]['dependencies']=[]
        with self.assertRaisesRegex(ValueError,'source operation'):
            m.compile_qwen_kv_extension(self.directory,native)

    def test_metadata_bitmap_cannot_precede_record_and_sector_reverse(self):
        nodes={n['id']:n for n in self.dag['nodes']}
        bitmap=next(n for n in nodes.values() if n['phase']=='KV_state_bitmap_visible')
        self.assertEqual(nodes[bitmap['dependencies'][0]]['phase'],'KV_metadata_reverse')
        record=next(n for n in nodes.values() if n['id']==bitmap['id'].replace(':bitmap',':record'))
        pending=list(bitmap['dependencies']);seen=set()
        while pending:
            dep=pending.pop()
            if dep not in seen:
                seen.add(dep);pending.extend(nodes[dep]['dependencies'])
        self.assertIn(record['id'],seen)
        self.assertEqual(nodes[record['dependencies'][0]]['phase'],'KV_metadata_reverse')
        self.assertEqual(self.dag['phase_counts']['KV_metadata_old_capture'],144)

    def test_reachable_held_credit_deadlock_rejects_constructively(self):
        def n(key,dep,acquire=None,release=None):
            return dict(id=key,phase='test_source',dependencies=dep,bank=None,acquire=acquire,release=release)
        bank=['L2',0,0,0]
        dag={'nodes':[n('grantA',[],bank),n('grantB',['grantA'],bank),n('reverseA',['grantB'],release=bank)]}
        costs={'test_source':dict(units=3,provenance='directed source model control',scope='explicit_provisional_software')}
        with self.assertRaisesRegex(ValueError,'credit dependency deadlock'):
            m.schedule_finite_extension(dag,costs,{})

    def test_source_cycle_and_foreign_reverse_reject(self):
        n=lambda key,deps,acquire=None,release=None:dict(id=key,phase='test_source',dependencies=deps,bank=None,acquire=acquire,release=release)
        costs={'test_source':dict(units=3,provenance='directed estimate',scope='explicit_provisional_software')}
        with self.assertRaisesRegex(ValueError,'consumer/lease dependency deadlock'):
            m.schedule_finite_extension({'nodes':[n('a',['b']),n('b',['a'])]},costs,{})
        bank=['L2',0,0,0]
        with self.assertRaisesRegex(ValueError,'foreign reverse'):
            m.schedule_finite_extension({'nodes':[n('a',[],bank),n('b',[],release=bank)]},costs,{})



class OnceOnlyCostTests(unittest.TestCase):
    def test_actual_shape_provider_replacement_preserves_native_buckets(self):
        old=dict(interval_id='actual.provider.interval',program_sha256='f'*64,PC=10,rank=0,
            position=0,provider_ref='Qwen.rank0.extent.L0.K',cost_domain='explicit_provisional_software',
            provider_cost=100,protected_costs=dict(C0=11,V1=13,RF_mirrors=17,I64=19))
        new={k:v for k,v in old.items() if k not in ('provider_cost','protected_costs')}
        new['ordered_steps']=[dict(phase='old_capture',repetitions=256,cost_per_repetition=None),
                              dict(phase='write_visible',repetitions=256,cost_per_repetition=83)]
        result=m.replace_provider_interval_once(old,new,{})
        self.assertIsNone(result['replacement_provider_cost'])
        self.assertEqual(result['protected_costs'],old['protected_costs'])
        self.assertEqual(result['protected_costs_added'],0)
        with self.assertRaisesRegex(ValueError,'already replaced'):
            m.replace_provider_interval_once(old,new,{old['interval_id']:result})
        new['position']=8191
        with self.assertRaisesRegex(ValueError,'position/reference'):
            m.replace_provider_interval_once(old,new,{})
        self.assertEqual(old['provider_cost'],100)



class StrictOperatorJournalJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=ROOT/'results/uarch/h3_complete_native_calendar_20261002'
        cls.control=json.loads(gzip.decompress((base/'group128_execution_join_r1/actual_group128_execution.json.gz').read_bytes()))
        cls.inventory=json.loads(gzip.decompress((base/'portable_input_closure_r1/r34_portable_r4/source_inventory.json.gz').read_bytes()))
        cls.source=(ROOT/'tools/h3_complete_native_calendar.py').read_bytes()
        cls.bindings,_=m.build_inventory()

    def test_all_retained_source_calls_and_shared_children_resolve_actual_events(self):
        x=m.verify_shared_journal_source(self.bindings,self.control,self.inventory,self.source)
        self.assertEqual(x['source_resolved_calls'],1152)
        self.assertEqual(x['source_resolved_shared64_children'],9216)
        self.assertEqual(x['actual_shared_provider_events_verified'],138240)
        self.assertEqual(x['physical_SRAM_ACK_observations'],0)

    def test_nonempty_exporter_ref_is_not_a_source_instruction_proof(self):
        bindings=dict(self.bindings,children=dict(self.bindings['children']))
        key=next(k for k,v in bindings['children'].items() if v['kind']=='shared64')
        bindings['children'][key]=dict(bindings['children'][key],provider_reference='nonempty exported claim')
        with self.assertRaisesRegex(ValueError,'resolve actual source journal'):
            m.verify_shared_journal_source(bindings,self.control,self.inventory,self.source)

    def test_valid_other_sector_pair_does_not_resolve_this_typed_offset(self):
        bindings=dict(self.bindings,children=dict(self.bindings['children']))
        keys=[k for k,v in bindings['children'].items() if v['kind']=='shared64']
        bindings['children'][keys[0]]=dict(bindings['children'][keys[0]],sector_children=bindings['children'][keys[1]]['sector_children'])
        with self.assertRaisesRegex(ValueError,'typed offset'):
            m.verify_shared_journal_source(bindings,self.control,self.inventory,self.source)

    def test_reference_must_resolve_retained_code_index_not_only_opcode_counts(self):
        control=dict(self.control,control_movement_calls=list(self.control['control_movement_calls']))
        first=control['control_movement_calls'][0]
        control['control_movement_calls'][0]=dict(first,source_reference=dict(first['source_reference'],code_index=99999))
        with self.assertRaisesRegex(ValueError,'instruction index'):
            m.verify_shared_journal_source(self.bindings,control,self.inventory,self.source)


if __name__ == '__main__':
    unittest.main()
