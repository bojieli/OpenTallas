import pathlib, subprocess, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ot_cleanup_provrefs as m


class ProvRefs(unittest.TestCase):
    def test_build_and_protected(self):
        with tempfile.TemporaryDirectory() as t:
            r = pathlib.Path(t) / "r"; v = r / "physical/die_plan/s81/cores/views/x"; v.mkdir(parents=True)
            (v / "PROVENANCE.json").write_text('{"a": "/srv/opentallas-scratch3/claude/die-s81-85/t51eco/i1/run/6_final.odb"}')
            g = lambda *a: subprocess.run(["git", "-C", str(r), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)
            g("init", "-q"); g("add", "-A"); g("commit", "-qm", "x"); g("branch", "-M", "main")
            refs = m.build(str(r), None, "HEAD")
            self.assertIn("/srv/opentallas-scratch2/claude/die-s81-85/t51eco/i1/run/6_final.odb", refs)
            self.assertTrue(m.protected("/srv/opentallas-scratch2/claude/die-s81-85", refs))        # parent of a referenced file
            self.assertTrue(m.protected("/srv/opentallas-scratch2/claude/die-s81-85/t51eco/i1/run/6_final.odb/x", refs))
            self.assertFalse(m.protected("/srv/opentallas-scratch2/claude/die-s81-86", refs))


if __name__ == "__main__":
    unittest.main()
