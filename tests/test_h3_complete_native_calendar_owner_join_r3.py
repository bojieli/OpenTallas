import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('owner_join_r3_tests', ROOT/'tools/h3_complete_native_calendar_owner_join_r3.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class OwnerJoinTests(unittest.TestCase):
    def setUp(self):
        self.join = m.ProductionOwnerJoin()
        self.command = next(c for c in self.join.commands.values() if c['kind'] == 'RF_partial_RMW')
        self.key = dict(die=self.command['die'], SM=self.command['SM'])
        self.receipt = self.join.receipt(self.command['id'], lease=51)
        self.join.submit(self.command['id'], receipt=self.receipt)
        self.token = self.join.admit_next(**self.key, edge=0, origin='directed_verifier_control',drain_pins=m.directed_idle_pins(self.join.atomic))
        self.edge = 1
    def ev(self, desc, name, **kw):
        x = self.join.live[self.key['die'], self.key['SM']]
        event = self.join._event(x['parent'], name, edge=self.edge, origin=x['origin'], child=desc['child'], **kw)
        self.join.observe_SRAM(**self.key, token=self.token, completion_token=desc['completion_token'], event=event)
    def ACK(self, *, read_data=None, reverse=True, ready=True, payload=None):
        desc = self.join.issue(**self.key, token=self.token, edge=self.edge, payload=payload)
        for i, bank in enumerate(desc['expected_SRAMs']):
            kw = dict(SRAM=bank, write=desc['write'])
            if desc['write']:
                offset=bank[1]*32
                kw['data']=desc['payload'][offset:offset+32]
            self.ev(desc,'SRAM_accept',**kw)
        self.edge += 1
        if not desc['write']:
            for i, bank in enumerate(desc['expected_SRAMs']):
                self.ev(desc,'SRAM_capture',SRAM=bank,data=read_data[i*32:(i+1)*32])
            self.edge += 1
        self.ev(desc,'child_ACK',valid=True,ready=True)
        self.join.capture_completion(**self.key, token=self.token, completion_token=desc['completion_token'],
                                     payload=None if desc['write'] else read_data)
        self.edge += 1
        self.join.consume_completion(**self.key,token=self.token,ready=ready)
        if reverse:
            self.join.reverse_child(**self.key,token=self.token,completion_token=desc['completion_token'],edge=self.edge)
            self.edge+=1
        return desc
    def finish(self):
        self.join.visibility(**self.key,token=self.token,edge=self.edge);self.edge+=1
        self.join.consumer(**self.key,token=self.token,edge=self.edge);self.edge+=1
        self.join.reverse(**self.key,token=self.token,edge=self.edge,CDC_receipt=dict(token=self.token,
                          sender_domain='CORE',sender_edge=17,receiver_domain='H1_streaming',receiver_edge=self.edge),drain_pins=m.directed_idle_pins(self.join.atomic))
        self.edge+=1
    def test_actual_owner_RMW_opaque_tail_exact_common_ACK_and_retirement(self):
        old = bytes(range(256))*2
        self.ACK(read_data=old*2)
        prefix = bytes([0x81,0,0xFF,0x7F])*self.command['active_words']
        merged = self.join.merge(**self.key,token=self.token,payload=prefix)
        self.assertEqual(merged,prefix+old[len(prefix):])
        self.ACK()
        self.ACK(read_data=merged*2)
        self.finish()
        self.assertEqual(self.join.endpoint.completed,{self.command['id']})
        self.assertEqual(self.join.summary()['live_SM_owners'],0)
        self.assertEqual(self.join.ledger.summary()['physical_credit_debt'],0)
    def test_completion_capture_independent_of_consumer_ready(self):
        old = bytes(1024)
        desc = self.ACK(read_data=old,reverse=False,ready=False)
        self.assertEqual(self.join.summary()['held_completions'],1)
        self.assertEqual(self.join.endpoint.live[0,0]['phase'],'READ_ACK')
        for _ in range(9): self.assertIsNone(self.join.consume_completion(**self.key,token=self.token,ready=False))
        with self.assertRaises(ValueError): self.join.issue(**self.key,token=self.token,edge=self.edge)
        with self.assertRaises(ValueError): self.join.reverse_child(**self.key,token=self.token,completion_token=desc['completion_token'],edge=self.edge)
        self.join.consume_completion(**self.key,token=self.token,ready=True)
        self.join.reverse_child(**self.key,token=self.token,completion_token=desc['completion_token'],edge=self.edge)
        self.assertEqual(self.join.endpoint.live[0,0]['phase'],'MERGE')
        self.assertEqual(self.join.summary()['live_SM_owners'],1)
    def test_wrong_parent_and_stale_prior_child_completions_reject(self):
        first=self.ACK(read_data=bytes(1024))
        self.join.merge(**self.key,token=self.token,payload=bytes(self.command['active_words']*4))
        second=self.join.issue(**self.key,token=self.token,edge=self.edge)
        with self.assertRaisesRegex(ValueError,'wrong-owner|stale'):
            self.join.capture_completion(**self.key,token=self.token,completion_token=first['completion_token'])
        with self.assertRaisesRegex(ValueError,'wrong or stale'):
            self.join.capture_completion(**self.key,token='0'*64,completion_token=second['completion_token'])
        self.assertEqual(self.join.summary()['live_SM_owners'],1)
        self.assertEqual(self.join.endpoint.live[0,0]['phase'],'WRITE_ACK')
    def test_ACK_without_all_banks_and_token_only_cannot_capture(self):
        desc=self.join.issue(**self.key,token=self.token,edge=self.edge)
        with self.assertRaisesRegex(ValueError,'resolved common'):
            self.join.capture_completion(**self.key,token=self.token,completion_token=desc['completion_token'],payload=bytes(1024))
        for bank in desc['expected_SRAMs'][:-1]:self.ev(desc,'SRAM_accept',SRAM=bank,write=False)
        self.edge+=2
        with self.assertRaisesRegex(ValueError,'all SRAM'):self.ev(desc,'child_ACK',valid=True,ready=True)
    def test_mismatched_word_capture_payload_and_old_mirrors_reject(self):
        # The retained Popper endpoint refuses unequal old copies even if every
        # individual SRAM capture is real and the transport token matches.
        with self.assertRaisesRegex(ValueError,'identical old mirror tails'):
            self.ACK(read_data=bytes(512)+bytes([1])*512,reverse=False)
        self.assertEqual(self.join.summary()['held_completions'],1)
        with self.assertRaises(ValueError):self.join.visibility(**self.key,token=self.token,edge=self.edge)
    def test_same_SM_contender_waits_through_consumer_and_reverse(self):
        nextc=next(c for c in self.join.commands.values() if c['kind']=='RF_partial_RMW' and c['die']==0 and c['SM']==0 and c['id']!=self.command['id'])
        self.join.submit(nextc['id'],receipt=self.join.receipt(nextc['id'],lease=52))
        self.assertIsNone(self.join.admit_next(**self.key,edge=self.edge,origin='directed_verifier_control',drain_pins=m.directed_idle_pins(self.join.atomic)))
        self.ACK(read_data=bytes(1024)); self.join.merge(**self.key,token=self.token,payload=bytes(self.command['active_words']*4));self.ACK();self.ACK(read_data=bytes(1024))
        self.join.visibility(**self.key,token=self.token,edge=self.edge);self.edge+=1
        self.join.consumer(**self.key,token=self.token,edge=self.edge);self.edge+=1
        self.assertIsNone(self.join.admit_next(**self.key,edge=self.edge,origin='directed_verifier_control',drain_pins=m.directed_idle_pins(self.join.atomic)))
        self.join.reverse(**self.key,token=self.token,edge=self.edge,CDC_receipt=dict(token=self.token,sender_domain='CORE',sender_edge=100,receiver_domain='H1_streaming',receiver_edge=self.edge),drain_pins=m.directed_idle_pins(self.join.atomic));self.edge+=1
        token2=self.join.admit_next(**self.key,edge=self.edge,origin='directed_verifier_control',drain_pins=m.directed_idle_pins(self.join.atomic))
        self.assertIsNotNone(token2)
        with self.assertRaises(ValueError): self.join.issue(**self.key,token=self.token,edge=self.edge)
    def test_lease_ref_generation_and_source_command_receipt_negative(self):
        c=next(c for c in self.join.commands.values() if c['kind']=='RF_partial_RMW' and c['die']==1)
        receipt=self.join.receipt(c['id'],lease=77)
        for field,value in [('generation',2),('lease',0),('source_lease','foreign'),('provider_reference',999),('outer_owner',[]),('command_sha256','0'*64)]:
            bad=copy.deepcopy(receipt);bad[field]=value
            with self.assertRaisesRegex(ValueError,'entering source'):self.join.submit(c['id'],receipt=bad)
        self.assertNotIn((1,c['SM']),self.join.live)
        with self.assertRaisesRegex(ValueError,'duplicate'):self.join.submit(self.command['id'],receipt=self.receipt)
    def test_cross_rank_completion_token_cannot_consume_other_owner(self):
        c=next(c for c in self.join.commands.values() if c['kind']=='RF_partial_RMW' and c['die']==1)
        self.join.submit(c['id'],receipt=self.join.receipt(c['id'],lease=51))
        token=self.join.admit_next(die=1,SM=c['SM'],edge=0,origin='directed_verifier_control',drain_pins=m.directed_idle_pins(self.join.atomic))
        desc=self.join.issue(die=1,SM=c['SM'],token=token,edge=1)
        with self.assertRaises(ValueError):self.join.capture_completion(**self.key,token=self.token,completion_token=desc['completion_token'])
        self.assertEqual(self.join.summary()['live_SM_owners'],2)

    def test_duplicate_completion_pulse_cannot_overwrite_held_payload(self):
        desc=self.ACK(read_data=bytes(1024),ready=False,reverse=False)
        before=copy.deepcopy(self.join.live[0,0]['held'])
        with self.assertRaisesRegex(ValueError,'capture seat'):
            self.join.capture_completion(**self.key,token=self.token,completion_token=desc['completion_token'],payload=bytes([1])*1024)
        self.assertEqual(self.join.live[0,0]['held'],before)
    def test_wrong_source_write_bytes_not_accepted_by_bank(self):
        self.ACK(read_data=bytes(1024))
        self.join.merge(**self.key,token=self.token,payload=bytes(self.command['active_words']*4))
        desc=self.join.issue(**self.key,token=self.token,edge=self.edge)
        with self.assertRaisesRegex(ValueError,'source write/merge'):
            self.ev(desc,'SRAM_accept',SRAM=desc['expected_SRAMs'][0],write=True,data=bytes([1])*32)
        self.assertFalse(self.join.ledger.live[self.command['id']]['child']['accepts'])
    def test_foreign_completion_payload_not_in_captured_SRAM_receipts(self):
        desc=self.join.issue(**self.key,token=self.token,edge=self.edge)
        for bank in desc['expected_SRAMs']:self.ev(desc,'SRAM_accept',SRAM=bank,write=False)
        self.edge+=1
        for bank in desc['expected_SRAMs']:self.ev(desc,'SRAM_capture',SRAM=bank,data=bytes(32))
        self.edge+=1;self.ev(desc,'child_ACK',valid=True,ready=True)
        with self.assertRaisesRegex(ValueError,'equal all exact source'):
            self.join.capture_completion(**self.key,token=self.token,completion_token=desc['completion_token'],payload=bytes([1])*1024)
        self.assertIsNone(self.join.live[0,0]['held'])
    def test_no_missing_pin_or_held_ACK_implicit_admission(self):
        c=next(c for c in self.join.commands.values() if c['kind']=='RF_partial_RMW' and c['die']==1)
        self.join.submit(c['id'],receipt=self.join.receipt(c['id'],lease=52))
        key=dict(die=1,SM=c['SM'],edge=0,origin='directed_verifier_control')
        self.assertIsNone(self.join.admit_next(**key))
        pins=m.directed_idle_pins(self.join.atomic);pins['host_ack_valid']=True
        self.assertIsNone(self.join.admit_next(**key,drain_pins=pins))
        self.assertNotIn((1,c['SM']),self.join.endpoint.live)
        pins['host_ack_valid']=False
        self.assertIsNotNone(self.join.admit_next(**key,drain_pins=pins))

    def test_retained_owner_class_inspection_and_canonical_modules_unchanged(self):
        import inspect
        import sys
        import hashlib
        before={name:sys.modules.get(name) for name in ('h4_hbm_selected_cache_rmw','h4_hbm_atomic_source_g0','h3_complete_native_calendar_grants_r1')}
        other=m.ProductionOwnerJoin()
        text=inspect.getsource(type(other.endpoint))
        self.assertIn('class SelectedEndpoint:',text)
        self.assertIn('parent_reverse_lease_grant',text)
        self.assertEqual(hashlib.sha256(Path(inspect.getfile(type(other.endpoint))).read_bytes()).hexdigest(),m.PINS['tools/h4_hbm_selected_cache_rmw.py'])
        self.assertEqual(before,{name:sys.modules.get(name) for name in before})

    def test_complete_emitted_command_replay_through_real_Popper_owner(self):
        result,tape=m.run_control()
        self.assertEqual(result['Popper_completed_commands'],9504)
        self.assertEqual(result['events']['completion_backpressured'],10080)
        self.assertEqual(result['SRAM_ledger']['events']['SRAM_accept'],46080)
        self.assertEqual(result['events']['parent_reverse'],352)
        self.assertTrue(result['all_selected_commands_replayed'])
        self.assertFalse(result['hardware_qualified'])
        self.assertEqual(len(tape),sum(result['SRAM_ledger']['events'].values()))

class CostAndCompositionTests(unittest.TestCase):
    def setUp(self):
        self.nodes=[dict(id='node0',phase='ACK',PC=0)]
        self.geometry='literal32B'
        self.kw=dict(program_sha256='a'*64,positive_terms={},retained_intervals={},reuse_bindings={},geometry=self.geometry)
    def test_unknown_never_paid_by_numeric_zero(self):
        result=m.reconcile_event_costs(self.nodes,**self.kw)
        self.assertIsNone(result['complete_incremental_edges_by_domain'])
        self.assertEqual(result['missing_by_phase'],{'ACK':1})
        term=dict(cycles=0,clock_domain='H1',evidence_kind='explicit_provisional_parameter',source_sha256='b'*64,geometry=self.geometry)
        with self.assertRaises(ValueError):m.reconcile_event_costs(self.nodes,**dict(self.kw,positive_terms={'ACK':term}))
        term['cycles']=2
        result=m.reconcile_event_costs(self.nodes,**dict(self.kw,positive_terms={'ACK':term}))
        self.assertEqual(result['incremental_known_edges_by_domain'],{'H1':2})
        term['geometry']='wide750Bslot'
        with self.assertRaises(ValueError):m.reconcile_event_costs(self.nodes,**dict(self.kw,positive_terms={'ACK':term}))
    def test_exact_paid_interval_reuse_once_and_wrong_instruction_rejected(self):
        event=dict(source_node_sha256=m.sha(m.canonical(self.nodes[0])),phase='ACK',cycles=2,clock_domain='H1')
        interval=dict(program_sha256='a'*64,geometry=self.geometry,source_sha256='b'*64,paid_events={'e0':event})
        bind=dict(interval_id='paid0',interval_sha256=m.sha(m.canonical(interval)),event_key='e0')
        kw=dict(self.kw,retained_intervals={'paid0':interval},reuse_bindings={'node0':bind})
        result=m.reconcile_event_costs(self.nodes,**kw)
        self.assertEqual(result['reused_paid_events'],{'ACK':1});self.assertEqual(result['incremental_known_edges_by_domain'],{})
        bad=copy.deepcopy(self.nodes);bad[0]['PC']=1
        with self.assertRaisesRegex(ValueError,'instruction'):m.reconcile_event_costs(bad,**kw)
        other=dict(self.nodes[0],id='node1')
        with self.assertRaises(ValueError):m.reconcile_event_costs(self.nodes+[other],**dict(kw,reuse_bindings={'node0':bind,'node1':bind}))
    def test_native_recipe_frontier_not_generic_one_event_cost(self):
        node=dict(self.nodes[0],phase='existing_native_calendar_frontier')
        term=dict(cycles=2,clock_domain='H1',evidence_kind='explicit_provisional_parameter',source_sha256='b'*64,geometry=self.geometry)
        with self.assertRaisesRegex(ValueError,'native recipe'):m.reconcile_event_costs([node],**dict(self.kw,positive_terms={node['phase']:term}))
    def test_current_metadata_source_order_counts_and_old_graph_unadopted(self):
        import gzip,json
        plan=json.loads(gzip.decompress((ROOT/m.OUT/'inputs/KV_current_plan.json.gz').read_bytes()))
        graph=m.compile_current_metadata(plan)
        self.assertEqual(graph['metadata_source_writes'],432)
        self.assertEqual(graph['phase_counts']['RF_both_copy_write'],576)
        self.assertEqual(graph['phase_counts']['RF_common_ACK'],576)
        self.assertEqual(graph['phase_counts']['KV_metadata_reverse'],432)
        self.assertTrue(graph['old_R1_record_before_bitmap_not_adopted'])
        bad=copy.deepcopy(plan);bad['groups'][0]['metadata_writes'][1]['operation']='commit_record'
        with self.assertRaisesRegex(ValueError,'bitmap-before-record'):m.compile_current_metadata(bad)
    def test_DS_boundary_unknown_and_positive_multidomain_parameterization(self):
        import json
        snap=json.loads((ROOT/m.OUT/'inputs/DS_chain_boundaries.json').read_bytes())
        model=m.ds_boundary_model(snap)
        self.assertEqual(model['source_boundaries'],329)
        self.assertEqual(model['verified_published_baseline']['tokens_s'],2801.8)
        self.assertIsNone(model['current_complete_service']['conditional_AR_total_us'])
        self.assertGreater(model['one_percent_rate_loss_uniform_cycles_threshold'],11)
        self.assertLess(model['one_percent_rate_loss_uniform_cycles_threshold'],12)
        one=dict(snap,boundaries=snap['boundaries'][:1])
        term=dict(cycles=2,repetitions=3,clock_domain='configured_H1',source_sha256='b'*64,evidence_kind='explicit_provisional_parameter',unit='configured_endpoint_cycles')
        profile={phase:dict(term)for phase in m.BOUNDARY_PHASES}
        profile['CDC_reverse']['clock_domain']='configured_CORE'
        result=m.price_ds_boundaries(one,{one['boundaries'][0]['id']:profile},{'configured_H1':1200000000,'configured_CORE':900000000})
        self.assertGreater(result['conditional_AR_total_us'],one['baseline_exact_T_us'])
        self.assertIsNone(result['production_rate']);self.assertFalse(result['headline_replacement_allowed'])
        profile['backend_wait']['cycles']=0
        with self.assertRaises(ValueError):m.price_ds_boundaries(one,{one['boundaries'][0]['id']:profile},{'configured_H1':1200000000,'configured_CORE':900000000})
    def test_composed_model_corrects_source_audit_without_credit(self):
        model=m.composition_model()
        self.assertFalse(model['RTL_build_allowed'])
        self.assertTrue(model['source_common_ACK']['C0_V1_serialized_time_already_charged_once'])
        self.assertEqual(model['r14_default_off']['owner'],'Claude independent W1')
        self.assertFalse(model['owner_candidate']['selected_hardware_field_spec_complete'])
        self.assertEqual(model['KV_phase_costs_missing'],21)
        self.assertIsNone(model['current_metadata_cost_reconciliation']['complete_incremental_edges_by_domain'])

class ConsumerSpanJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json,gzip
        cls.requirements=json.loads((ROOT/m.OUT/'inputs/Goodall_requirements.json').read_bytes())
        cls.native=json.loads(gzip.decompress((ROOT/'results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz').read_bytes()))
        cls.plan=json.loads(gzip.decompress((ROOT/m.OUT/'inputs/KV_current_plan.json.gz').read_bytes()))
    def join(self,requirements=None,native=None,plan=None,directory=None):
        return m.join_goodall_consumer_spans(requirements or self.requirements,native or self.native,plan or self.plan,
            directory_sha256=directory or self.requirements['directory_sha256'])
    def test_all72_native_chains_and_active_extent(self):
        result=self.join()
        self.assertEqual(result['native_consumer_instructions'],216)
        self.assertEqual(result['decoded_sector32_transactions'],9216)
        self.assertEqual(result['old_K_tail_capture_transactions'],18432)
        first=result['groups'][0]['active_cache_mapping'][0]
        self.assertEqual(first['active_FP32_words'],512)
        self.assertEqual(first['allocated_words'],4194304)
        self.assertEqual(first['active_SMs'],[0,1])
        self.assertEqual(sum(s['sector32_transactions']for s in first['spans']),64)
        self.assertFalse(result['metadata_contract_conflict']['resolved'])
        self.assertFalse(result['representative_gate']['archive_harness_completion_credit'])
    def test_wrong_instruction_version_and_span_rejected(self):
        bad=copy.deepcopy(self.requirements);bad['groups'][0]['source_consumer_chain'][0]['reads'][1]='wrong_version'
        with self.assertRaisesRegex(ValueError,'instruction'):self.join(requirements=bad)
        bad=copy.deepcopy(self.plan);bad['groups'][0]['decoded_sectors'][0]['address']+=32
        with self.assertRaisesRegex(ValueError,'address/ref'):self.join(plan=bad)
    def test_wrong_directory_RF_slot_and_extent_rejected(self):
        with self.assertRaisesRegex(ValueError,'directory'):self.join(directory='0'*64)
        bad=copy.deepcopy(self.plan);bad['groups'][0]['producer_vectors'][0]['RF_slot']=511
        with self.assertRaisesRegex(ValueError,'RF slot'):self.join(plan=bad)
        bad=copy.deepcopy(self.requirements)
        version=bad['groups'][0]['source_consumer_chain'][0]['reads'][1]
        bad['groups'][0]['version_home_inventory'][version]['allocated_words']=512
        with self.assertRaisesRegex(ValueError,'allocated extent'):self.join(requirements=bad)

if __name__=='__main__':unittest.main()
