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
