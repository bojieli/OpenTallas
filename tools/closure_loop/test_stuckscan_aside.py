"""drive-0849 2026-10-10: a retried job's aside directory (<dir>.attempt<N>) is not a live ORFS base."""
import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import stuckscan as ss  # noqa: E402

NS = {}
exec("import re, os, glob\n" + ss.PROBE[ss.PROBE.index("def rd("):ss.PROBE.index("def probe_base")], NS)


class Aside(unittest.TestCase):
    def test_aside_bases_ignored(self):
        with tempfile.TemporaryDirectory() as r:
            for d in ("routes/x/work/orfs/logs/asap7/d/base", "routes/x.attempt1/work/orfs/logs/asap7/d/base",
                      "routes/x.attempt1.1700000000/work/orfs/logs/asap7/d/base"):
                os.makedirs(os.path.join(r, d))
            got = NS["bases"](dict(run=r))
        self.assertEqual([g[len(r):] for g in got], ["/routes/x/work/orfs/logs/asap7/d/base"])


if __name__ == "__main__":
    unittest.main()
