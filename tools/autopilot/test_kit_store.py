#!/usr/bin/env python3
"""tests for kit_store.py (KIT-INPUT-STORE-1) and its opt-in kit_wave hook (no ssh: everything local in a tmp dir)"""
import json
import os
import shutil
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_store as KS  # noqa: E402
import kit_wave as KW  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="ks_")
        self.lanes = os.path.join(self.t, "srv", "scr", "claude")       # lane depth >= 5 like /srv/<scr>/claude/<lane>/x
        self._old = (KS.SCAN_PREFIX, KS.ROOT_FLOOR_GB, KS.SCRATCH_FLOOR_GB)
        KS.SCAN_PREFIX, KS.ROOT_FLOOR_GB, KS.SCRATCH_FLOOR_GB = os.path.join(self.t, "srv"), 0, 0
        self.store = os.path.join(self.t, "srv", "scr", "kit-store")
        L = self.lanes
        self.rtl = self.w(f"{L}/laneA/src/rtl/leaf.sv", "module leaf; endmodule\n", ro=True)
        self.rtl_w = self.w(f"{L}/laneA/src/rtl/leaf_w.sv", "module leaf_w; endmodule\n", ro=False)
        self.bind = f"{L}/laneB/bind9"
        self.w(f"{self.bind}/bind.f", f"{self.rtl}\n{self.rtl_w}\n", ro=True)
        self.w(f"{self.bind}/bind_report.json", json.dumps({"errors": 0}), ro=True)
        self.w(f"{self.bind}/rtl/bound.sv", "module bound; endmodule\n", ro=True)
        self.plan = self.w(f"{L}/laneC/plan_x/plan_c.json", json.dumps({"view": f"{L}/laneD/pv/a.lef", "dir": f"{L}/laneD"}))
        self.w(f"{L}/laneC/plan_x/die_io.json", "{}")
        self.w(f"{L}/laneC/plan_x/r8/kv_r8_landing.json", "{}")
        self.w(f"{L}/laneC/plan_x/deep/ignored.json", "{}")
        self.lef = self.w(f"{L}/laneD/pv/a.lef", "MACRO a\n", ro=True)
        self.asb = self.w(f"{L}/laneE/asbuilt.json", json.dumps({"base": f"{L}/laneA/src"}))
        self.script = self.w(f"{L}/laneF/kit_rtl.sh", f"export S81_BIND_OUT={self.bind}\nexport A={self.asb}\n"
                                                      f"cp {self.bind}/rtl/bound.sv $OUT/\n")
        self.kit = f"{L}/wave/items/t1/attempt_2"

    def tearDown(self):
        KS.SCAN_PREFIX, KS.ROOT_FLOOR_GB, KS.SCRATCH_FLOOR_GB = self._old
        for dp, dns, fns in os.walk(self.t):
            for n in dns + fns:
                try:
                    os.chmod(os.path.join(dp, n), 0o755, follow_symlinks=False)
                except OSError:
                    pass
        shutil.rmtree(self.t)

    def w(self, p, txt, ro=False):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(txt)
        if ro:
            os.chmod(p, 0o444)
        return p

    def spec(self):
        return {"inputs": [{"role": "plan", "path": self.plan, "kind": "file", "required": True, "siblings": ["r8"]},
                           {"role": "asbuilt", "path": self.asb, "kind": "file", "required": True, "siblings": []},
                           {"role": "bind_out", "path": self.bind, "kind": "dir", "required": True},
                           {"role": "kit_rtl_script", "path": self.script, "kind": "file", "required": True}],
                "rebuild": {"src_sha": "abc"}, "meta": {"die": "kv", "item": "t1", "attempt": "attempt_2"}}

    def snap(self, kit=None):
        return KS.snapshot(self.spec(), (kit or self.kit) + "/kit_inputs", self.store, log=lambda *a: None)


