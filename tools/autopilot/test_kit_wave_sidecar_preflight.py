import json, subprocess, sys, tempfile, unittest
from pathlib import Path
import kit_wave as KW


def local_rpy(host, code, args, timeout=600):
    r = subprocess.run([sys.executable, "-I", "-c", code, json.dumps(args)], capture_output=True, text=True)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("AP_JSON ")][-1]
    return json.loads(line[8:])


class SidecarPreflight(unittest.TestCase):
    """KW-FIX-46 11-12 PSPLIT-SIDECAR-STALE: a gen sidecar missing plan part types holds the rows (fail closed)"""

    def run_case(self, types):
        td = Path(tempfile.mkdtemp())
        (td / "plan.json").write_text(json.dumps({"partitions": [{"type": "a"}, {"type": "b__pv1"}]}))
        (td / "sc.json").write_text(json.dumps({"collector": {"types": {t: {} for t in types}}}))
        cfg = {"dies": {"s81": {"plan": str(td / "plan.json"), "gen_host": "h",
                                "gen_args": ["--x", "1", "--clock-landing", str(td / "sc.json")]}}}
        return KW.sidecar_preflight(None, cfg, {}, "s81", [{"item": "t1"}, {"item": "c", "kind": "core"}], rpy=local_rpy)

    def test_stale_sidecar_holds(self):
        out = self.run_case(["a", "b"])
        self.assertEqual(list(out), ["t1"])
        self.assertIn("b__pv1", out["t1"])

    def test_matching_sidecar_launches(self):
        self.assertEqual(self.run_case(["a", "b__pv1"]), {})

    def test_gen_sidecar(self):
        self.assertEqual(KW.gen_sidecar(["--clock-landing", "/p"]), "/p")
        self.assertEqual(KW.gen_sidecar(["--clock-landing=/q"]), "/q")
        self.assertEqual(KW.gen_sidecar([]), "")


if __name__ == "__main__":
    unittest.main()
