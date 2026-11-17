import hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import view_by_hash as V


def mk(tmp, good, bad_tool):
    v = Path(tmp) / "view" / "m1"
    le = v / "landing_evidence"
    le.mkdir(parents=True)
    so = b'{"verdict":"SIGNED"}'
    lef, lib = b"LEF", b"LIB"
    h = lambda b: hashlib.sha256(b).hexdigest()
    prov = {"kit": {"face_guard_sha256": h(good)}, "export": {"signoff_sha256": h(so), "files_sha256": {"m1.lef": h(lef), "m1_tt.lib": h(lib)}}}
    (le / "provenance.json").write_text(json.dumps(prov))
    for n, b in (("signoff.json", so), ("m1.lef", lef), ("m1_tt.lib", lib), ("face_guard_source.py", bad_tool)):
        (le / n).write_bytes(b)
    (le / "manifest.json").write_text(json.dumps({"master": "m1", "sha256": {n: h((le / n).read_bytes()) for n in ("signoff.json", "m1.lef", "m1_tt.lib", "face_guard_source.py")}}))
    return v


class T(unittest.TestCase):
    def test_wrong_bytes_detected_then_staged_by_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = b"frozen tool", b"edited later"
            v = mk(tmp, good, bad)
            self.assertTrue(any("face_guard_source.py" in e for e in V.check(v)))   # w652-style wrong bytes
            nb = Path(tmp) / "neighbour"
            nb.mkdir()
            (nb / "face_guard_source.py").write_bytes(good)                          # right bytes live elsewhere
            (nb / "decoy.py").write_bytes(bad)
            self.assertEqual(V.stage(v, [str(nb)]), [])
            self.assertEqual((v / "landing_evidence" / "face_guard_source.py").read_bytes(), good)
            self.assertEqual(V.check(v), [])                                         # manifest refreshed

    def test_no_source_with_the_recorded_bytes_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            v = mk(tmp, b"frozen tool", b"edited later")
            nb = Path(tmp) / "only_bad"
            nb.mkdir()
            (nb / "face_guard.py").write_bytes(b"edited later")
            with self.assertRaises(SystemExit):
                V.stage(v, [str(nb)])
            self.assertEqual((v / "landing_evidence" / "face_guard_source.py").read_bytes(), b"edited later")   # nothing was touched


if __name__ == "__main__":
    unittest.main()
