"""Compiler negative witnesses; fixtures below qualify the compiler only."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from compile_calendar import compile_program, schedule_jobs, issuer_done_row, ROOT, PIPELINE_ABI


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
