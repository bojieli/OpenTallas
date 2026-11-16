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


class AsbuiltMap(unittest.TestCase):
    def test_nested_s81_manifest_map_is_resolved_by_real_plan_gate(self):
        # Actual S81 packed layout: base climbs five levels to the tree, but
        # map_file still starts physical/. Binder resolves map_file at the JSON.
        with tempfile.TemporaryDirectory() as t:
            repo = t + "/repo"
            os.makedirs(repo + "/physical/die_plan/s81/bind/inputs")
            g = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), check=True, capture_output=True, text=True).stdout.strip()
            g("init", "-q")
            relmap = "physical/die_plan/s81/bind/inputs/map_b178.json"
            open(repo + "/" + relmap, "w").write("{}")
            relhard = "physical/die_plan/s81/plan_inputs/romq_rtl/col.hard_params.json"
            os.makedirs(os.path.dirname(repo + "/" + relhard))
            open(repo + "/" + relhard, "w").write("{\"D\":4096}")
            g("add", "physical"); g("commit", "-qm", "map")
            SM.CACHE_DIR = t + "/cache"
            old, new = t + "/old", t + "/new"
            SM.build(repo, g("rev-parse", "HEAD"), None, ["physical"], old, main_ref="")
            rel = "physical/die_plan/s81/plan_inputs/run"
            src = t + "/stage/" + rel
            os.makedirs(src)
            open(src + "/asbuilt_run.json", "w").write(json.dumps(dict(top="dv_die", base="../../../../..", netlist=[], map_file=relmap, hard_params=[old + "/" + relhard])))
            pack = t + "/pack"
            DP.make(old, new, pack, [(src, rel)])
            SM.delta_apply(pack, old, new)
            abfile = new + "/" + rel + "/asbuilt_run.json"
            ab = json.load(open(abfile))
            self.assertEqual(ab["map_file"], "../../bind/inputs/map_b178.json")
            self.assertEqual(ab["base"], "../../../../..")
            self.assertEqual(ab["hard_params"], [relhard])
            import manifest_paths
            self.assertEqual(manifest_paths.check(ab, os.path.dirname(abfile), new), [])
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../die_plan"))
            import plan_gate_pre
            base, paths = plan_gate_pre.manifest_paths(ab, os.path.dirname(abfile), new)
            maps = [q for key, q, kind in paths if key == "map_file"]
            self.assertEqual(len(maps), 1)
            self.assertTrue(maps[0].is_file())
            SM.publish(new)
            self.assertEqual(SM.verify(new, ro=True, full=True)[0], [])

    def test_qc_manifest_relative_map_can_stay_in_baseline(self):
        with tempfile.TemporaryDirectory() as t:
            repo = t + "/repo"
            bind = "physical/die_plan/qwen_compute/bind"
            os.makedirs(repo + "/" + bind)
            g = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), check=True, capture_output=True, text=True).stdout.strip()
            g("init", "-q")
            open(repo + "/" + bind + "/asbuilt_map_p6.json", "w").write("{}")
            g("add", "physical"); g("commit", "-qm", "map")
            SM.CACHE_DIR = t + "/cache"
            old, new = t + "/old", t + "/new"
            SM.build(repo, g("rev-parse", "HEAD"), None, ["physical"], old, main_ref="")
            rel = "physical/die_plan/qwen_compute/qc_start_1106/runtime"
            stage = t + "/stage"
            os.makedirs(stage + "/" + rel)
            open(stage + "/" + rel + "/asbuilt_sw2_pv.json", "w").write(json.dumps(dict(top="qfd_die", base="../../../../..", map_file="../../bind/asbuilt_map_p6.json")))
            pack = t + "/pack"
            DP.make(old, new, pack, [(stage, ".")])
            SM.delta_apply(pack, old, new)
            ab = json.load(open(new + "/" + rel + "/asbuilt_sw2_pv.json"))
            self.assertEqual(ab["map_file"], "../../bind/asbuilt_map_p6.json")
            manifest_dir = new + "/" + rel
            import manifest_paths, plan_gate_pre
            self.assertEqual(manifest_paths.check(ab, manifest_dir, new), [])
            self.assertTrue(os.path.isfile(os.path.join(manifest_dir, ab["map_file"])))
            _, paths = plan_gate_pre.manifest_paths(ab, manifest_dir, new)
            self.assertTrue(all(path.is_file() for _, path, kind in paths if kind == "file"))
            SM.publish(new)
            self.assertEqual(SM.verify(new, ro=True, full=True)[0], [])

    def test_manifest_relative_map_takes_precedence_and_missing_map_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(t + "/manifest")
            open(t + "/manifest/map.json", "w").write("{}")
            d = DP.rebase_asbuilt_map(dict(top="dv_die", base=t, map_file="map.json"), t + "/manifest/ab.json", t, t + "/new", [(t + "/manifest", t + "/new/inputs")])
            self.assertEqual(d["map_file"], "map.json")
            self.assertEqual(d["base"], "..")
            with self.assertRaises(ValueError):
                DP.rebase_asbuilt_map(dict(top="dv_die", map_file="missing.json"), t + "/manifest/ab.json", t, t + "/new", [(t + "/manifest", t + "/new/inputs")])


if __name__ == "__main__":
    unittest.main()
