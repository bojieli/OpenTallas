import copy
import ast
import hashlib
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import h4_c0_source_operand_views_r1 as a


class SourceViewsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = a.OperandViews(enabled=True)

    def packet(self, start=0):
        return self.adapter.bind(35, start, generation=3, owner_tag=7, response_stall_bound=11)

    def test_default_off(self):
        with self.assertRaisesRegex(ValueError, 'default off'):
            a.OperandViews().bind(35, 0, generation=1, owner_tag=1, response_stall_bound=1)

    def test_exact_native_leaf_and_dtype(self):
        c = self.packet()['native_command']
        self.assertEqual((c['template_id'], c['ordered_step_index'], c['opcode']), ('add',0,'FADD'))
        self.assertEqual(c['source_bittypes'], [32,32])
        self.assertEqual(c['source_attrs_rounding'], {})
        self.assertEqual(c['destination_bittype'], 32)

    def test_actual_first_homes(self):
        p = self.packet()
        self.assertEqual([v['RFslot9'] for v in p['native_command']['source_version_home_refs']], [34,38])
        self.assertEqual([(v['storage_rank'],v['storage_SM'],v['RFslot9']) for v in p['source_output_replicas']],
                         [(0,0,36),(1,0,36)])

    def test_worker_not_storage_SM(self):
        p = self.packet(256)
        self.assertEqual((p['native_command']['rank'],p['native_command']['SM']), (0,0))
        self.assertEqual([v['storage_SM'] for v in p['native_command']['source_version_home_refs']], [1,1])

    def test_second_tile_exact_lanes(self):
        p = self.packet(128)
        self.assertEqual([v['RFslot9'] for v in p['native_command']['source_version_home_refs']], [35,39])
        self.assertEqual(p['source_output_replicas'][0]['lanes'], list(range(128)))

    def test_no_fabricated_HBM_address_or_ticket(self):
        p = self.packet()
        for v in p['native_command']['source_version_home_refs'] + p['source_output_replicas']:
            self.assertIsNone(v['HBM_byte_address'])
            self.assertIsNone(v['parent55'])
            self.assertIn('NOT_APPLICABLE_DIRECT_RF', v['parent55_scope'])

    def test_partial_tile_rejected(self):
        for start in (-128, 1, 4096, True):
            with self.subTest(start=start), self.assertRaises(ValueError):
                self.packet(start)

    def test_unenrolled_recipe_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not enrolled'):
            self.adapter.bind(2, 0, generation=1, owner_tag=1, response_stall_bound=1)

    def test_owner_and_bound_required(self):
        for key, value in [('generation',0),('owner_tag',0),('response_stall_bound',0),('generation',True)]:
            args=dict(generation=1,owner_tag=1,response_stall_bound=1);args[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.adapter.bind(35,0,**args)

    def test_home_version_and_consumer_bounds(self):
        with self.assertRaisesRegex(ValueError, 'producer/consumer'):
            self.adapter.view('Qwen.34.L0.o.44',0,128,0,'read',36)

    def test_source_step_tamper_rejected(self):
        p=self.packet();p['source_step']['op']='FMUL'
        with self.assertRaisesRegex(ValueError,'identity changed'):
            a.price(p)

    def test_dtype_shape_only_not_accepted(self):
        p=self.packet();p['native_command']['source_bittypes']=[64,64]
        with self.assertRaisesRegex(ValueError,'identity changed'):
            a.price(p)

    def test_missing_output_replica_rejected(self):
        p=self.packet();p['source_output_replicas'].pop()
        with self.assertRaisesRegex(ValueError,'identity changed'):
            a.price(p)

    def test_price_staging_and_mirrors_once(self):
        p=a.price(self.packet())
        self.assertEqual(p['service_counts'],dict(RF_READ=3,RF_MIRRORED_ACK=5,FADD=1,NoC_PAGE=1,CDC=2,REVERSE_GRANT=7))
        self.assertEqual(p['physical_mirror_write_bits'],40960)
        self.assertEqual(p['NoC_payload_bits'],4096)
        self.assertIsNone(p['latency_ns'])

    def test_positive_costs_and_no_zero_remote(self):
        costs={k:1 for k in a.COSTS}
        self.assertEqual(a.price(self.packet(),costs)['latency_ns'],19)
        costs['NoC_PAGE']=0
        with self.assertRaisesRegex(ValueError,'finite positive'):
            a.price(self.packet(),costs)

    def test_source_owned_dispatch_and_no_alias(self):
        d=a.DirectRFDispatch(enabled=True);p=d.propose(35,0,generation=1,response_stall_bound=1)
        self.assertEqual(p['workspace_slots'],dict(a=17,b=18,out=19))
        self.assertEqual(p['binding']['client'],0)
        self.assertEqual(p['native_command']['source_bittypes'],[32,32])
        self.assertEqual([v['RF_vectors'] for v in p['native_command']['source_version_home_refs']],[[17],[18]])
        self.assertEqual(p['native_command']['destination_version_home_ref']['RF_vectors'],[19])
        self.assertEqual([x['action'] for x in p['ordered_actions']],
                         ['read_home_into_workspace','read_home_into_workspace','native_leaf',
                          'copy_output_to_source_home','copy_output_to_source_home'])
        with self.assertRaisesRegex(ValueError,'one outstanding'):
            d.propose(35,128,generation=1,response_stall_bound=1)

    def test_original_owner_home_validator_on_prospective_views(self):
        tree=ast.parse(a.sources()['owner_guard.py'])
        cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='AtomicV1Owners')
        method=copy.deepcopy(next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='validate_home'))
        method.decorator_list=[]
        env={'AdmissionError':ValueError}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'original-validate-home','exec'),env)
        p=a.DirectRFDispatch(enabled=True).propose(35,0,generation=1,response_stall_bound=1)
        c=p['native_command'];b=dict(physical_RF_id='prospective.Qwen.rank0.SM0.RF')
        for home in c['source_version_home_refs']+[c['destination_version_home_ref']]:
            env['validate_home'](home,c,b,32)
        # This validates port metadata, and does not bypass PhysicalBindings.
        bad=copy.deepcopy(c['source_version_home_refs'][0]);bad['SM']=1
        with self.assertRaises(ValueError):env['validate_home'](bad,c,b,32)

    def test_original_Popper_guard_rejects_prospective_binding(self):
        tree=ast.parse(a.sources()['popper_emitter.py'])
        selected=[x for x in tree.body if (isinstance(x,ast.ClassDef) and x.name=='NativeCompiler')
                  or (isinstance(x,ast.FunctionDef) and x.name in ('need','uint'))
                  or (isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('REQUIRED','ALIASES') for t in x.targets))]
        native=self.adapter.native
        descriptions=[dict(family=o['opcode'],leaves={k:native['microcode'][k] for k,n in
                      o['calendar_export']['physical_primitives']['kernel_invocations'].items()
                      if n and k in native['microcode']}) for o in native['operations']]
        env=dict(ast=ast,copy=copy,inputs=a.sources,
                 catalog=lambda:dict(Qwen=dict(hash=a.sha(a.sources()['Qwen_tiled.json.gz']),PCs=1737,ops=descriptions)))
        exec(compile(ast.Module(body=selected,type_ignores=[]),'unchanged-Popper-compiler','exec'),env)
        p=self.adapter.bind_eligible(40,0,generation=1,owner_tag=1,response_stall_bound=1)
        binding=dict(model='Qwen',rank=0,SM=0,die=0,physical_RF_id='prospective.Qwen.rank0.SM0.RF',
                     scope='prospective_source',operand_view_scope='source_derived_direct_RF')
        # die0 here is a negative-test fixture, not an actual source assignment.
        with self.assertRaisesRegex(ValueError,'production native SSA'):
            env['NativeCompiler']().compile(p['native_command'],{},binding,0)

    def test_actual_eligible_C0_FMAX_source_call(self):
        p=self.adapter.bind_eligible(40,0,generation=1,owner_tag=1,response_stall_bound=1)
        c=p['native_command']
        self.assertEqual((c['source_PC'],c['family'],c['template_id'],c['ordered_step_index'],c['opcode']),
                         (40,'SILU_GATE','exp',0,'FMAX'))
        self.assertEqual(c['source_bittypes'],[32,32])
        self.assertEqual(c['destination_bittype'],32)
        self.assertEqual(c['source_attrs_rounding'],{})
        self.assertEqual(p['source_gate_home']['version'],'Qwen.39.L0.d0.gu_post.49')
        self.assertEqual(p['source_gate_home']['RFslot9'],38)
        constant=c['source_version_home_refs'][1]
        self.assertEqual(constant['source_producer']['literal_bits_U32'],0xc2ae0000)
        self.assertEqual(constant['source_producer']['broadcast_words'],128)
        self.assertEqual(c['source_version_home_refs'][0]['source_producer']['source_step'],
                         dict(dst='out',op='NEG',src=['x']))
        self.assertEqual(a.price_eligible(p)['service_counts']['FMAX'],1)

    def test_eligible_negative_width_home_lease_opcode(self):
        for name in ('width','home','lease','opcode'):
            p=self.adapter.bind_eligible(40,0,generation=1,owner_tag=1,response_stall_bound=1)
            c=p['native_command']
            if name=='width':c['source_bittypes'][0]=64
            elif name=='home':c['source_version_home_refs'][0]['RF_vectors']=[31]
            elif name=='lease':c['source_version_home_refs'][0]['lease']='other-generation'
            else:c['opcode']='FMIN'
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'identity changed'):
                a.price_eligible(p)

    def test_retire_requires_source_receipts(self):
        d=a.DirectRFDispatch(enabled=True);p=d.propose(35,0,generation=1,response_stall_bound=1)
        receipt=dict(scope='source_provider_software',native_owner=p['native_owner'],all_consumers_done=True,
                     all_reverse_grants_accepted=True,mirrored_write_ACKs=[])
        with self.assertRaisesRegex(ValueError,'mirror ACKs'):
            d.release(p,provider_reverse_receipt=receipt)
        receipt['mirrored_write_ACKs']=[[v['source_provider_ref'],v['lease'],v['RFslot9'],2]
                                      for v in p['source_output_replicas']]
        d.release(p,provider_reverse_receipt=receipt)
        q=d.propose(35,128,generation=1,response_stall_bound=1)
        self.assertEqual(q['native_command']['owner_tag'],2)

    def test_no_hardware_OR_original_guard_admission(self):
        p=self.packet()
        self.assertFalse(p['hardware_admitted'])
        self.assertFalse(p['original_Popper_compile_admitted'])
        self.assertFalse(p['payload_compared'])

    def test_complete_family_and_all_source_PCs_accounted(self):
        m=a.compose_context();c=m['coverage']
        self.assertEqual(len(c['enrolled_PCs']),72)
        self.assertEqual(c['enrolled_calls'],2304)
        self.assertEqual(c['remaining_PCs'],1665)
        self.assertEqual(sum(m['home_view_counts'].values()),4*2304)
        self.assertEqual(m['service_counts']['FADD'],2304)

    def test_frozen_cold_model(self):
        self.assertEqual(a.canonical(a.compose()), (a.BASE/'model_r1.json').read_bytes())


if __name__=='__main__':
    unittest.main()
