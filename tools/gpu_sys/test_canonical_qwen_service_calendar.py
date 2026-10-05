"""Source calendar/cost gates only; no numerical prefix, provider or RTL run."""
from collections import Counter
from fractions import Fraction
import unittest
from tools.gpu_sys import canonical_qwen_service_calendar as C


class CalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native=C.read(C.ROOT/C.PROGRAM)
        cls.source=(C.ROOT/C.SOURCE).read_bytes()
        cls.kv=C.read(C.BASE/'inputs/kv_commit_model.json')
        cls.model=C.compose(cls.native,8191,cls.kv,raw_source=cls.source)

    def test_complete_current_original_not_legacy_native_alias(self):
        self.assertEqual(self.model['program_sha256'],C.PROGRAM_SHA)
        self.assertEqual([r['pc'] for r in self.model['operations']],list(range(1737)))
        self.assertEqual(self.model['original_runtime'],'870c5fe581b768df28dd2998b2d0aecc24510c23')
        self.assertEqual(sum(self.model['native_service_demands'].values()),269956823)

    def test_missing_cost_is_unknown_not_zero_token_or_start(self):
        self.assertIsNone(self.model['total']['duration_ps'])
        self.assertIsNone(self.model['conditional_source_calendar_ps'])
        self.assertIsNone(self.model['operations'][0]['start_ps'])
        self.assertIsNone(self.model['operations'][-1]['end_ps'])
        self.assertIn('native/FADD/bits32/W4_write_ACK',self.model['total']['unresolved'])
        self.assertIn('native/FADD/bits32/W6_result_capture',self.model['total']['unresolved'])
        self.assertIn('native/FADD/bits32/forward_route_CDC',self.model['total']['unresolved'])

    def test_commit_source_floor_once_at_fence_not_arithmetic_writer(self):
        writer=self.model['operations'][10];fence=self.model['operations'][11]
        self.assertNotIn('kv_commit',writer['kv_RPCs'])
        self.assertEqual(fence['kv_RPCs']['kv_commit'],1)
        self.assertEqual(writer['kv_RPCs']['kv_stage_write/64'],16)
        self.assertTrue(writer['native_units'])
        self.assertEqual(Fraction(self.model['total']['known_constraints_floor_ps']),668340000)
        self.assertEqual(self.model['KV_RPC_demands']['kv_commit'],72)
        self.assertTrue(self.model['W2']['commit_floor_already_contains_II'])

    def test_per_byte_state_reads_not_bulk_or_cached_prefix(self):
        self.assertEqual(self.model['KV_state_RPC_reads'],609288552)
        self.assertEqual(self.model['KV_state_RPC_writes'],432)
        self.assertEqual(self.model['KV_RPC_demands']['kv_payload_read/128'],4718592)
        p=self.native['source_program']
        for pos in (0,8191):
            counts=Counter()
            for name in ('KV_WRITE','KV_FENCE','KV_READ','SCORES','PV'):
                counts.update(C.kv_demand(name,p,pos))
            self.assertEqual(counts['kv_state_read/1']+counts['kv_state_read/16'],1033*(pos+1)+5)

    def test_consumer_and_drain_fulloperator_not_per_primitive(self):
        self.assertEqual(self.model['KV_RPC_demands']['kv_consumer_done'],144)
        self.assertEqual(self.model['KV_RPC_demands']['kv_reader_release'],72)
        self.assertNotIn('W6',self.model['native_service_demands'])
        self.assertFalse(self.model['physical_qualified'])
        self.assertIsNone(self.model['single_user_tokens_s'])

    def test_same_client_II_is_max_not_added_RTT(self):
        def request(pc=0,client=1):
            return dict(physical_PC=pc,client=client,offer_edge=0,request_edges=8,
                        backend_edges=1,capture_edges=8,reverse_edges=1)
        rows=C.same_client_calendar([request(),request()])
        self.assertEqual([r['accept_edge'] for r in rows],[8,27])
        self.assertEqual(rows[0]['reverse_edge'],18)
        rows=C.same_client_calendar([request(),dict(request(),depends_on=[0])])
        self.assertEqual(rows[1]['accept_edge'],27)
        rows=C.same_client_calendar([request(),request(client=2),request(pc=1)])
        self.assertEqual([r['accept_edge'] for r in rows],[8,18,8])

    def test_same_client_contract_and_unmapped_route_refused(self):
        with self.assertRaises(ValueError):C.same_client_calendar([],same_client_II=8)
        with self.assertRaises(ValueError):C.same_client_calendar([dict(physical_PC=128,client=1)])

    def test_native_zero_or_clock_relaxation_refused(self):
        key='native/FADD/bits32/launch'
        row=dict(edges=0,domain='streaming',source='test',scope='conditional')
        with self.assertRaises(ValueError):C.Prices(dict(services={key:row})).duration(key)
        row.update(edges=1,period_ps='1000')
        with self.assertRaises(ValueError):C.Prices(dict(services={key:row})).duration(key)

    def test_same_clock_zero_needs_explicit_pinned_proof(self):
        key='native/FADD/bits32/forward_route_CDC'
        row=dict(edges=0,domain='streaming',same_clock_source_sha256='a'*64)
        with self.assertRaises(ValueError):C.Prices(dict(services={key:row})).duration(key)
        self.assertEqual(C.Prices(dict(services={key:row},verified_same_clock_source_sha256=['a'*64])).duration(key),0)

    def test_native_lowering_retains_three_NEG_steps_and64bit_words(self):
        node=self.model['native_recipes']['neg']
        self.assertEqual(node['ABI']['steps'][0]['native_steps'],['BITCAST_U','XOR','BITCAST_F'])
        units=self.model['native_service_demands']
        self.assertIn('F2I/bits64',units)
        self.assertIn('IADD/bits64',units)
        self.assertIn('SHL/bits64',units)

    def test_positive_partial_price_does_not_close_remaining_unknowns(self):
        profile=dict(services={'PC_launch':dict(edges=2,domain='streaming',source='explicit-test',scope='conditional')})
        interval=C.Interval();prices=C.Prices(profile)
        interval.charge('PC_launch',3,prices);interval.charge('unknown_ACK',1,prices)
        self.assertEqual(interval.priced,6*C.FAST)
        self.assertIsNone(interval.record()['duration_ps'])
        self.assertEqual(interval.record()['unresolved'],{'unknown_ACK':1})

    def test_source_commit_minimum_cannot_be_erased_or_doubled(self):
        floor=Fraction(self.kv['scenarios']['zero_external_protocol_floor']['exposed_commit_ps'])
        edges=int(floor/C.FAST)
        price=dict(edges=edges,domain='streaming',source='Peirce-local-floor',scope='source_minimum')
        interval=C.Interval();interval.charge('kv_commit',72,C.Prices(dict(services={'kv_commit':price})),minimum_ps=floor)
        self.assertEqual(interval.priced,72*floor)
        self.assertEqual(interval.floor,72*floor)
        price['edges']=1
        with self.assertRaises(ValueError):C.Interval().charge('kv_commit',1,C.Prices(dict(services={'kv_commit':price})),minimum_ps=floor)

    def test_source_metadata_pin_refused_before_AST_execution(self):
        with self.assertRaises(ValueError):C.counting_functions(self.source+b'\n')

    def test_actual_measured_W2_runtime_pin_and_request_series(self):
        raw=(C.ROOT/'results/rtl/w2_fullnc6_functional_20261003/r7_reset_quarantine_pass/runtime.log').read_bytes()
        self.assertEqual(len(C.verify_W2_runtime(raw,self.kv)),16)
        with self.assertRaises(ValueError):C.verify_W2_runtime(raw+b'\n',self.kv)

    def test_all_positive_calibration_produces_conditional_calendar_only(self):
        services={key:dict(edges=1,domain='streaming',source='synthetic-test-calibration',scope='conditional')
                  for key in self.model['calibration']['required_services']}
        floor=Fraction(self.kv['scenarios']['zero_external_protocol_floor']['exposed_commit_ps'])
        services['kv_commit']['edges']=int(floor/C.FAST)
        closed=C.compose(self.native,8191,self.kv,dict(services=services),raw_source=self.source)
        self.assertFalse(closed['total']['unresolved'])
        self.assertIsNotNone(closed['conditional_source_calendar_ps'])
        self.assertEqual(closed['operations'][-1]['end_ps'],closed['conditional_source_calendar_ps'])
        self.assertIsNone(closed['actual_token_latency_ps'])
        self.assertIsNone(closed['single_user_tokens_s'])
        self.assertFalse(closed['physical_qualified'])

    def test_serialPC_retirement_precedes_next_launch(self):
        for pc,row in enumerate(self.model['operations'][1:],1):
            self.assertIn(pc-1,row['depends_on'])
            self.assertIn(f'PC{pc}/source_retirement',row['calendar']['unresolved'])
            self.assertIn(f'PC{pc}/fixed_LOOP_tile_control',row['calendar']['unresolved'])

if __name__=='__main__':unittest.main()