class Snapshot(Base):
    def test_self_contained_and_dedupe(self):
        m = self.snap()
        ki = self.kit + "/kit_inputs"
        for p in (self.plan, self.asb, self.bind, self.script):
            self.assertEqual(m["map"][p], ki + p)
        # bind.f sources and the plan's own neighbours (not deep/) are in the kit
        for p in (self.rtl, self.rtl_w, self.lef, self.plan.replace("plan_c.json", "die_io.json"),
                  self.plan.replace("plan_c.json", "r8/kv_r8_landing.json")):
            self.assertTrue(os.path.isfile(ki + p), p)
        self.assertFalse(os.path.exists(ki + self.plan.replace("plan_c.json", "deep/ignored.json")))
        # read-only source: one inode for source, blob and kit; writable source: copied, its mode untouched
        sha = m["files"][self.rtl]
        blob = os.path.join(self.store, "blobs", sha[:2], sha)
        self.assertEqual(os.stat(blob).st_ino, os.stat(self.rtl).st_ino)
        self.assertEqual(os.stat(ki + self.rtl).st_ino, os.stat(blob).st_ino)
        self.assertNotEqual(os.stat(self.rtl_w).st_ino, os.stat(ki + self.rtl_w).st_ino)
        self.assertTrue(os.stat(self.rtl_w).st_mode & stat.S_IWUSR)
        self.assertEqual(stat.S_IMODE(os.stat(ki + self.rtl_w).st_mode), 0o444)
        # identity json byte-identical, recipes rewritten to kit-local paths
        self.assertEqual(open(ki + self.plan, "rb").read(), open(self.plan, "rb").read())
        self.assertEqual(open(ki + self.asb, "rb").read(), open(self.asb, "rb").read())
        bf = open(ki + self.bind + "/bind.f").read()
        self.assertEqual(bf, f"{ki}{self.rtl}\n{ki}{self.rtl_w}\n")
        sh = open(ki + self.script).read()
        self.assertIn(f"S81_BIND_OUT={ki}{self.bind}\n", sh)
        self.assertIn(f"cp {ki}{self.bind}/rtl/bound.sv", sh)
        self.assertEqual(sorted(m["rewritten"]), sorted([self.bind + "/bind.f", self.script]))
        # data json names a dir: recorded absent, never copied
        self.assertTrue(any(a["path"] == f"{self.lanes}/laneD" for a in m["absent"]))
        # manifests: kit copy + store copy (retention)
        self.assertTrue(os.path.isfile(ki + "/MANIFEST.json"))
        self.assertEqual(len(os.listdir(os.path.join(self.store, "manifests"))), 1)
        # a second kit adds no bytes
        # a second kit adds only its own rewritten recipes (kit-local paths differ per kit)
        k3 = self.kit.replace("attempt_2", "attempt_3")
        m2 = self.snap(k3)
        self.assertEqual(m2["bytes_copied"], sum(os.path.getsize(k3 + "/kit_inputs" + f) for f in m2["rewritten"]))

    def test_restore_after_prune(self):
        self.snap()
        for d in (f"{self.lanes}/laneA", f"{self.lanes}/laneB"):      # cleanup removes the bind and source worktrees
            for dp, dns, fns in os.walk(d):
                os.chmod(dp, 0o755)
            shutil.rmtree(d)
        k2 = self.kit.replace("attempt_2", "attempt_3")
        m = self.snap(k2)
        self.assertIn(self.bind, m["restored"])
        self.assertIn(self.rtl, m["restored"])
        self.assertEqual(open(k2 + "/kit_inputs" + self.rtl).read(), "module leaf; endmodule\n")
        self.assertTrue(os.path.isfile(k2 + "/kit_inputs" + self.bind + "/rtl/bound.sv"))

    def test_required_missing_fails(self):
        sp = self.spec()
        sp["inputs"].append({"role": "plan", "path": f"{self.lanes}/gone/plan.json", "required": True})
        with self.assertRaises(KS.StoreError) as e:
            KS.snapshot(sp, self.kit + "/kit_inputs", self.store, log=lambda *a: None)
        self.assertIn("KIT-STORE MISSING", str(e.exception))

    def test_localize_filelist(self):
        self.snap()
        ki = self.kit + "/kit_inputs"
        inside = self.w(self.kit + "/rtl/wrap.sv", "module wrap; endmodule\n")
        other = self.w(f"{self.lanes}/laneG/x.sv", "module x; endmodule\n")
        fl = self.w(self.kit + "/rtl/kit_rtl.f", f"{inside}\n{ki}{self.rtl}\n{other}\n{self.lanes}/nope/y.sv\n")
        r = KS.localize_filelist(fl, self.kit, ki, self.store)
        self.assertEqual(r["n_moved"], 1)
        self.assertEqual(r["missing"], [f"{self.lanes}/nope/y.sv"])
        lines = open(fl).read().split()
        self.assertEqual(lines[:3], [inside, ki + self.rtl, ki + other])
        self.assertTrue(os.path.isfile(ki + other))
        self.assertTrue(os.path.isfile(fl + ".orig_paths"))


