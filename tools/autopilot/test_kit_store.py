"""kit_store (KIT-INPUT-STORE-1, COORD 11-10): self-contained kit inputs backed by a per-host dedupe store, and the kit_wave option that turns it on."""
import json
import os
import sys
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_store as KS   # noqa: E402


def put(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(data)
    return p


class Store(unittest.TestCase):
    def setUp(self):
        self.t = os.path.realpath(tempfile.mkdtemp(prefix="kst"))
        self.root = os.path.join(self.t, "scratch/kit-store")
        self.lane = os.path.join(self.t, "scratch/claude/lane1")

    def snap(self, paths, **kw):
        spec = {"inputs": [{"role": "plan", "path": p, "kind": "file", "required": True} for p in paths]}
        ki = os.path.join(self.t, f"kit{kw.get('n', 1)}/kit_inputs")
        return KS.snapshot(spec, ki, store_root=self.root, log=lambda *a: None), ki

    def test_snapshot_makes_a_kit_local_copy_and_one_readonly_blob_per_content(self):
        a = put(os.path.join(self.lane, "a/plan.json"), '{"x": 1}')
        b = put(os.path.join(self.lane, "b/plan_copy.json"), '{"x": 1}')          # same content
        man, ki = self.snap([a, b])
        for p in (a, b):
            self.assertEqual(open(ki + p).read(), '{"x": 1}')                       # kit-local path = kit_inputs + original abs path
        blobs = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(self.root, "blobs")) for f in fs]
        self.assertEqual(len(blobs), 1)                                              # deduped
        self.assertEqual(os.stat(blobs[0]).st_mode & 0o222, 0)                      # read-only inode
        self.assertTrue(os.path.exists(os.path.join(ki, "MANIFEST.json")))
        self.assertEqual(man["map"][a], ki + a)

    def test_pruned_original_is_restored_from_the_store(self):
        a = put(os.path.join(self.lane, "a/plan.json"), '{"x": 2}')
        self.snap([a], n=1)
        os.unlink(a)                                                                 # cleanup prunes the lane worktree
        man, ki = self.snap([a], n=2)
        self.assertEqual(open(ki + a).read(), '{"x": 2}')
        self.assertTrue(man.get("restored"), man)

    def test_gc_dry_run_deletes_nothing_and_apply_follows_the_referenced_set_rule(self):
        st = KS.Store(self.root)
        sha_free = st.put_bytes(b"unreferenced")
        sha_man = st.put_bytes(b"named by a launch manifest")
        sha_link = st.put_bytes(b"hardlinked into a kit")
        st.commit()
        kit = os.path.join(self.t, "kit/f")
        os.makedirs(os.path.dirname(kit))
        os.link(os.path.join(self.root, "blobs", sha_link[:2], sha_link), kit)       # a live kit holds it (st_nlink > 1)
        with open(os.path.join(self.root, "manifests", "m1.json"), "w") as f:
            json.dump({"shas": [sha_man]}, f)
        dry = KS.gc(self.root, apply=False, log=lambda *a: None)
        self.assertEqual((dry["delete"], dry["kept_linked"], dry["kept_manifest"]), (1, 1, 1))
        for s in (sha_free, sha_man, sha_link):
            self.assertTrue(os.path.exists(os.path.join(self.root, "blobs", s[:2], s)))   # dry run touched nothing
        done = KS.gc(self.root, apply=True, log=lambda *a: None)
        self.assertEqual(done["delete"], 1)
        self.assertFalse(os.path.exists(os.path.join(self.root, "blobs", sha_free[:2], sha_free)))
        self.assertTrue(os.path.exists(os.path.join(self.root, "blobs", sha_man[:2], sha_man)))
        self.assertTrue(os.path.exists(os.path.join(self.root, "blobs", sha_link[:2], sha_link)))

    def test_gc_refuses_on_an_unreadable_manifest(self):
        KS.Store(self.root).commit()
        with open(os.path.join(self.root, "manifests", "bad.json"), "w") as f:
            f.write("{not json")
        with self.assertRaises(KS.StoreError):
            KS.gc(self.root, apply=True, log=lambda *a: None)

    def test_expired_manifest_no_longer_protects(self):
        st = KS.Store(self.root)
        sha = st.put_bytes(b"old manifest content")
        st.commit()
        m = os.path.join(self.root, "manifests", "old.json")
        with open(m, "w") as f:
            json.dump({"shas": [sha]}, f)
        old = time.time() - (KS.KEEP_DAYS + 1) * 86400
        os.utime(m, (old, old))
        out = KS.gc(self.root, apply=False, log=lambda *a: None)
        self.assertEqual(out["delete"], 1)


