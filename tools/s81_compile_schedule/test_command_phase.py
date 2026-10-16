"""Compiler-only witnesses for reset-relative HCX issue phase; no native claim."""
import copy
import unittest
import test_compile_calendar as fixtures
from compile_calendar import command_issue_phase, schedule_jobs, compile_program


class CommandPhaseTest(unittest.TestCase):
    setUp = fixtures.CompileTest.setUp
    tearDown = fixtures.CompileTest.tearDown

    def clock(self):
        return dict(stream_period_ps='2500/3', serial_period_ps='10000/9',
                    first_active_stream_edge=1000, context_accept_stream_edge=1250,
                    issuer_to_engine_sample_edges=2, required_counter_phase=2,
                    evidence=self.evidence)

    def test_derive_reset_relative_phase_and_dependency_alignment(self):
        clock=self.clock()
        self.assertEqual(command_issue_phase(clock,self.root),(4,2))
        job=self.binding['jobs']['su']
        job.update(command_clock_abi=clock, phase_period_stream=4,start_phase_stream=2)
        # MIX4 native pin->pin 810 at issue656 completes1467; next HCX row1470.
        self.binding['jobs']['field']['duration_cycles']=810
        self.program['ops'][0]['ext']=656
        self.program['ops'][1]['ext']=1467
        sched=schedule_jobs(self.program,self.binding,self.root)
        self.assertEqual(sched['ops'][0]['end'],1467)
        self.assertEqual(sched['ops'][1]['start'],1470)
        # Every different job epoch translates to the correct relative row.
        for shift in range(8):
            moved=dict(clock,context_accept_stream_edge=1250+shift)
            self.assertEqual(command_issue_phase(moved,self.root),(4,(2-shift)%4))

    def test_old_phase_and_missing_pin_edge_are_rejected(self):
        job=self.binding['jobs']['su']
        job.update(command_clock_abi=self.clock(),phase_period_stream=4,start_phase_stream=0)
        with self.assertRaisesRegex(ValueError,'reset/command clock ABI'):
            schedule_jobs(self.program,self.binding,self.root)
        r=compile_program(self.program,self.binding,self.contract,self.root)
        self.assertFalse(r['dispatch_eligible'])
        for key,value in [('issuer_to_engine_sample_edges',1),('required_counter_phase',4),
                          ('serial_period_ps','2500/3'),('evidence',[])]:
            bad=copy.deepcopy(self.clock());bad[key]=value
            with self.assertRaises((ValueError,KeyError)):
                command_issue_phase(bad,self.root)


if __name__=='__main__':unittest.main()
