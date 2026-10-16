"""Compiler negative witnesses; fixtures below qualify the compiler only."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import shutil
import unittest
from compile_calendar import compile_program, schedule_jobs, issuer_done_row, ROOT, PIPELINE_ABI
import vm_service_profile as VSP


class CompileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'native.sv').write_text('// test fixture: no claim of native hardware qualification\n')
        self.evidence = [{'path':'native.sv', 'sha256':hashlib.sha256((self.root/'native.sv').read_bytes()).hexdigest()}]
        self.program = dict(stage='S000', ops=[
            dict(id='field',eng='fld',port=0,start=0,end=11,preds=[]),
            dict(id='su',eng='su',port=1,start=12,end=23,preds=[0])])
        self.contract = dict(stream_period_ps=1,vm_period_ps=1,stream_phase_ps=0,vm_phase_ps=0,
                             banks=32,bank_ops_per_cycle=1,read_ingress_per_cycle=16,write_ingress_per_cycle=16,
                             request_min_ps=1,read_min_ps=1,commit_min_ps=1,
                             slot_capacity={'field/write/0':4,'su/read/0':4},client_capacity={'field':4,'su':4},
                             measured_native_bounds=True, bank_queue_capacity=4)
        def job(eng, kind):
            return dict(engine=eng,implementation='native_rtl',endpoint='test_fixture',client='field' if eng=='fld' else eng,
                        tag=0,duration_cycles=10,phase_period_stream=1,start_phase_stream=0,evidence=self.evidence,
                        accesses=[dict(kind=kind,tensor='q',row_offset=0,slot=0,issue_cycle=1,ingress_cycle=2,
                                       bank_enqueue_cycle=2,service_cycle=3,deadline_cycle=8,
                                       **({'commit_cycle':4} if kind=='write' else {'response_cycle':4}))],
                        vm_pipeline_abi=dict(PIPELINE_ABI['vm']),
                        **({'pipeline_abi':dict(PIPELINE_ABI[eng])} if eng in PIPELINE_ABI else {}))
        self.binding = dict(stage='S000',tensors={'q':dict(base_row=256,nrows=1,source='native_job',producer='field',
                                                        consumers=['su'],evidence=self.evidence)},
                            jobs={'field':job('fld','write'),'su':job('su','read')})

    def tearDown(self):
        self.tmp.cleanup()

    def run_compile(self):
        return compile_program(self.program,self.binding,self.contract,self.root)

    def test_compiler_lowering_and_address_256(self):
        r=self.run_compile()
        self.assertTrue(r['dispatch_eligible'], r)
        self.assertFalse(r['qualified'])
        self.assertEqual([e['row'] for e in r['schedule']['events']],[256,256])
        self.assertEqual(r['schedule']['events'][1]['service_cycle'],15)
        self.assertEqual(len(r['schedule']['dependencies']),1)

    def selected_profile_fixture(self):
        name = 's81_vm_r4_c2_w1'
        manifest = json.loads((VSP.ROOT / VSP.MEASURED_MANIFEST).read_text())
        for path in set(manifest) | set(VSP.PROFILES[name]['receipts']) | {VSP.MEASURED_MANIFEST}:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(VSP.ROOT / path, target)
        self.contract.update(request_min_ps=0, read_min_ps=0, commit_min_ps=0,
            bank_mapping='xor_row7_5_shift2',
            vm_service_profile=dict(name=name, rtl_tuple=VSP.PROFILES[name]['rtl_tuple'],
                                    evidence=VSP.evidence_for(name, self.root)))
        # Nonzero job origins exercise stream raw-cycle rebasing independently
        # from ordinal lane=2. This is compiler evidence, not RTL qualification.
        self.program['ops'][0].update(start=5, end=25)
        self.program['ops'][1].update(start=26, end=50)
        self.binding['jobs']['field']['duration_cycles'] = 19
        self.binding['jobs']['su']['duration_cycles'] = 23
        self.binding['jobs']['field']['accesses'][0].update(
            raw_cycle=13, lane=2, service_cycle=13, commit_cycle=15, deadline_cycle=15)
        self.binding['jobs']['su']['accesses'][0].update(
            raw_cycle=8, service_cycle=8, response_cycle=17, deadline_cycle=17)

    def test_selected_profile_compiles_raw_and_returned_edges(self):
        self.selected_profile_fixture()
        result = self.run_compile()
        self.assertTrue(result['dispatch_eligible'], result)
        write, read = result['schedule']['events']
        self.assertEqual((write['issue_cycle'], write['raw_cycle'], write['commit_cycle'], write['lane']),
                         (6, 18, 20, 2))
        self.assertEqual((read['issue_cycle'], read['raw_cycle'], read['response_cycle']), (27, 34, 43))
        self.assertFalse(result['qualified'])

    def test_selected_profile_missing_raw_edge_blocks_all_dispatch(self):
        self.selected_profile_fixture()
        del self.binding['jobs']['field']['accesses'][0]['raw_cycle']
        result = self.run_compile()
        self.assertFalse(result['dispatch_eligible'])
        self.assertIsNone(result['schedule'])
        self.assertIn('profile_raw_cycle_unbound', [x['kind'] for x in result['reservations']['violations']])

    def test_selected_profile_stale_commit_blocks_all_dispatch(self):
        self.selected_profile_fixture()
        self.binding['jobs']['field']['accesses'][0]['commit_cycle'] -= 1
        result = self.run_compile()
        self.assertFalse(result['dispatch_eligible'])
        self.assertIsNone(result['schedule'])
        self.assertIn('profile_write_returned_commit_edge', [x['kind'] for x in result['reservations']['violations']])

    def test_sparse_tensor_counts_actual_rows_not_reserved_holes(self):
        self.binding['tensors']['q'].update(nrows=80,row_stride=4,reserved_span_rows=320)
        for job in self.binding['jobs'].values():job['accesses'][0]['row_offset']=79
        r=self.run_compile()
        self.assertTrue(r['dispatch_eligible'],r)
        self.assertEqual([e['row'] for e in r['schedule']['events']],[572,572])
        self.assertEqual(len(r['schedule']['dependencies']),1)
    def test_sparse_tensor_capacity_uses_stride(self):
        self.binding['tensors']['q'].update(base_row=16380,nrows=2,row_stride=4)
        r=self.run_compile()
        self.assertFalse(r['dispatch_eligible'])
        self.assertIn('invalid_tensor_binding',[e['kind'] for e in r['rejections']])
    def test_sparse_hole_is_reserved_without_fake_producer_write(self):
        self.binding['tensors']['q'].update(nrows=80,row_stride=4,reserved_span_rows=320)
        self.binding['tensors']['r']=copy.deepcopy(self.binding['tensors']['q'])
        self.binding['tensors']['r'].update(base_row=257,nrows=1,row_stride=1,reserved_span_rows=1)
        r=self.run_compile()
        self.assertFalse(r['dispatch_eligible'])
        self.assertIn('live_tensor_address_alias',[e['kind'] for e in r['rejections']])
    def test_sparse_reserved_bound_cannot_omit_last_live_row(self):
        self.binding['tensors']['q'].update(nrows=80,row_stride=4,reserved_span_rows=80)
        self.assertFalse(self.run_compile()['dispatch_eligible'])
    def test_missing_job_blocks_atomic_dispatch(self):
        del self.binding['jobs']['su']
        r=self.run_compile()
        self.assertFalse(r['dispatch_eligible']); self.assertIsNone(r['schedule'])
        self.assertIn('missing_native_job_binding',[e['kind'] for e in r['rejections']])

    def test_reference_tensor_rejected(self):
        self.binding['tensors']['q']['source']='golden_snapshot'
        r=self.run_compile(); self.assertFalse(r['dispatch_eligible'])
        self.assertIn('invalid_tensor_binding',[e['kind'] for e in r['rejections']])

    def test_no_native_producer_writes(self):
        self.binding['jobs']['field']['accesses']=[]
        r=self.run_compile(); self.assertFalse(r['dispatch_eligible'])
        self.assertIn('unproduced_native_read',[e['kind'] for e in r['rejections']])

    def test_partial_write_does_not_supply_full_row(self):
        self.binding['jobs']['field']['accesses'][0]['mask']=1
        r=self.run_compile(); self.assertFalse(r['dispatch_eligible'])
        self.assertIn('unproduced_native_read',[e['kind'] for e in r['rejections']])

    def test_physical_latency_change_requires_recompile(self):
        self.binding['jobs']['su']['duration_cycles']=11
        self.assertFalse(self.run_compile()['dispatch_eligible'])

    def test_done_row_missing_issue_to_command_pin_edge_rejected(self):
        # MIX4 off-by-one class: done = issue + pin_to_pin (no +1) must not compile, for every engine.
        for index in range(len(self.program['ops'])):
            program=copy.deepcopy(self.program)
            op=program['ops'][index]; op['end']=op['start']+self.binding['jobs'][op['id']]['duration_cycles']
            r=compile_program(program,self.binding,self.contract,self.root)
            self.assertFalse(r['dispatch_eligible'])
            reasons=[e.get('reason','') for e in r['rejections']]
            self.assertTrue(any('issue + 1' in x for x in reasons),reasons)
        self.assertEqual(issuer_done_row(656,772),1429)
        for bad in [(656,0),(-1,772),(656,True and 1.0)]:
            with self.assertRaises(ValueError): issuer_done_row(*bad)

    def test_hc_return_columns_stage_requires_remeasured_duration(self):
        from compile_calendar import PIPELINE_ABI
        self.binding['jobs']['su']['engine']='hc'; self.program['ops'][1]['eng']='hc'
        r=self.run_compile(); self.assertFalse(r['dispatch_eligible'])
        self.assertTrue(any('stale hc pipeline' in e.get('reason','') for e in r['rejections']), r['rejections'])
        stale=dict(PIPELINE_ABI['hc'], return_columns_extra_edges=0)
        self.binding['jobs']['su']['pipeline_abi']=stale
        self.assertFalse(self.run_compile()['dispatch_eligible'])
        with self.assertRaises(ValueError): schedule_jobs(self.program,self.binding)
        self.binding['jobs']['su']['pipeline_abi']=dict(PIPELINE_ABI['hc'])
        self.assertTrue(self.run_compile()['dispatch_eligible'])

    def test_coll_cal7_v3_and_pincap_record_is_the_collective_controller_profile(self):
        # the S81 compiler's coll record must equal the bound collective controller ROM profile (CAL7 v3 + PINCAP 1)
        import importlib.util
        spec=importlib.util.spec_from_file_location('cimg',ROOT/'tools/s81_static_collective/resetpins/controller_image.py')
        cimg=importlib.util.module_from_spec(spec); spec.loader.exec_module(cimg)
        rec=PIPELINE_ABI['coll']
        self.assertEqual(rec['control_rom_abi'],cimg.ABI)
        for k in ('control_rom_output_capture_edges_hidden_by_prefetch','control_rom_initialization_extra_edges','vm_boundary_pin_capture_edges'):
            self.assertEqual(rec[k],cimg.LATENCIES[k],k)
        self.assertEqual(rec['vm_boundary_pin_capture_edges'],1)
        # a coll job measured on the v2 ROM / PINCAP 0 boundary is refused, the current record accepted
        self.binding['jobs']['su']['engine']='coll'; self.program['ops'][1]['eng']='coll'
        for stale in (None, dict(rec,vm_boundary_pin_capture_edges=0), dict(rec,control_rom_abi='opentallas.s81.collective-fixed-edge-rom.v2')):
            if stale is None: self.binding['jobs']['su'].pop('pipeline_abi',None)
            else: self.binding['jobs']['su']['pipeline_abi']=stale
            self.assertFalse(self.run_compile()['dispatch_eligible'])
            with self.assertRaises(ValueError): schedule_jobs(self.program,self.binding)
        self.binding['jobs']['su']['pipeline_abi']=dict(rec)
        self.assertTrue(self.run_compile()['dispatch_eligible'])

    def test_fld_record_carries_the_static_return_node_r2_pipeline(self):
        # S-NET r2 node: +3 edges per node level (PIPE_C 10); field durations measured on the 7-edge node are refused
        import importlib.util
        spec=importlib.util.spec_from_file_location('src',ROOT/'tools/s81/static_return_calendar.py')
        src=importlib.util.module_from_spec(spec); spec.loader.exec_module(src)
        rec=PIPELINE_ABI['fld']
        self.assertEqual(rec['return_node_exit_edges'],src.PIPE_C)
        self.assertEqual(rec['return_node_levels_max'],6)
        good=self.binding['jobs']['field']['pipeline_abi']
        self.binding['jobs']['field']['pipeline_abi']=dict(good,return_node_exit_edges=7)
        self.assertFalse(self.run_compile()['dispatch_eligible'])
        with self.assertRaises(ValueError): schedule_jobs(self.program,self.binding)
        self.binding['jobs']['field']['pipeline_abi']=good
        self.assertTrue(self.run_compile()['dispatch_eligible'])

    def test_tile_pin_registers_come_from_the_kit_port_latency_report(self):
        # owner 19:50: registered tile pins (+1-2 edges a boundary) enter the schedule from the kit report, not constants
        from compile_calendar import kit_boundary_edges, KIT_PORT_LATENCY_SCHEMA
        rep=self.root/'kit'/'port_latency.json'; rep.parent.mkdir()
        rep.write_text(json.dumps(dict(schema=KIT_PORT_LATENCY_SCHEMA,ports=dict(c_cmd=dict(dir='input',register_edges=1),
                                                                                  c_done=dict(dir='output',register_edges=2)))))
        sha=hashlib.sha256(rep.read_bytes()).hexdigest()
        su=self.binding['jobs']['su']
        su['kit_boundary']=dict(report='kit/port_latency.json',sha256=sha,ports=['c_cmd','c_done'],duration_measured_at='rtl_core')
        self.assertEqual(kit_boundary_edges(su,self.root),3)
        # the graph priced at 10 is now stale (pin-to-pin 13): refused until recompiled
        self.assertFalse(self.run_compile()['dispatch_eligible'])
        sched=schedule_jobs(self.program,self.binding,self.root)
        self.assertEqual(sched['ops'][1]['end']-sched['ops'][1]['start'],1+10+3)
        self.program=sched; self.assertTrue(self.run_compile()['dispatch_eligible'])
        su['kit_boundary']=dict(su['kit_boundary'],duration_measured_at='kit_pins'); self.assertEqual(kit_boundary_edges(su,self.root),0)
        for bad in (dict(su['kit_boundary'],sha256='0'*64), dict(su['kit_boundary'],ports=['c_cmd','nope']),
                    dict(su['kit_boundary'],duration_measured_at=None)):
            su['kit_boundary']=bad
            with self.assertRaises(ValueError): kit_boundary_edges(su,self.root)
        del su['kit_boundary']; su['boundary_edges']=2
        with self.assertRaises(ValueError): kit_boundary_edges(su,self.root)

    def test_vm_a2f_relay_record_required_on_vm_touching_jobs(self):
        vm=PIPELINE_ABI['vm']
        self.assertEqual((vm['a2_write_extra_edges'],vm['a2f_relay_write_edges'],vm['a2f_relay_read_edges'],vm['a2f_relay_commit_edges']),(2,9,16,3))
        su=self.binding['jobs']['su']
        for stale in (None, dict(vm,a2f_relay_read_edges=0)):
            if stale is None: su.pop('vm_pipeline_abi')
            else: su['vm_pipeline_abi']=stale
            self.assertFalse(self.run_compile()['dispatch_eligible'])
            with self.assertRaises(ValueError): schedule_jobs(self.program,self.binding)
        su['vm_pipeline_abi']=dict(vm); self.assertTrue(self.run_compile()['dispatch_eligible'])

    def test_sa2x2rp_floorplan_stages_require_remeasured_durations(self):
        # SA_2x2_RP: SU-VM link +3 relay edges, field round trip 140 -> 118: old measurements are refused
        self.assertEqual(PIPELINE_ABI['su']['vm_link_relay_extra_edges'],3)
        self.assertEqual(PIPELINE_ABI['fld']['field_round_trip_cycles'],118)
        for name,key,old in [('su','vm_link_relay_extra_edges',0),('field','field_round_trip_cycles',140)]:
            good=self.binding['jobs'][name]['pipeline_abi']
            self.binding['jobs'][name]['pipeline_abi']=dict(good,**{key:old})
            self.assertFalse(self.run_compile()['dispatch_eligible'])
            with self.assertRaises(ValueError): schedule_jobs(self.program,self.binding)
            del self.binding['jobs'][name]['pipeline_abi']
            self.assertFalse(self.run_compile()['dispatch_eligible'])
            self.binding['jobs'][name]['pipeline_abi']=good
            self.assertTrue(self.run_compile()['dispatch_eligible'])

    def test_clock_phase_mismatch_rejected(self):
        self.binding['jobs']['su']['phase_period_stream']=4
        self.binding['jobs']['su']['start_phase_stream']=1
        self.assertFalse(self.run_compile()['dispatch_eligible'])

    def test_engine_overlap_rejected(self):
        self.program['ops'][1].update(port=0,start=2,end=13,preds=[])
        r=self.run_compile(); self.assertFalse(r['dispatch_eligible'])
        self.assertIn('engine_overlap',[e['kind'] for e in r['rejections']])

    def test_stale_source_rejected(self):
        (self.root/'native.sv').write_text('changed source')
        self.assertFalse(self.run_compile()['dispatch_eligible'])

    def test_aliasing_live_tensors_rejected(self):
        self.binding['tensors']['r']=copy.deepcopy(self.binding['tensors']['q'])
        r=self.run_compile(); self.assertFalse(r['dispatch_eligible'])
        self.assertIn('live_tensor_address_alias',[e['kind'] for e in r['rejections']])

    def test_bank_collision_cannot_silently_extend_schedule(self):
        self.binding['tensors']['q']['nrows']=33
        extra=copy.deepcopy(self.binding['jobs']['su']['accesses'][0]); extra['row_offset']=32
        self.binding['jobs']['su']['accesses'].append(extra)
        write=copy.deepcopy(self.binding['jobs']['field']['accesses'][0]); write['row_offset']=32
        self.binding['jobs']['field']['accesses'].append(write)
        r=self.run_compile(); self.assertFalse(r['dispatch_eligible'])
        self.assertIsNone(r['schedule'])
        self.assertIn('bank_collision',[e['kind'] for e in r['reservations']['violations']])

    def test_offline_schedule_serializes_ports_and_reserves_phase(self):
        self.program['ops'][1].update(port=0,start=2,end=12,preds=[])
        self.binding['jobs']['su'].update(phase_period_stream=4,start_phase_stream=3)
        lowered=schedule_jobs(self.program,self.binding)
        self.assertEqual(lowered['ops'][1]['start'],11)
        self.assertEqual(lowered['ops'][0]['end'],11)
        self.assertEqual(lowered['ops'][1]['end'],22)
        self.assertFalse(lowered['offline_schedule']['performance_accepted'])
        self.assertEqual(self.program['ops'][1]['start'],2)
        self.assertTrue(compile_program(lowered,self.binding,self.contract,self.root)['dispatch_eligible'])

    def test_offline_schedule_cannot_infer_missing_native_duration(self):
        del self.binding['jobs']['su']['duration_cycles']
        with self.assertRaises(KeyError):
            schedule_jobs(self.program,self.binding)

    def test_native_ingress_resource_preserved(self):
        self.contract['ingress_capacities']={'capture/write':1,'ctrl_p3/read':1}
        self.binding['jobs']['field']['accesses'][0]['ingress_resource']='capture/write'
        self.binding['jobs']['su']['accesses'][0]['ingress_resource']='ctrl_p3/read'
        result=self.run_compile()
        self.assertTrue(result['dispatch_eligible'], result)
        self.assertEqual(result['schedule']['events'][0]['ingress_resource'],'capture/write')

    def test_all_59_actual_programs_require_native_binding(self):
        sources=sorted((ROOT/'results/rtl/s81_ctrl_20261008/programs').glob('S[0-9][0-9][0-9].json'))
        self.assertEqual(len(sources),59)
        jobs=0
        for path in sources:
            program=json.loads(path.read_text())
            r=compile_program(program,dict(stage=program['stage']),self.contract,self.root)
            self.assertFalse(r['dispatch_eligible']); self.assertIsNone(r['schedule'])
            self.assertEqual(sum(e['kind']=='missing_native_job_binding' for e in r['rejections']),len(program['ops']))
            jobs+=len(program['ops'])
        self.assertGreater(jobs,1000)


if __name__=='__main__':
    unittest.main()
