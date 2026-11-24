"""FLOW-1700: a request ot-run refuses before the unit starts ends with `NOT-RUN <reason>` as the last stderr line and exit status 78."""
import io, pathlib, re, unittest
from contextlib import redirect_stderr
import test_ot_run_scratch_disk as T

m = T.m
SRC = (pathlib.Path(__file__).resolve().parent / "ot-run").read_text()


class NotRun(unittest.TestCase):
    def test_helper_prints_the_line_and_exits_78(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as c:
            m.not_run("every requested host is held (x)")
        self.assertEqual(c.exception.code, 78)
        self.assertEqual(err.getvalue().strip().splitlines()[-1], "NOT-RUN every requested host is held (x)")

    def test_every_client_refusal_goes_through_the_helper(self):
        main = SRC[SRC.index("def main("):] if "def main(" in SRC else SRC[SRC.index("NEEDS_1115"):]
        for ln in main.splitlines():
            if "NOT RUN" in ln and "sys.exit(" in ln:
                self.fail("refusal exits without NOT-RUN/78: " + ln.strip())
        self.assertGreaterEqual(SRC.count("not_run("), 6)

    def test_status_75_is_no_longer_the_final_status_of_a_refusal(self):
        self.assertNotRegex(SRC, r"say\(f?\"ot-run: NOT RUN[^\n]*\n\s+sys\.exit\(75\)")


def test_snapshot_declarations_are_exact_read_only_inputs():
    prefix = "/srv/opentallas-scratch2/kit-store/snaps/" + "a" * 40
    assert m.snapshot_stage_path(prefix + "/root/srv/opentallas-scratch2/claude/head-west/bind")
    assert not m.snapshot_stage_path(prefix)
    assert not m.snapshot_stage_path(prefix + "/root/etc/passwd")
    assert not m.snapshot_stage_path(prefix + "/root/srv/opentallas-scratch2/claude/head-west/../../secret")


if __name__ == "__main__":
    unittest.main()
