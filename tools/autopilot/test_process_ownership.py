"""Many terminal jobs must not repeatedly tokenize the same large live argv."""
import unittest
from unittest import mock

import autopilot as A


class ProcessOwnershipTest(unittest.TestCase):
    def setUp(self):
        A.process_staging_roots.cache_clear()

    def test_large_live_parent_is_parsed_once_for_distinct_nested_kits(self):
        root = '/srv/opentallas-scratch2/claude/parent/e2'
        argv = 'python3 /home/ubuntu/.local/bin/ot-run --stage=' + root + " -- python3 -c '" + 'x' * 50000 + "'"
        with mock.patch.object(A.shlex, 'split', wraps=A.shlex.split) as split:
            for i in range(30):
                self.assertTrue(A.process_uses_kit(argv, root + '/kit' + str(i)))
            self.assertFalse(A.process_uses_kit(argv, root + '0/kit'))
            self.assertEqual(split.call_count, 1)
            changed = argv.replace('/parent/e2', '/parent/e3')
            self.assertFalse(A.process_uses_kit(changed, root + '/kit'))
            self.assertEqual(split.call_count, 2)

    def test_malformed_and_literal_live_clients_retain_ownership(self):
        kit = '/srv/opentallas-scratch2/claude/parent/e2/kit'
        self.assertTrue(A.process_uses_kit("ot-run --dir 'unfinished", kit))
        self.assertTrue(A.process_uses_kit('docker run ' + kit + '/run', kit))
        self.assertFalse(A.process_uses_kit('docker run ' + kit + 'ty/run', kit))

    def test_existing_exclusions_skip_parsing_before_ownership_work(self):
        lines = '123 20 python3 autopilot.py ignored\n124 30 ssh host ignored\n125 40 python3 -I - ignored\n'
        with mock.patch.object(A, 'sh', return_value=(0, lines, '')), \
                mock.patch.object(A, 'process_uses_kit', side_effect=AssertionError('excluded process parsed')):
            self.assertEqual(A.hub_procs('/srv/opentallas-scratch2/claude/example'), [])


if __name__ == '__main__':
    unittest.main()