class Retention(Base):
    def test_referenced_set_rule(self):
        self.snap()
        sha = KS.snapshot(self.spec(), self.kit + "/kit_inputs", self.store, log=lambda *a: None)["files"][self.rtl_w]
        blob = os.path.join(self.store, "blobs", sha[:2], sha)
        # the kit links it: kept
        r = KS.gc(self.store, apply=True, log=lambda *a: None)
        self.assertTrue(os.path.exists(blob))
        shutil.rmtree(self.kit, ignore_errors=True)
        for dp, dns, fns in os.walk(self.kit):
            os.chmod(dp, 0o755)
        shutil.rmtree(self.kit, ignore_errors=True)
        self.assertEqual(os.stat(blob).st_nlink, 1)
        # no link, but a manifest of the window names it: kept
        KS.gc(self.store, apply=True, log=lambda *a: None)
        self.assertTrue(os.path.exists(blob))
        # manifests older than 14 days: an extra referenced list still keeps it; dry run deletes nothing
        old = time.time() - 15 * 86400
        md = os.path.join(self.store, "manifests")
        for n in os.listdir(md):
            os.utime(os.path.join(md, n), (old, old))
        KS.gc(self.store, extra={sha}, apply=True, log=lambda *a: None)
        self.assertTrue(os.path.exists(blob))
        r = KS.gc(self.store, apply=False, log=lambda *a: None)
        self.assertTrue(os.path.exists(blob))
        self.assertGreaterEqual(r["delete"], 1)
        r = KS.gc(self.store, apply=True, log=lambda *a: None)
        self.assertFalse(os.path.exists(blob))
        # read-only sources stay linked by their lane file: never deleted while that file exists
        s2 = KS.Store(self.store)
        self.assertTrue(os.path.exists(s2.blob(KS.sha256_file(self.rtl))))

    def test_unreadable_manifest_refuses(self):
        self.snap()
        with open(os.path.join(self.store, "manifests", "bad.json"), "w") as f:
            f.write("{")
        with self.assertRaises(KS.StoreError):
            KS.gc(self.store, apply=True, log=lambda *a: None)

    def test_du(self):
        self.snap()
        d = KS.du(self.store)
        self.assertGreater(d["blobs"], 0)
        # store-only = the original bytes of recipes the kit holds rewritten (kept by the manifest rule), nothing else
        self.assertLessEqual(d["store_only_blobs"], 2)


class WaveHook(unittest.TestCase):
    def cfg(self, **over):
        d = {"enabled": True, "event": "e1", "gate": {}, "plan": "/srv/p/plan_c.json", "gen_host": "intel1",
             "src": "/srv/wt/kw", "src_sha": "620077f42", "owner_lane": "X",
             "kit_rtl": {"mode": "bind", "asbuilt": "/srv/a/asb.json", "bind_out": "/srv/a/bind9"}}
        d.update(over)
        return {"enabled": True, "dies": {"qwen_kvsys": d}}

    def test_default_off_spec_unchanged(self):
        self.assertNotIn("kit_store", KW.spec_for(self.cfg(), "qwen_kvsys", "kv3_pc", "intel2"))
        self.assertTrue(KW.spec_for(self.cfg(kit_store=True), "qwen_kvsys", "kv3_pc", "intel2")["kit_store"])
        c = self.cfg()
        c["kit_store"] = True                            # global switch
        self.assertTrue(KW.spec_for(c, "qwen_kvsys", "kv3_pc", "intel2")["kit_store"])
        pil = self.cfg(kit_store=["kv3_pv*"])            # pilot: item patterns
        self.assertTrue(KW.spec_for(pil, "qwen_kvsys", "kv3_pv_v12", "intel2")["kit_store"])
        self.assertNotIn("kit_store", KW.spec_for(pil, "qwen_kvsys", "kv3_pc", "intel2"))
        self.assertNotIn("kit_store", KW.spec_for(self.cfg(kit_store=False), "qwen_kvsys", "kv3_pc", "intel2"))

    def test_map_and_inputs(self):
        mp = {"/srv/a/bind9": "/w/kit_inputs/srv/a/bind9", "/srv/p/plan_c.json": "/w/kit_inputs/srv/p/plan_c.json"}
        self.assertEqual(KW.ks_map("/srv/p/plan_c.json", mp), mp["/srv/p/plan_c.json"])
        self.assertEqual(KW.ks_map(["--x", "/srv/a/bind9/f.json", "/srv/a/bind90"], mp),
                         ["--x", "/w/kit_inputs/srv/a/bind9/f.json", "/srv/a/bind90"])
        self.assertEqual(KW.ks_map({"note": "/srv/a/bind9", "bind_out": "/srv/a/bind9"}, mp),
                         {"note": "/srv/a/bind9", "bind_out": "/w/kit_inputs/srv/a/bind9"})
        sp = {"kit_rtl": {"mode": "bind", "asbuilt": "/srv/a/asb.json", "bind_out": "/srv/a/bind9"},
              "gen_args": ["--clock-landing", "/srv/s/side.json"], "gen_env": {"OT_X": "1"}}
        roles = {(i["role"], i["path"]) for i in KW.ks_inputs(sp, "/srv/p/plan_c.json")}
        self.assertEqual(roles, {("plan", "/srv/p/plan_c.json"), ("asbuilt", "/srv/a/asb.json"),
                                 ("bind_out", "/srv/a/bind9"), ("gen_args", "/srv/s/side.json")})
        self.assertTrue(KW.kit_store_applies(sp))
        self.assertFalse(KW.kit_store_applies({"kit_rtl": {"mode": "bind", "asbuilt": "/a"}}))
        self.assertFalse(KW.kit_store_applies({"kind": "core", "core_kit": {"gen_cmd": "x"}, "kit_rtl": {}}))

    def test_ks_cmd_runs_store_source(self):
        self.assertIn("def snapshot(", KW.ks_cmd("du --store-root /x"))


if __name__ == "__main__":
    unittest.main()
