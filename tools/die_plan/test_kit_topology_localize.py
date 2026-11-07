"""kit-rtl can leave a bound module at the bind output; the wave's prepare-stations must localize it (QC sle_fe_v2)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import kit_topology as K


def kit(root, local_name=None):
    bind = root / "bind" / "rtl"; bind.mkdir(parents=True)
    src = bind / "m__v.sv"; src.write_text("module m__v; endmodule\n")
    other = bind / "bind_cells.sv"; other.write_text("// cells\n")
    kd = root / "kit"; kd.mkdir()
    wrap = kd / "m.sv"; wrap.write_text("module m; m__v u_bound(); endmodule\n")
    files = [str(wrap), str(src), str(other)]
    (kd / "kit_rtl.json").write_text(json.dumps(dict(files=files, bound_module="m__v", plan_type="v")))
    for n in ("kit_rtl.f", "kit_rtl_sim.f"):
        (kd / n).write_text("\n".join(files) + "\n")
    if local_name:
        (kd / local_name).write_text("// something else\n")
    return kd, src, other


class LocalizeBound(unittest.TestCase):
    def test_copies_same_bytes_and_repoints_only_the_bound_file(self):
        with TemporaryDirectory() as d:
            kd, src, other = kit(Path(d))
            before = src.read_bytes()
            local = K.localize_bound(kd)
            self.assertEqual(local, kd / "m__v.sv")
            self.assertEqual(local.read_bytes(), before)
            self.assertEqual(src.read_bytes(), before)
            man = json.loads((kd / "kit_rtl.json").read_text())
            self.assertEqual(man["files"], [str(kd / "m.sv"), str(local), str(other)])
            for n in ("kit_rtl.f", "kit_rtl_sim.f"):
                self.assertEqual((kd / n).read_text().split(), man["files"])

    def test_second_run_is_a_no_op(self):
        with TemporaryDirectory() as d:
            kd, _, _ = kit(Path(d))
            K.localize_bound(kd)
            snap = {p.name: p.read_bytes() for p in kd.iterdir()}
            self.assertIsNone(K.localize_bound(kd))
            self.assertEqual(snap, {p.name: p.read_bytes() for p in kd.iterdir()})

    def test_different_local_file_refuses_and_changes_nothing(self):
        with TemporaryDirectory() as d:
            kd, _, _ = kit(Path(d), "m__v.sv")
            old = (kd / "kit_rtl.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "KIT_TOPOLOGY_REGENERATE"):
                K.localize_bound(kd)
            self.assertEqual((kd / "kit_rtl.json").read_bytes(), old)
            self.assertEqual((kd / "m__v.sv").read_text(), "// something else\n")


if __name__ == "__main__":
    unittest.main()
