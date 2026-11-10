"""KW-FIX-44 11-10 (COORD): which prd_run.sh containers run as the host user.

The count container (openroad reads the routed DB, may write the RCX SPEF into /work, no chown after it) runs as
--user $(id -u):$(id -g), so it leaves no root-owned file.  The pass / finish containers must stay root: they patch
ORFS scripts inside the image (orfs_hold_mm.py, kwrs_busfit.py patch util.tcl; root 0664 in openroad/orfs:asap7lock,
measured 11-10 on intel2: util_NOT_writable as uid 1000), and each is followed by a root chown of /work."""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def runs():
    """every '$DK run' command of prd_run.sh, continuation lines joined"""
    text = (HERE / "prd_run.sh").read_text().replace("\\\n", " ")
    return [ln.strip() for ln in text.splitlines() if re.match(r"\s*\$DK run\b", ln)]


class ContainerUser(unittest.TestCase):
    def test_count_runs_as_host_user(self):
        count = [r for r in runs() if "--name prd-count-" in r]
        self.assertEqual(len(count), 1, runs())
        self.assertIn('--user "$(id -u):$(id -g)"', count[0])

    def test_patching_containers_stay_root_and_are_chowned(self):
        rs = runs()
        patching = [r for r in rs if "$PATCH" in r]
        self.assertEqual(len(patching), 2, rs)          # pass loop + finish
        for r in patching:
            self.assertNotIn("--user", r)
        chown = [r for r in rs if re.search(r'"\$IMAGE" chown -R \$\(id -u\):\$\(id -g\) /work', r)]
        self.assertEqual(len(chown), 2, rs)            # one root chown after each patching container
        for r in chown:
            self.assertNotIn("--user", r)
        text = (HERE / "prd_run.sh").read_text()
        self.assertIn("/OpenROAD-flow-scripts/flow/scripts/util.tcl", text)   # the in-image patch that needs root
        self.assertIn("orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts", text)


if __name__ == "__main__":
    unittest.main()
