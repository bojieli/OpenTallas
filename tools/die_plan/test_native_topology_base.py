import ast
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kit_topology


class NativeBaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = self.root / "physical" / "plans" / "plan.json"
        self.plan.parent.mkdir(parents=True)
        self.manifest = self.root / "manifests" / "asbuilt.json"
        self.manifest.parent.mkdir()
        self.native = self.root / "native"
        self.native.mkdir()
        (self.native / "landing.json").write_text('{"collector":{"types":{}}}')
        tree = ast.parse(Path(kit_topology.__file__).with_name("bind.py").read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "plan_base")
        self.scope = {"Path": Path, "_AB_OVERRIDE": {}, "E": types.SimpleNamespace(REPO=self.root)}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "bind.plan_base", "exec"), self.scope)

    def check_base(self, ab, explicit):
        raw = {"partition_types": {"t": {"buses": []}}, "asbuilt": ab}
        self.manifest.write_text(json.dumps(ab))
        self.scope["_AB_OVERRIDE"] = {"path": str(self.manifest)} if explicit else {}
        expected = self.scope["plan_base"](str(self.plan), raw)
        absolute = dict(raw, asbuilt=dict(ab, base=expected))
        actual = kit_topology.native_contract(raw, self.manifest if explicit else None, self.plan)
        self.assertEqual(actual, kit_topology.native_contract(absolute, plan_path=self.plan))
        return raw

    def test_explicit_manifest_relative_base(self):
        self.check_base({"base": "../native", "clock_landing_table": "landing.json"}, True)

    def test_inline_base_stays_plan_relative(self):
        self.check_base({"base": "../../native", "clock_landing_table": "landing.json"}, False)

    def test_absolute_manifest_base(self):
        self.check_base({"base": str(self.native), "clock_landing_table": "landing.json"}, True)

    def test_external_clock_table_still_refused(self):
        outside = self.root / "outside.json"
        outside.write_text("{}")
        raw = {"partition_types": {}, "asbuilt": {}}
        self.manifest.write_text(json.dumps({"base": "../native", "clock_landing_table": "../outside.json"}))
        with self.assertRaisesRegex(ValueError, "inside its declared native base"):
            kit_topology.native_contract(raw, self.manifest, self.plan)

    def test_absolute_live_table_reroots_into_snapshot(self):
        live = self.root / "srv" / "tree"
        snap = self.root / "snaps" / "abc" / "root"
        mirror = snap / live.relative_to(live.anchor)
        (mirror / "runtime").mkdir(parents=True)
        (mirror / "runtime" / "landing.json").write_text('{"collector":{"types":{}}}')
        live_table = live / "runtime" / "landing.json"          # absolute live path, as the iso manifests write it
        raw = {"partition_types": {"t": {"buses": []}}, "asbuilt": {}}
        self.manifest.write_text(json.dumps({"base": str(mirror), "clock_landing_table": str(live_table)}))
        got = kit_topology.native_contract(raw, self.manifest, self.plan)
        self.assertIsNotNone(got["clock_table_sha256"])
        self.manifest.write_text(json.dumps({"base": str(mirror), "clock_landing_table": "runtime/landing.json"}))
        self.assertEqual(got, kit_topology.native_contract(raw, self.manifest, self.plan))

    def test_absolute_table_without_snapshot_copy_still_refused(self):
        outside = self.root / "elsewhere" / "landing.json"
        outside.parent.mkdir()
        outside.write_text("{}")
        self.manifest.write_text(json.dumps({"base": str(self.native), "clock_landing_table": str(outside)}))
        with self.assertRaisesRegex(ValueError, "inside its declared native base"):
            kit_topology.native_contract({"partition_types": {}, "asbuilt": {}}, self.manifest, self.plan)


if __name__ == "__main__":
    unittest.main()