class InPlaceSrc(unittest.TestCase):
    """KIT-STAGE-1 11-13: KV kv3_pv x15 failed kit_rtl 'preferred HDL source missing: <kit_inputs>/<src>/rtl/...': the plan and
    as-built live in the wave src, were moved into the kit, and the bind resolved tree-relative files against the moved copy"""

    def setUp(self):
        self.t = os.path.realpath(tempfile.mkdtemp(prefix="kst"))
        self.old = KS.SCAN_PREFIX
        KS.SCAN_PREFIX = self.t
        self.root = os.path.join(self.t, "scratch/kit-store")
        self.src = os.path.join(self.t, "scratch/claude/kw45/src_kv_main_abc")
        self.lane = os.path.join(self.t, "scratch/claude/kit-ops-1/kvbind")

    def tearDown(self):
        KS.SCAN_PREFIX = self.old

    def test_src_inputs_stay_in_place_outside_inputs_move_in(self):
        plan = put(os.path.join(self.src, "physical/die_plan/kv/plan_c.json"), '{"p": 1}')
        ab = put(os.path.join(self.src, "physical/die_plan/kv/asbuilt.json"), '{"base": "x", "files": ["rtl/a.sv"]}')
        sv = put(os.path.join(self.src, "rtl/a.sv"), "module a; endmodule\n")
        ext = put(os.path.join(self.t, "scratch/claude/other-lane/views/b.sv"), "module b; endmodule\n")
        put(os.path.join(self.lane, "out/bind_report.json"), '{"errors": []}')
        put(os.path.join(self.lane, "out/bind.f"), sv + "\n" + ext + "\n")
        spec = {"in_place": [self.src], "inputs": [
            {"role": "plan", "path": plan, "kind": "file", "required": True, "siblings": ["r8"]},
            {"role": "asbuilt", "path": ab, "kind": "file", "required": True, "siblings": []},
            {"role": "bind_out", "path": os.path.join(self.lane, "out"), "kind": "dir", "required": True}]}
        ki = os.path.join(self.t, "kit/kit_inputs")
        man = KS.snapshot(spec, ki, store_root=self.root, log=lambda *a: None)
        self.assertNotIn(plan, man["map"])                    # read where it is: tree-relative files resolve in the src
        self.assertNotIn(ab, man["map"])
        self.assertIn(plan, man["in_place"])
        self.assertIn(sv, man["in_place"])
        self.assertEqual(len(man["in_place"][sv]), 64)        # recorded by content sha
        self.assertIn(ext, man["map"])                        # outside the src: copied into the kit
        bf = open(ki + os.path.join(self.lane, "out/bind.f")).read().split()
        self.assertEqual(bf, [sv, ki + ext])                  # the src line kept, the lane line kit-local
        self.assertTrue(os.path.exists(ki + ext))


class KitWaveOption(unittest.TestCase):
    def setUp(self):
        self.K = SourceFileLoader("kw_ks", str(HERE / "kit_wave.py")).load_module()

    def cfg(self, v, die=True):
        return {"dies": {"hbm": ({"kit_store": v} if die else {})}, **({} if die else {"kit_store": v})}

    def test_off_by_default(self):
        self.assertFalse(self.K.kit_store_on({"dies": {"hbm": {}}}, "hbm", "x"))

    def test_true_means_every_item(self):
        self.assertTrue(self.K.kit_store_on(self.cfg(True), "hbm", "anything"))

    def test_list_is_an_fnmatch_pilot(self):
        c = self.cfg(["kv3_pv_*", "hd_ctl"])
        self.assertTrue(self.K.kit_store_on(c, "hbm", "kv3_pv_v1"))
        self.assertTrue(self.K.kit_store_on(c, "hbm", "hd_ctl"))
        self.assertFalse(self.K.kit_store_on(c, "hbm", "q_b101"))


if __name__ == "__main__":
    unittest.main()
