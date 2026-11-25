"""RT-PRUNE-REFS-1124c: admission bundle push to the hub at stage time + fetch backoff.  python3 -I tools/autopilot/test_admission_push_1124.py"""
import os, sys, types, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autopilot as AP


class Push(unittest.TestCase):
    def fake(self, have):
        calls = []
        def run(argv, **k):
            calls.append(argv)
            rc = 0
            if argv[0] == "ssh" and "test -f" in argv[-1] and "mv -T" not in argv[-1]:
                rc = 0 if have else 1
            return types.SimpleNamespace(returncode=rc)
        return run, calls

    def test_pushes_part_then_rename(self):
        run, calls = self.fake(False)
        self.assertTrue(AP.push_admission_to_hub("/srv/opentallas-scratch2/claude/autopilot/admission_tools/abc", hub="h", run=run))
        self.assertEqual([c[0] for c in calls], ["ssh", "rsync", "ssh"])
        self.assertIn(".part.", calls[1][-1])
        self.assertIn("mv -T", calls[2][-1])

    def test_hub_already_has_it_no_copy(self):
        run, calls = self.fake(True)
        self.assertTrue(AP.push_admission_to_hub("/x/abc", hub="h", run=run))
        self.assertEqual(len(calls), 1)

    def test_failure_never_raises(self):
        def boom(*a, **k): raise OSError("x")
        self.assertFalse(AP.push_admission_to_hub("/x/abc", hub="h", run=boom))

    def test_bootstrap_backs_off_between_attempts(self):
        self.assertIn("sleep(5*3**(attempt-1))", AP.ADMISSION_BOOTSTRAP)


if __name__ == "__main__":
    unittest.main()
