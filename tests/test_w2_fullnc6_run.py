import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w2_fullnc6_run as runner

class CompileAdmissionTests(unittest.TestCase):
    def test_large_host_uses32_and_small_host_uses_available(self):
        self.assertEqual(runner.choose_jobs(124.5),32)
        self.assertEqual(runner.choose_jobs(62.7),32)
        self.assertEqual(runner.choose_jobs(7.8),7)

    def test_no_idle_cpu_refuses_instead_of_launching_busy_job(self):
        with self.assertRaisesRegex(ValueError,'NO_LOCAL_CPU_HEADROOM'):
            runner.choose_jobs(0.8)

    def test_explicit_jobs_require_measured_headroom(self):
        self.assertEqual(runner.choose_jobs(40,32),32)
        with self.assertRaisesRegex(ValueError,'EXCEED_MEASURED'):
            runner.choose_jobs(16,32)

    def test_cpu_sample_honors_affinity_and_measures_tick_deltas(self):
        before={0:(100,20),1:(200,50),2:(300,60)}
        after={0:(200,120),1:(300,75),2:(400,160)}
        self.assertEqual(runner.idle_cpu_equivalents(before,after,{0,1}),1.25)

if __name__=='__main__':unittest.main()
