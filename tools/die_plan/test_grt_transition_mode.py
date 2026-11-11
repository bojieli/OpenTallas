"""GRT-PATCH-1 11-11: opt-in halving-off router arm (run_kit.sh GRTM block, gen-time K/grt_transition_mode,
route_supply per-type mode).  Default (no mode) must leave the main ORFS run on the stock image with no extra args."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_grtm_test", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


GP = _load("gen_phys")
RS = _load("route_supply")
LINES = GP.RUN_KIT.splitlines()
I0 = next(i for i, l in enumerate(LINES) if l.startswith("IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}"))
PRE = [l for l in LINES[I0 + 1:I0 + 20] if l.endswith("# GRTM")]
I1 = next(i for i, l in enumerate(LINES) if l.startswith('[ -z "$LECA" ] || rc=$(bash'))
POST = [l for l in LINES[I1 + 1:I1 + 6] if l.endswith("# GRTM")]


def run(K, env, body, docker_ok=True):
    d = Path(K) / "bin"
    d.mkdir(exist_ok=True)
    (d / "fakedocker").write_text("#!/bin/bash\n" + ("echo sha256:feed\n" if docker_ok else "exit 1\n"))
    (d / "fakedocker").chmod(0o755)
    script = "set -u\nK=%s\nGOAL=grt\nIMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}\n%s\n%s\n" % (K, "\n".join(PRE), body)
    e = {"PATH": os.environ["PATH"], "OT_DOCKER": str(d / "fakedocker"), **env}
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=e)


class GrtTransitionModeTest(unittest.TestCase):
    def test_template_blocks_present(self):
        self.assertGreaterEqual(len(PRE), 8)
        self.assertEqual(len(POST), 3)
        main = [l for l in LINES if '-w /OpenROAD-flow-scripts/flow "$GIMAGE" bash -lc' in l]
        self.assertEqual(len(main), 1)
        self.assertEqual(sum('"${GRTD[@]}"' in l for l in LINES), 1)
        # LEC and sign-off stay on the stock image
        self.assertTrue(any('lec_async.sh" start "$K" "$NAME" "$IMAGE"' in l for l in LINES))
        self.assertTrue(any('--image "$IMAGE" --corners' in l for l in LINES))

    def test_default_is_stock(self):
        with tempfile.TemporaryDirectory() as K:
            r = run(K, {}, 'echo "IMG=$GIMAGE N=${#GRTD[@]}"; echo argv x "${GRTD[@]}" y')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("IMG=openroad/orfs:asap7lock N=0", r.stdout)
            self.assertIn("argv x y\n", r.stdout)
            self.assertFalse((Path(K) / "grt_transition.json").exists())
            r = run(K, {"OT_ORFS_IMAGE": "openroad/orfs:other"}, 'echo "IMG=$GIMAGE N=${#GRTD[@]}"')
            self.assertIn("IMG=openroad/orfs:other N=0", r.stdout)

    def test_mode_from_kit_file_and_env(self):
        with tempfile.TemporaryDirectory() as K:
            (Path(K) / "grt_transition_mode").write_text("off\n")
            r = run(K, {}, 'echo "IMG=$GIMAGE STOCK=$IMAGE ARGS=${GRTD[*]}"')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("IMG=opentallas/orfs:asap7lock-grtoff STOCK=openroad/orfs:asap7lock "
                          "ARGS=-e OT_GRT_TRANSITION_MODE=off", r.stdout)
            rec = (Path(K) / "grt_transition.json").read_text()
            self.assertIn('"image_id": "sha256:feed"', rec)
            r = run(K, {"OT_GRT_TRANSITION_MODE": "edge_outline", "OT_GRT_IMAGE": "x/y:z"}, 'echo "IMG=$GIMAGE ARGS=${GRTD[*]}"')
            self.assertIn("IMG=x/y:z ARGS=-e OT_GRT_TRANSITION_MODE=edge_outline", r.stdout)

    def test_bad_mode_or_missing_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as K:
            r = run(K, {"OT_GRT_TRANSITION_MODE": "halfoff"}, "echo REACHED")
            self.assertEqual(r.returncode, 10)
            self.assertNotIn("REACHED", r.stdout)
            r = run(K, {"OT_GRT_TRANSITION_MODE": "off"}, "echo REACHED", docker_ok=False)
            self.assertEqual(r.returncode, 10)
            self.assertIn("missing", r.stdout)

    def test_post_gate_needs_grt9103(self):
        with tempfile.TemporaryDirectory() as K:
            lg = Path(K) / "run/logs/asap7/d/base"
            lg.mkdir(parents=True)
            body = "rc=0\n" + "\n".join(POST) + '\necho "RC=$rc"'
            (lg / "5_1_grt.log").write_text("[INFO GRT-0096] stock\n")
            r = run(K, {"OT_GRT_TRANSITION_MODE": "off"}, body)
            self.assertIn("RC=1", r.stdout)
            self.assertTrue((Path(K) / "FAIL_GRT_MODE").exists())
            (lg / "5_1_grt.log").write_text("[INFO GRT-9103] OT transition-layer mode off (K=2 gcells).\n")
            r = run(K, {"OT_GRT_TRANSITION_MODE": "off"}, body)
            self.assertIn("RC=0", r.stdout)
            r = run(K, {"OT_GRT_TRANSITION_MODE": "edge"}, body)
            self.assertIn("RC=1", r.stdout)
            (lg / "5_1_grt.log").write_text("no mode line\n")
            r = run(K, {}, body)                                   # stock run: no gate
            self.assertIn("RC=0", r.stdout)

    def test_gen_writes_mode_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(GP.write_grt_transition_mode(d, {}))
            self.assertFalse((Path(d) / "grt_transition_mode").exists())
            self.assertEqual(GP.write_grt_transition_mode(d, {"OT_GRT_TRANSITION_MODE": "off"}), "off")
            self.assertEqual((Path(d) / "grt_transition_mode").read_text(), "off\n")
            with self.assertRaises(ValueError):
                GP.write_grt_transition_mode(d, {"OT_GRT_TRANSITION_MODE": "none"})

    def test_route_supply_per_type(self):
        self.assertEqual(RS.grt_halving_types([]), {})
        self.assertEqual(RS.grt_halving_types(["a=off", "b=edge_outline"]), {"a": "off", "b": "edge_outline"})
        for bad in ("a", "a=half", "=off"):
            with self.assertRaises(ValueError):
                RS.grt_halving_types([bad])


if __name__ == "__main__":
    unittest.main()
