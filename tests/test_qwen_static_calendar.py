"""Compiler tests are algorithm evidence, never native engine qualification."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from qwen_static_schedule.calendar import compile_calendar, verify_trace, sha, ScheduleError
from qwen_static_schedule.xpf import arm_table


class StaticCalendar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root/'engine.sv'
        self.source.write_text('module engine; endmodule\n')
        self.program = self.root/'program.hex'
        self.program.write_text('1\n2\n')
        self.contract = dict(schema='opentallas.qwen-native-microcalendar.v1',
            source_sha256={'engine.sv':sha(self.source)}, clocks={'core':dict(period_fs=10,phase_fs=0)},
            resources={'vm':dict(clock='core',capacity=1)}, deadline_fs=1000, start_fs=100,
            instructions=[dict(stage=0,pc=0,word='1',unit=2,clock='core',rtl_instance='dut.su',rtl_module='engine',
                events=[dict(id='write',offset_fs=20,resource='vm',produces=['X:epoch0'],kind='vm_write_tap',address=0,lanes=1,stride=1,mask=1)]),
                dict(stage=0,pc=1,word='2',unit=1,clock='core',rtl_instance='dut.me',rtl_module='engine',
                events=[dict(id='read',offset_fs=0,resource='vm',requires=['X:epoch0'])])])

    def tearDown(self): self.tmp.cleanup()
    def compile(self): return compile_calendar([self.program],self.contract,self.root)

    def test_dependency_and_clock(self):
        result=self.compile()
        self.assertEqual([i['time_fs'] for i in result['issues']],[100,130])
        self.assertEqual(result['events'][0]['time_fs'],120)

    def test_conflict_solved_before_execution(self):
        self.contract['instructions'][1]['events'][0].pop('requires')
        self.contract['instructions'][1]['events'][0]['offset_fs']=10
        result=self.compile()
        self.assertEqual(result['issues'][1]['time_fs'],120)
        self.assertEqual(result['events'][1]['time_fs'],130)
        self.contract['instructions'][1]['issue_at_fs']=110
        with self.assertRaises(ScheduleError):self.compile()

    def test_missing_source_producer_word_and_deadline_mutants(self):
        original=copy.deepcopy(self.contract)
        for change in ('missing','word','producer','deadline','dynamic','source'):
            self.contract=copy.deepcopy(original)
            if change=='missing': self.contract['instructions'].pop()
            if change=='word': self.contract['instructions'][0]['word']='3'
            if change=='producer': self.contract['instructions'][1]['events'][0]['requires']=['missing']
            if change=='deadline': self.contract['deadline_fs']=120
            if change=='dynamic': self.contract['instructions'][0]['events'][0]['dynamic']=True
            if change=='source': self.contract['source_sha256']['engine.sv']='0'*64
            with self.subTest(change=change),self.assertRaises(ScheduleError): self.compile()

    def test_real_trace_boundary_and_cycle_mutants(self):
        result=self.compile()
        trace=dict(program_sha256=result['program_sha256'],source_sha256=result['source_sha256'],producer='native_rtl_ports',elaboration_sha256='fixture-not-production',events=copy.deepcopy(result['events']),issues=copy.deepcopy(result['issues']))
        self.assertEqual(verify_trace(result,trace,self.root)['status'],'NATIVE_TIMELINE_MATCH')
        trace['events'][0]['time_fs']+=10
        with self.assertRaises(ScheduleError):verify_trace(result,trace,self.root)
        trace['events']=copy.deepcopy(result['events']);trace['producer']='lvm_model'
        with self.assertRaises(ScheduleError):verify_trace(result,trace,self.root)
        trace['producer']='native_rtl_ports';trace['ready_stalls']=1
        with self.assertRaises(ScheduleError):verify_trace(result,trace,self.root)

    def test_buffer_and_capacity_mutants(self):
        self.contract['buffers']={'q':dict(capacity=1)}
        self.contract['instructions'][0]['events'][0]['buffer_delta']={'q':1}
        self.contract['instructions'][1]['events'][0]['buffer_delta']={'q':-1}
        self.assertEqual(self.compile()['buffer_peaks'],{'q':1})
        self.contract['instructions'][0]['events'][0]['buffer_delta']={'q':2}
        with self.assertRaises(ScheduleError):self.compile()

    def test_compile_arms_without_trace_and_coverage_mutant(self):
        result=self.compile()
        # Descriptor: arm valid, stride1, k1, one element at address0.
        desc=1 | (1<<37) | (1<<53)
        stage=dict(stage=0,program_sha256=sha(self.program),producer_records=[dict(xpf_hex=f'{desc:018x}',producer_pcs=[0],arm_before_pc=0,producer_unit=2)])
        route=dict(source_sha256={'engine.sv':sha(self.source)},clock_period_fs=10,clock_phase_fs=0,arm_transport_edges=2,tap_internal_edges=3)
        table=arm_table(result,stage,route,self.root)
        self.assertEqual((table[0]['arm_cycle'],table[0]['issue_cycle'],table[0]['first_write_cycle']),(7,10,12))
        result['events'][0]['mask']=0
        with self.assertRaises(ScheduleError):arm_table(result,stage,route,self.root)

    def test_actual_production_programs_reject_absent_native_contracts(self):
        repo=Path(__file__).resolve().parents[1]
        programs=[repo/'results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/embedding_program.hex',
                  repo/'results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex']
        self.contract['instructions']=[]
        with self.assertRaisesRegex(ScheduleError,'incomplete actual instruction coverage'):
            compile_calendar(programs,self.contract,self.root)

    def test_multi_clock_phase(self):
        self.contract['clocks']['slow']=dict(period_fs=20,phase_fs=0)
        self.contract['resources']['vm']['clock']='slow'
        self.assertEqual([i['time_fs'] for i in self.compile()['issues']],[100,140])
        self.contract['clocks']['slow']['phase_fs']=1
        with self.assertRaises(ScheduleError):self.compile()

if __name__=='__main__':unittest.main()
