import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import qc_guard_revalidate as G


def put(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=1) + "\n")
    return str(p)


class ManifestGuardRelocation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        r = Path(self.tmp.name)
        old, new = r / "old", r / "new"
        for root in (old, new):
            (root / "runtime").mkdir(parents=True)
            (root / "rtl").mkdir()
            (root / "map.json").write_text('{"instance":"p"}\n')
            for name in ("a", "b"):
                (root / "rtl" / (name + ".sv")).write_text("module " + name + "; endmodule\n")
            for i, name in enumerate(("side", "r8", "extra0", "extra1")):
                put(root / "runtime" / (name + ".json"), {"table": i})
        cm = {"p": {"src": "core"}}
        base = dict(base="..", top="die", files=["rtl/a.sv", "rtl/b.sv"],
                    map_file="../map.json", clock_landing_table="runtime/base_side.json",
                    land_r8="runtime/base_r8.json", land_r8_extra=[])
        original = put(old / "runtime/base.json", base)
        before = dict(base, clock_merge=cm, kit_source_station_pricing=True)
        mb = put(old / "runtime/composed.json", before)
        refs = [str(old / "runtime" / (n + ".json")) for n in ("side", "r8", "extra0", "extra1")]
        q = dict(before, clock_landing_table=refs[0], land_r8=refs[1], land_r8_extra=refs[2:])
        qualified = put(r / "qualified_copy.json", q)
        nq = dict(q, clock_landing_table="runtime/side.json", land_r8="runtime/r8.json",
                  land_r8_extra=["runtime/extra0.json", "runtime/extra1.json"])
        nm = put(new / "runtime/qualified.json", nq)
        receipt = dict(source_manifest=mb, source_sha256=G.sha(mb),
                       isolated_manifest=str(old / "runtime/qualified.json"),
                       isolated_sha256=G.sha(qualified), sidecar=refs[0], r8=refs[1],
                       sidecar_sha256=G.sha(refs[0]), r8_sha256=G.sha(refs[1]),
                       extra_override_spec="recorded", extra_tables=[
                           dict(copy=p, sha256=G.sha(p)) for p in refs[2:]])
        sources = [str(old / "rtl" / (n + ".sv")) for n in ("a", "b")]
        source_map = [dict(original=p, packaged=str(new / Path(p).relative_to(old)), sha256=G.sha(p))
                      for p in sources]
        assets = dict(asset_count=4, assets=[dict(source=p, copy=p, sha256=G.sha(p)) for p in refs])
        self.spec = dict(old_guard=put(r / "old_cm.json", dict(schema="opentallas.qc_clock_merge.v1",
                         clock_merge=cm, manifest_sha256=G.sha(original))),
                         old_kp_guard=put(r / "old_kp.json", dict(kit_source_station_pricing=True,
                                                              manifest_sha256=G.sha(original))),
                         original_manifest=original, source_manifest=mb, qualified_manifest=qualified,
                         isolation_receipt=put(r / "isolated.json", receipt),
                         new_manifest=nm, old_root=str(old), new_root=str(new),
                         selected_source_map=put(r / "source_map.json", source_map),
                         source_inventory=put(r / "sources.json", dict(full=sources, lib=[])),
                         runtime_assets=put(r / "assets.json", assets))
        self.r, self.old, self.new = r, old, new

    def mutate(self, key, update):
        p = Path(self.spec[key])
        d = G.read(p)
        update(d)
        put(p, d)

    def test_exact_relocation_accepts_all_selected_sources_and_runtime(self):
        p = G.validate(self.spec)
        self.assertEqual((p["selected_source_count"], p["runtime_asset_count"]), (2, 4))

    def test_original_guard_hash_cannot_be_swapped(self):
        self.mutate("old_guard", lambda d: d.update(manifest_sha256="0" * 64))
        with self.assertRaisesRegex(ValueError, "old CM guard"):
            G.validate(self.spec)

    def test_selected_payload_change_rejected(self):
        (self.new / "rtl/a.sv").write_text("module wrong; endmodule\n")
        with self.assertRaisesRegex(ValueError, "selected source payload"):
            G.validate(self.spec)

    def test_missing_selected_source_rejected(self):
        p = Path(self.spec["selected_source_map"])
        put(p, G.read(p)[:1])
        with self.assertRaisesRegex(ValueError, "source omitted"):
            G.validate(self.spec)

    def test_changed_map_rejected(self):
        (self.new / "map.json").write_text('{"instance":"other"}\n')
        with self.assertRaisesRegex(ValueError, "map bytes"):
            G.validate(self.spec)

    def test_changed_runtime_extra_rejected(self):
        put(self.new / "runtime/extra1.json", {"table": 99})
        with self.assertRaisesRegex(ValueError, "runtime asset payload"):
            G.validate(self.spec)

    def test_unrecorded_recipe_change_rejected(self):
        self.mutate("new_manifest", lambda d: d.update(type_canon=True))
        with self.assertRaisesRegex(ValueError, "manifest semantics"):
            G.validate(self.spec)

    def test_changed_clock_domain_map_rejected(self):
        self.mutate("new_manifest", lambda d: d.update(clock_merge={"p": {"src": "other"}}))
        with self.assertRaisesRegex(ValueError, "CM/KP semantics"):
            G.validate(self.spec)

    def test_failed_isolation_chain_rejected(self):
        self.mutate("isolation_receipt", lambda d: d.update(source_sha256="f" * 64))
        with self.assertRaisesRegex(ValueError, "source hash mismatch"):
            G.validate(self.spec)


if __name__ == "__main__":
    unittest.main()

