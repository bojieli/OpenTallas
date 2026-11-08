"""KW-FIX-32 11-07 (COORD 19:0x, FLOW-CHILD-ETM-CONTEXT at sign-off, DIE-HBM-89 q_spb2 vE): the kit runners hand the
parent flow tag to signoff.py (--flow-tag), so unexpanded child ETMs can count as SIGNED_CHILD_ETM; no tag = unchanged."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]


def signoff_block():
    import gen_phys
    lines = gen_phys.RUN_KIT.splitlines()
    a = next(i for i, ln in enumerate(lines) if ln.startswith("if [ $rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then"))
    b = next(i for i in range(a, len(lines)) if lines[i] == "fi")
    return "\n".join(lines[a:b + 1])


class RunKitSignoffFlowTag(unittest.TestCase):
    def run_block(self, ft):
        d = tempfile.mkdtemp()
        K = Path(d)
        (K / "signoff.py").write_text("import sys\nprint('ARGV', ' '.join(sys.argv[1:]))\n")
        sh = "K=%s\nrc=0\nGOAL=route\nIMAGE=img\nFT=%s\n%s\ncat \"$K/signoff.log\"\n" % (K, ft, signoff_block())
        p = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return next(ln for ln in p.stdout.splitlines() if ln.startswith("ARGV"))

    def test_tag_passed_when_set(self):
        argv = self.run_block("flow-20261107-ei-hbm")
        self.assertIn("--flow-tag flow-20261107-ei-hbm", argv)
        self.assertIn("--corners tt,ff", argv)

    def test_no_tag_unchanged(self):
        argv = self.run_block("")
        self.assertNotIn("--flow-tag", argv)

    def test_same_ft_as_grt_gate(self):
        import gen_phys
        rk = gen_phys.RUN_KIT
        self.assertLess(rk.index('FT=${OT_FLOW_TAG:-$(head -1 "$K/flow_tag" 2>/dev/null)}'),
                        rk.index('"$K/signoff.py" run'))
        p = subprocess.run(["bash", "-n"], input=rk, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


class CoreRunnersSignoffFlowTag(unittest.TestCase):
    def test_core_runners(self):
        for rel in ("physical/die_plan/hbm_arch_cores/run_kit_hbm.sh",
                    "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh"):
            t = (REPO / rel).read_text()
            i = t.index('"$K/signoff.py" run')
            self.assertIn('${FT:+--flow-tag "$FT"}', t[i:i + 300], rel)
            self.assertIn('FT=${OT_FLOW_TAG:-$(head -1 "$K/flow_tag" 2>/dev/null)}', t[:i], rel)
            p = subprocess.run(["bash", "-n", str(REPO / rel)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
