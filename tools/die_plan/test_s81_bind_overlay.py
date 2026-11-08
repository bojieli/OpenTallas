"""S81 kit_rtl bind overlay in a re-used attempt dir (KW6-CLASS 11-04: iqf__t1 a4, serdes__t15__cla3d02796 a2,
slice_station__t7__cl503f4913 a8 "rtl_bindov/asbuilt.json exists and is not a link")."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "image_params", Path(__file__).resolve().parents[2] / "physical/die_plan/s81/kit_wave/image_params.py")
IP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IP)


def bind(root, name):
    out = root / name
    out.mkdir()
    (out / "asbuilt.json").write_text("{}")
    (out / "bind.f").write_text("")
    (out / "bind_report.json").write_text(json.dumps({"errors": 0}))
    return out


class Overlay(unittest.TestCase):
    def test_link_to_an_older_bind_is_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old, new, ov = bind(root, "bind_old"), bind(root, "bind_new"), root / "ov"
            (old / "only_old.txt").write_text("x")
            IP.overlay(old, root, ov)
            IP.overlay(new, root, ov)
            self.assertEqual((ov / "asbuilt.json").resolve(), (new / "asbuilt.json").resolve())
            self.assertFalse((ov / "only_old.txt").is_symlink())

    def test_real_file_still_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            new, ov = bind(root, "bind_new"), root / "ov"
            ov.mkdir()
            (ov / "asbuilt.json").write_text("real")
            with self.assertRaisesRegex(IP.KitError, "not a link"):
                IP.overlay(new, root, ov)


class Follow(unittest.TestCase):
    """S81-TYPES-9-LEC 11-08: S81_LEAF_FOLLOW takes a listed leaf file from the wave source, nothing else."""

    def setup(self, root, new_text="module m (input a); endmodule\n"):
        base, src, out = root / "base", root / "src", root / "out"
        for d in (base / "rtl", src / "rtl", out):
            d.mkdir(parents=True)
        (base / "rtl" / "x.sv").write_text("module m (input a); /* old */ endmodule\n")
        (base / "rtl" / "y.sv").write_text("module n; endmodule\n")
        (src / "rtl" / "x.sv").write_text(new_text)
        (src / "rtl" / "y.sv").write_text("module n; /* newer, not listed */ endmodule\n")
        files = [str(base / "rtl" / "x.sv"), str(base / "rtl" / "y.sv")]
        (out / "kit_rtl.f").write_text("\n".join(files) + "\n")
        (out / "kit_rtl_sim.f").write_text("\n".join(files) + "\n")
        (out / "kit_rtl.json").write_text(json.dumps({"unindexed_sources": {"m": files[0], "n": files[1]}}))
        return base, src, out

    def test_listed_file_follows_the_wave_source(self):
        with tempfile.TemporaryDirectory() as td:
            base, src, out = self.setup(Path(td))
            res = IP.follow(out, src, ["rtl/x.sv", "rtl/not_in_this_type.sv"])
            self.assertEqual(res["followed"], 1)
            for fl in ("kit_rtl.f", "kit_rtl_sim.f"):
                self.assertEqual((out / fl).read_text().split(),
                                 [str((src / "rtl" / "x.sv").resolve()), str(base / "rtl" / "y.sv")])
            r = json.loads((out / "kit_rtl.json").read_text())
            self.assertEqual(r["unindexed_sources"]["m"], str((src / "rtl" / "x.sv").resolve()))
            self.assertEqual(r["unindexed_sources"]["n"], str(base / "rtl" / "y.sv"))
            (row,) = r["leaf_follow"]["files"]
            self.assertEqual((row["file"], row["was"]), ("rtl/x.sv", str(base / "rtl" / "x.sv")))
            self.assertNotEqual(row["was_sha256"], row["now_sha256"])

    def test_module_set_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            base, src, out = self.setup(Path(td), new_text="module m2 (input a); endmodule\n")
            before = (out / "kit_rtl.f").read_text()
            with self.assertRaisesRegex(IP.KitError, "defines"):
                IP.follow(out, src, ["rtl/x.sv"])
            self.assertEqual((out / "kit_rtl.f").read_text(), before)

    def test_missing_in_wave_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            base, src, out = self.setup(Path(td))
            (src / "rtl" / "x.sv").unlink()
            with self.assertRaisesRegex(IP.KitError, "not in"):
                IP.follow(out, src, ["rtl/x.sv"])


if __name__ == "__main__":
    unittest.main()
