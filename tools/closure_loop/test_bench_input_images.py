"""Missing memory images cannot qualify all-zero comparisons or mutants."""
from types import SimpleNamespace
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import closure_loop as CL

BAD = "%Warning: /work/cap_images/s0/sm00/backing.hex:0: $readmem file not found"


class InputImages(unittest.TestCase):
    def test_missing_images_reject_positive_and_mutant_even_with_verdicts(self):
        log = BAD + "\nEXACT PASS checks=1000\nMUTANT FAIL\n"
        for expect, rc in [('pass', 0), ('fail', 1), ('fail', 0)]:
            job = dict(host='h', run='/r', stage_tag='b')
            stage = dict(key='b', expect=expect, pass_regex='EXACT PASS', fail_regex='MUTANT FAIL')
            with patch.object(CL, 'ssh', return_value=SimpleNamespace(returncode=0, stdout='OT_BENCH_LOG_READ\n' + log)):
                self.assertFalse(CL.bench_outcome(job, stage, rc))
            self.assertIn('input error', CL.bench_why(job, stage, rc))
            self.assertFalse(CL.expected_fail_seen(stage, rc, log))

    def test_icarus_missing_file_and_normal_image_messages(self):
        self.assertTrue(CL.bench_input_error('ERROR: tb.sv:5: $readmemh: Unable to open weights.hex for reading.'))
        self.assertTrue(CL.bench_input_error("$readmemb cannot open program.bin"))
        self.assertFalse(CL.bench_input_error('Loaded image using $readmemh; checks=1000 PASS'))
        self.assertFalse(CL.bench_input_error('$readmemh: Not enough words in file for requested range [0:4095].'))

    def test_real_mutant_still_counts(self):
        self.assertTrue(CL.expected_fail_seen(dict(fail_regex='SCORE_AGE_MISMATCH'), 1, 'SCORE_AGE_MISMATCH at 10'))

    def test_initialization_error_before_log_tail_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            cl = Path(tmp) / 'cl'
            cl.mkdir()
            (cl / 'b.log').write_text(BAD + '\n' + 'checked a word\n' * 21000 + 'EXACT PASS checks=21000\n')
            def local_read(host, command, **kwargs):
                return subprocess.run(['bash', '-c', command], capture_output=True, text=True)
            job = dict(host='unused', run=tmp, stage_tag='b')
            with patch.object(CL, 'ssh', side_effect=local_read):
                self.assertFalse(CL.bench_outcome(job, dict(key='b', expect='pass', pass_regex='EXACT PASS'), 0))
            self.assertIn('input error', job['bench_work']['b'])


if __name__ == '__main__':
    unittest.main()
