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


if __name__ == "__main__":
    unittest.main()
