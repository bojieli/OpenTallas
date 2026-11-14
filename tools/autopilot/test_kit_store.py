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


class Snap(unittest.TestCase):
    """KIT-FIX-F 11-13 (option kit_snap): one content-addressed, sha256-verified snapshot per input closure"""

    def setUp(self):
        self.t = os.path.realpath(tempfile.mkdtemp(prefix="ksn"))
        self.old = KS.SCAN_PREFIX
        KS.SCAN_PREFIX = self.t
        self.snaps = os.path.join(self.t, "scratch/kit-store/snaps")
        self.src = os.path.join(self.t, "scratch/claude/kw45/src_kv_main_abc")
        self.lane = os.path.join(self.t, "scratch/claude/kit-ops-1/kvbind")
        self.plan = put(os.path.join(self.src, "physical/die_plan/kv/plan_c.json"), '{"p": 1}')
        self.sv = put(os.path.join(self.src, "rtl/a.sv"), "module a; endmodule\n")
        self.ext = put(os.path.join(self.t, "scratch/claude/other-lane/views/b.sv"), "module b; endmodule\n")
        put(os.path.join(self.lane, "out/bind_report.json"), '{"errors": []}')
        put(os.path.join(self.lane, "out/bind.f"), self.sv + "\n" + self.ext + "\n")

    def tearDown(self):
        KS.SCAN_PREFIX = self.old

    def spec(self, extra=()):
        return {"in_place": [self.src], "inputs": [
            {"role": "plan", "path": self.plan, "kind": "file", "required": True, "siblings": ["r8"]},
            {"role": "bind_out", "path": os.path.join(self.lane, "out"), "kind": "dir", "required": True}] + list(extra)}

    def snap(self, **kw):
        return KS.snap(self.spec(**kw), self.snaps, log=lambda *a: None)

    def test_same_inputs_give_one_snapshot_and_the_second_item_reuses_it(self):
        a = self.snap()
        b = self.snap()
        self.assertEqual(a["id"], b["id"])
        self.assertFalse(a["reused"])
        self.assertTrue(b["reused"])
        self.assertEqual(len([n for n in os.listdir(self.snaps) if os.path.isdir(os.path.join(self.snaps, n))
                              and not n.startswith(".")]), 1)
        self.assertEqual(a["dir"], os.path.join(self.snaps, a["id"]))
        self.assertTrue(os.path.exists(os.path.join(a["dir"], ".verified")))
        man = json.load(open(os.path.join(a["dir"], "MANIFEST.json")))
        self.assertEqual(man["snap_id"], a["id"])
        self.assertEqual(len(man["files"][self.ext]), 64)                 # sha256 per file
        self.assertEqual(a["map"][self.ext], a["kit_inputs"] + self.ext)   # readers get the snapshot path
        bf = Path(a["kit_inputs"] + os.path.join(self.lane, "out/bind.f")).read_text().split()
        self.assertEqual(bf, [self.sv, a["kit_inputs"] + self.ext])       # src line in place, lane line inside the snapshot

    def test_changed_content_is_a_new_snapshot_and_the_old_one_is_untouched(self):
        a = self.snap()
        put(self.ext, "module b; wire x; endmodule\n")
        b = self.snap()
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual(Path(a["kit_inputs"] + self.ext).read_text(), "module b; endmodule\n")
        self.assertEqual(Path(b["kit_inputs"] + self.ext).read_text(), "module b; wire x; endmodule\n")

    def test_changed_file_in_the_pinned_src_tree_changes_the_id(self):
        a = self.snap()
        put(self.plan, '{"p": 2}')
        self.assertNotEqual(a["id"], self.snap()["id"])

    def test_missing_required_input_fails_fast_and_names_it(self):
        gone = os.path.join(self.t, "scratch/claude/pruned-lane/x/asbuilt.json")
        with self.assertRaises(KS.StoreError) as e:
            self.snap(extra=[{"role": "asbuilt", "path": gone, "kind": "file", "required": True}])
        self.assertIn("KIT-STORE MISSING asbuilt " + gone, str(e.exception))
        self.assertEqual([n for n in os.listdir(self.snaps) if re_hex(n)], [])   # nothing half-built is left as a snapshot

    def test_pruned_original_is_served_from_the_snapshot_store(self):
        a = self.snap()
        os.unlink(self.ext)                                                # cleanup deletes the lane file
        b = self.snap()
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(Path(b["kit_inputs"] + self.ext).read_text(), "module b; endmodule\n")

    def test_verify_rejects_a_corrupt_copy_and_removes_the_marker(self):
        a = self.snap()
        f = a["kit_inputs"] + self.ext
        os.unlink(f)                                                       # a bad copy on another host (not the shared inode)
        put(f, "module b; /* corrupt */ endmodule\n")
        with self.assertRaises(KS.StoreError) as e:
            KS.verify(a["dir"])
        self.assertIn("differ from the manifest", str(e.exception))
        self.assertFalse(os.path.exists(os.path.join(a["dir"], ".verified")))
        b = self.snap()                                                    # no marker: the next item rebuilds it in place
        self.assertFalse(b["reused"])
        self.assertEqual(Path(f).read_text(), "module b; endmodule\n")

    def test_verify_refuses_a_snapshot_at_another_path(self):
        a = self.snap()
        moved = os.path.join(self.t, "elsewhere", a["id"])
        os.makedirs(os.path.dirname(moved))
        os.rename(a["dir"], moved)
        with self.assertRaises(KS.StoreError) as e:
            KS.verify(moved)
        self.assertIn("same absolute path", str(e.exception))

    def test_tree_takes_the_plan_directory_whole_and_a_large_one_stays_flat(self):
        """HEAD hd_spn canary: the kit_rtl script reads <plan dir>/native_domains/... by relative path"""
        prep = os.path.join(self.t, "scratch/claude/kit-ops-1/head/prep")
        plan = put(os.path.join(prep, "source_plan.json"), '{"h": 1}')
        nd = put(os.path.join(prep, "native_domains/parent_clock_contract.json"), '{"c": 1}')
        spec = {"inputs": [{"role": "plan", "path": plan, "kind": "file", "required": True, "siblings": ["r8"], "tree": True}]}
        a = KS.snap(spec, self.snaps, log=lambda *x: None)
        self.assertEqual(Path(a["kit_inputs"] + nd).read_text(), '{"c": 1}')
        self.assertEqual(a["map"][prep], a["kit_inputs"] + prep)
        old = KS.TREE_MAX_BYTES
        KS.TREE_MAX_BYTES = 4                                              # the directory is now "large"
        try:
            b = KS.snap(spec, self.snaps, log=lambda *x: None)
        finally:
            KS.TREE_MAX_BYTES = old
        self.assertFalse(os.path.exists(b["kit_inputs"] + nd))             # flat rule: own files + named subdirs only
        self.assertTrue(os.path.exists(b["kit_inputs"] + plan))
        spec["inputs"][0].pop("tree")                                      # kit_store (flag off) keeps its flat rule
        ki = os.path.join(self.t, "kitx/kit_inputs")
        KS.snapshot(spec, ki, store_root=os.path.dirname(self.snaps), log=lambda *x: None)
        self.assertFalse(os.path.exists(ki + nd))

    def test_snap_gc_deletes_only_snapshots_unused_past_the_window(self):
        a = self.snap()
        self.assertEqual(KS.snap_gc(self.snaps, apply=True, log=lambda *x: None)["delete"], 0)
        late = time.time() + 15 * 86400
        self.assertEqual(KS.snap_gc(self.snaps, now=late, log=lambda *x: None)["delete"], 1)     # dry run
        self.assertTrue(os.path.isdir(a["dir"]))
        KS.snap_gc(self.snaps, apply=True, now=late, log=lambda *x: None)
        self.assertFalse(os.path.exists(a["dir"]))


