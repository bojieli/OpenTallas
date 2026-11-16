import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_pack as DP  # noqa: E402
import src_manifest as SM  # noqa: E402


class T(unittest.TestCase):
    def test_pack_moves_lane_inputs_into_the_tree_and_rewrites_paths(self):
        with tempfile.TemporaryDirectory() as t:
            repo = t + "/repo"
            os.makedirs(repo + "/tools")
            g = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), check=True, capture_output=True, text=True).stdout.strip()
            g("init", "-q")
            open(repo + "/tools/a.py", "w").write("A=1\n")
            g("add", "."); g("commit", "-qm", "m")
            sha = g("rev-parse", "HEAD")
            SM.CACHE_DIR = t + "/cache"
            old = t + "/old"
            SM.build(repo, sha, None, ["tools"], old, main_ref="")
            lane = t + "/lane/prep"
            os.makedirs(lane + "/assets")
            open(lane + "/assets/s.json", "w").write("{}")
            open(lane + "/source_plan.json", "w").write(json.dumps({"p": lane + "/assets/s.json"}))
            open(lane + "/source_sidecar.json", "w").write("{}")
            open(lane + "/wave_prepare.json", "w").write(json.dumps({"prepared_plan_sha256": "x", "sidecar_sha256": "y",
                                                                     "native_sink_censuses": {"k": {"path": lane + "/assets/s.json", "sha256": "z"}}}))
            new = t + "/new"
            pack = t + "/pack"
            n = DP.make(old, new, pack, [(lane, "physical/prep")], "physical/prep/source_plan.json:physical/prep/wave_prepare.json")
            self.assertEqual(n, 4)
            nm = SM.delta_apply(pack, old, new)
            self.assertEqual(json.load(open(new + "/physical/prep/source_plan.json"))["p"], new + "/physical/prep/assets/s.json")
            w = json.load(open(new + "/physical/prep/wave_prepare.json"))
            self.assertEqual(w["prepared_plan_sha256"], DP.sha(new + "/physical/prep/source_plan.json"))
            self.assertEqual(w["native_sink_censuses"]["k"]["path"], new + "/physical/prep/assets/s.json")
            self.assertIn("physical/prep/source_plan.json", nm["overlay"])
            SM.publish(new)
            self.assertEqual(SM.verify(new, ro=True, full=True)[0], [])
            self.assertEqual(SM.shared_inodes(new), [])


class Dot(unittest.TestCase):
    def test_reldir_dot_gives_normalised_keys(self):
        with tempfile.TemporaryDirectory() as t:
            repo = t + "/repo"
            os.makedirs(repo + "/tools")
            g = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), check=True, capture_output=True, text=True).stdout.strip()
            g("init", "-q")
            open(repo + "/tools/a.py", "w").write("A=1\n")
            g("add", "."); g("commit", "-qm", "m")
            SM.CACHE_DIR = t + "/cache"
            old = t + "/old"
            SM.build(repo, g("rev-parse", "HEAD"), None, ["tools"], old, main_ref="")
            st = t + "/stage/physical/x"
            os.makedirs(st)
            open(st + "/f.json", "w").write("{}")
            new = t + "/new"
            DP.make(old, new, t + "/pack", [(t + "/stage", ".")])
            SM.delta_apply(t + "/pack", old, new)
            SM.publish(new)
            self.assertEqual(SM.verify(new, ro=True, full=True)[0], [])


if __name__ == "__main__":
    unittest.main()
