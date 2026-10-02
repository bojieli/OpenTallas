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
