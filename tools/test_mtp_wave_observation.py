import unittest
from mtp_wave_bench import classify_run


class WaveObservation(unittest.TestCase):
    def test_missing_pass_is_not_a_caught_mutant(self):
        self.assertEqual(classify_run('startup only\n', 0), 'no_observation')

    def test_unrelated_landing_overflow_is_harness_failure(self):
        log = 'FATAL: dsfd_p2_lnk.sv:220: landing queue overflow (RL 4 D 10)\n'
        self.assertEqual(classify_run(log, 1), 'runtime_error')
        self.assertEqual(classify_run(log, 0), 'runtime_error')

    def test_missing_image_is_not_a_caught_mutant(self):
        self.assertEqual(classify_run('ERROR: $readmemh cannot open mk_w.hex\n', 0), 'runtime_error')

    def test_explicit_payload_failure_is_observed(self):
        self.assertEqual(classify_run('WAVE FAIL: P2 row numeric at 42\n', 0), 'fail')

    def test_contradictory_payload_failure_cannot_pass(self):
        self.assertEqual(classify_run('WAVE FAIL: payload\nWAVE PASS emitted=12\n', 0), 'fail')

    def test_pass_requires_successful_simulator_exit(self):
        self.assertEqual(classify_run('WAVE PASS emitted=12\n', 0), 'pass')
        self.assertEqual(classify_run('WAVE PASS emitted=12\n', -11), 'runtime_error')


if __name__ == '__main__':
    unittest.main()
