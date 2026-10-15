"""stage_tail reads a stage's own redirected tool log (ref_tile collect '> export.log 2>&1')."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as CL  # noqa: E402


class StageLogs(unittest.TestCase):
    def job(self):
        return {"run": "/r/j1", "host": "h", "name": "j1", "spec": {"block": "b", "source": {"commit": "c"}}}

    def test_collect_redirect_target_is_tailed(self):
        st = {"cmd": "mkdir -p {RUN}/record/route && cp a b && python3 tools/ref_tile/ref_tile.py export --out x "
                     "> {RUN}/record/route/export.log 2>&1", "logs": []}
        self.assertEqual(CL.stage_logs(self.job(), st), ["/r/j1/record/route/export.log"])

    def test_declared_logs_kept_and_not_duplicated(self):
        st = {"cmd": "run.sh > {RUN}/a.log 2>&1", "logs": ["{RUN}/a.log", "{RUN}/routes/*/flow.log"]}
        self.assertEqual(CL.stage_logs(self.job(), st), ["/r/j1/a.log", "/r/j1/routes/*/flow.log"])

    def test_plain_redirects_without_stderr_and_fd_dups_ignored(self):
        st = {"cmd": "echo x > {RUN}/out.txt; cmd 2>&1 | tee y; foo >/dev/null", "logs": []}
        self.assertEqual(CL.stage_logs(self.job(), st), [])


if __name__ == "__main__":
    unittest.main()