def re_hex(n):
    import re
    return re.fullmatch(r"[0-9a-f]{40}", n)


class KitWaveSnap(unittest.TestCase):
    def setUp(self):
        self.K = SourceFileLoader("kw_ksn", str(HERE / "kit_wave.py")).load_module()
        self.t = os.path.realpath(tempfile.mkdtemp(prefix="kwsn"))
        self.old = KS.SCAN_PREFIX
        self.lane = os.path.join(self.t, "scratch/claude/lane")
        self.plan = put(os.path.join(self.lane, "p/plan.json"), '{"p": 1}')
        self.sp = {"die": "kv", "item": "kv3_pv_v1", "plan": self.plan, "src": "", "hosts": ["g1", "h2", "h3"],
                   "kit_rtl": {"mode": "bind", "asbuilt": "", "bind_out": ""}}
        self.W = os.path.join(self.t, "scratch/claude/wave/items/kv3_pv_v1/attempt_2")
        self.K.snap_root_of = lambda W: os.path.join(self.t, "scratch/kit-store/snaps")
        self.calls = []

    def local(self, argv):
        import subprocess
        import shlex
        cmd = argv[-1] if argv[0] != "ssh" else shlex.split(argv[-1])[2]   # ssh host "bash -c '<cmd>'"
        p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def stage(self, answers):
        """answers: stage -> 'real' (run the command here) or (rc, text)"""
        def run(stage, argv, timeout=None, idempotent=False):
            self.calls.append((stage, argv))
            a = answers.get(stage, "real")
            return self.local(argv) if a == "real" else a
        res = {}
        mp, why = self.K.kit_snap_stage(self.sp, run, lambda cmd: ["bash", "-c", cmd], res, self.W, self.plan, "g1", "hub")
        return mp, why, res

    def test_option_is_off_by_default_and_follows_the_kit_store_forms(self):
        K = self.K
        self.assertFalse(K.kit_snap_on({"dies": {"kv": {}}}, "kv", "x"))
        self.assertTrue(K.kit_snap_on({"dies": {"kv": {"kit_snap": True}}}, "kv", "x"))
        self.assertTrue(K.kit_snap_on({"kit_snap": ["kv3_pv*"], "dies": {"kv": {}}}, "kv", "kv3_pv_v8"))
        self.assertFalse(K.kit_snap_on({"kit_snap": ["kv3_pv*"], "dies": {"kv": {}}}, "kv", "kv3_phy"))

    def test_snapshot_on_the_gen_host_maps_the_plan_into_the_snapshot(self):
        mp, why, res = self.stage({})
        self.assertEqual(why, "")
        self.assertTrue(mp[self.plan].endswith("/root" + self.plan))
        self.assertEqual(Path(mp[self.plan]).read_text(), '{"p": 1}')
        self.assertEqual([c[0] for c in self.calls], ["kit_snap"])
        self.assertEqual(len(res["kit_snap"]["id"]), 40)

    def test_input_missing_on_the_gen_host_is_built_on_a_donor_copied_and_verified(self):
        miss = (3, "KIT-STORE FAIL KIT-STORE MISSING plan %s: absent on g1 and never stored here" % self.plan)
        mp, why, res = self.stage({"kit_snap": miss, "kit_snap_fetch": (0, "KW_SNAP_COPIED h2 12 KB\nKW_KIT_SNAP_VERIFY {}")})
        self.assertEqual(why, "")
        self.assertEqual([c[0] for c in self.calls], ["kit_snap", "kit_snap_donor", "kit_snap_fetch"])
        self.assertEqual(self.calls[1][1][:5], ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none"])
        self.assertEqual(self.calls[1][1][5], "h2")                        # first other die host
        fetch = self.calls[2][1][-1]
        self.assertIn("rsync -a --delete", fetch)
        self.assertIn(" verify ", fetch)                                   # sha256 re-check on the gen host before use
        self.assertEqual(res["kit_snap"]["copied_from"], "h2")

    def test_copy_that_does_not_verify_stops_the_item(self):
        miss = (3, "KIT-STORE FAIL KIT-STORE MISSING plan %s: absent" % self.plan)
        mp, why, _ = self.stage({"kit_snap": miss, "kit_snap_fetch": (3, "KIT-STORE FAIL KIT-SNAP VERIFY x: 1 file(s) differ from the manifest")})
        self.assertIsNone(mp)
        self.assertIn("did not verify", why)
        self.assertEqual(self.K.classify("kit_snap", why)[0], "FLOW")

    def test_input_on_no_host_is_kit_input_missing_named_and_never_infra(self):
        p = os.path.join(self.lane, "outline_blocked/asbuilt.json")        # words the PLAN rules key on
        miss = (3, "KIT-STORE FAIL KIT-STORE MISSING asbuilt %s: absent on x and never stored here" % p)
        mp, why, _ = self.stage({"kit_snap": miss, "kit_snap_donor": miss})
        self.assertIsNone(mp)
        self.assertEqual([c[0] for c in self.calls], ["kit_snap", "kit_snap_donor", "kit_snap_donor"])
        cls, reason = self.K.classify("kit_snap", why)
        self.assertEqual(cls, "FLOW")
        self.assertIn("KIT_INPUT_MISSING", reason)
        self.assertIn(p, why)
        self.assertIn("g1, h2, h3", why)

    def test_unreachable_donor_is_not_a_missing_input_verdict(self):
        miss = (3, "KIT-STORE FAIL KIT-STORE MISSING plan %s: absent" % self.plan)
        mp, why, _ = self.stage({"kit_snap": miss, "kit_snap_donor": (255, "ssh: connect to host h2 port 22: Connection refused")})
        self.assertIsNone(mp)
        self.assertNotIn("KIT_INPUT_MISSING", why)
        self.assertEqual(self.K.classify("kit_snap", why)[0], "INFRA")

    def test_flag_off_spec_has_no_snapshot_key(self):
        src = (HERE / "kit_wave.py").read_text()
        self.assertIn('| ({"kit_snap": True} if kit_snap_on(cfg, die, item) else {})', src)
        self.assertIn('snap_on = bool(sp.get("kit_snap")) and kit_store_applies(sp)', src)


if __name__ == "__main__":
    unittest.main()
