"""TOOLS-DECOUPLE phase 2: live_tree.py (one live tree per die, rename-only writes, hardlink snapshots from unpublished staging)."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import live_tree as LT  # noqa: E402
import src_manifest as SM  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make_published(root, files):
    os.makedirs(root)
    for p, b in files.items():
        q = os.path.join(root, p)
        os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "wb").write(b)
    m = {"version": 1, "main_sha": "a" * 40, "scope": ["tools", "physical"], "overlay": {},
         "files": {p: sha(b) for p, b in files.items()}}
    m["manifest_hash"] = SM.manifest_hash(m)
    json.dump(m, open(os.path.join(root, SM.MANIFEST), "w"))
    open(os.path.join(root, SM.HASHFILE), "w").write(m["manifest_hash"] + "\n")
    SM.make_ro(root)
    return m["manifest_hash"]


def make_pack(d, old_hash, add, delete=()):
    os.makedirs(os.path.join(d, "files"))
    for p, b in add.items():
        q = os.path.join(d, "files", p)
        os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "wb").write(b)
    json.dump({"old_manifest_hash": old_hash, "new_main": "b" * 40, "add": {p: {"sha256": sha(b), "exec": False} for p, b in add.items()},
               "delete": list(delete)}, open(os.path.join(d, "delta.json"), "w"))


def chmod_all_w(root):
    for dp, dn, fn in os.walk(root):
        os.chmod(dp, 0o755)


class LiveTree(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.pub = os.path.join(self.t, "src_x_r1")
        self.h0 = make_published(self.pub, {"tools/a.py": b"A1", "physical/plan.json": b"P1", "physical/keep.v": b"K"})
        self.live = LT.live_path("d", self.t)
        self.snaps = LT.snap_root("d", self.t)

    def tearDown(self):
        chmod_all_w(self.t)
        subprocess.run(["rm", "-rf", self.t])

    def test_seed_is_real_copy_and_snapshot_verifies(self):
        LT.host_seed(self.pub, self.live)
        a = os.path.join(self.live, "physical/plan.json")
        self.assertNotEqual(os.stat(a).st_ino, os.stat(os.path.join(self.pub, "physical/plan.json")).st_ino)   # never shares a published tree
        self.assertFalse(os.stat(a).st_mode & 0o222)
        LT.host_apply(self.live, "", self.snaps, "s0")
        s0 = os.path.join(self.snaps, "s0")
        self.assertEqual(os.stat(os.path.join(s0, "physical/plan.json")).st_ino, os.stat(a).st_ino)            # hardlink snapshot
        errs, info = SM.verify(s0, expect=self.h0, ro=True, full=True)
        self.assertEqual(errs, [])

    def test_apply_is_rename_only_and_old_snapshot_unchanged(self):
        LT.host_seed(self.pub, self.live)
        LT.host_apply(self.live, "", self.snaps, "s0")
        pk = os.path.join(self.t, "pk")
        make_pack(pk, self.h0, {"physical/plan.json": b"P2", "physical/new.v": b"N"}, delete=["physical/keep.v"])
        LT.host_apply(self.live, pk, self.snaps, "s1")
        s0, s1 = os.path.join(self.snaps, "s0"), os.path.join(self.snaps, "s1")
        self.assertEqual(open(os.path.join(s0, "physical/plan.json"), "rb").read(), b"P1")
        self.assertTrue(os.path.exists(os.path.join(s0, "physical/keep.v")))
        self.assertEqual(open(os.path.join(s1, "physical/plan.json"), "rb").read(), b"P2")
        self.assertFalse(os.path.exists(os.path.join(s1, "physical/keep.v")))
        self.assertEqual(os.stat(os.path.join(s0, "tools/a.py")).st_ino, os.stat(os.path.join(s1, "tools/a.py")).st_ino)
        e0, _ = SM.verify(s0, expect=self.h0, ro=True, full=True)
        m1 = json.load(open(os.path.join(s1, SM.MANIFEST)))
        e1, _ = SM.verify(s1, expect=m1["manifest_hash"], ro=True, full=True)
        self.assertEqual((e0, e1), ([], []))
        self.assertNotEqual(m1["manifest_hash"], self.h0)
        with self.assertRaises(PermissionError):                                       # an in-place write through a shared inode fails
            open(os.path.join(self.live, "tools/a.py"), "wb")

    def test_pack_for_other_tree_refused(self):
        LT.host_seed(self.pub, self.live)
        pk = os.path.join(self.t, "pk")
        make_pack(pk, "f" * 64, {"physical/plan.json": b"P2"})
        with self.assertRaises(SystemExit):
            LT.host_apply(self.live, pk, self.snaps, "s1")

    def test_bad_pack_file_refused(self):
        LT.host_seed(self.pub, self.live)
        pk = os.path.join(self.t, "pk")
        make_pack(pk, self.h0, {"physical/plan.json": b"P2"})
        os.chmod(os.path.join(pk, "files/physical/plan.json"), 0o644)
        open(os.path.join(pk, "files/physical/plan.json"), "wb").write(b"XX")
        with self.assertRaises(SystemExit):
            LT.host_apply(self.live, pk, self.snaps, "s1")

    def test_plain_published_cp_al_still_flagged(self):
        """a cp -al copy of a published tree (no .snap-group) is still NOT-READY"""
        cp = os.path.join(self.t, "copy")
        subprocess.run(["cp", "-al", self.pub, cp], check=True)
        errs, _ = SM.verify(self.pub, ro=True, full=True)
        self.assertTrue(any("NOT-READY" in e for e in errs))

    def test_reloc_pack_rewrites_self_paths_and_digest(self):
        LT.host_seed(self.pub, self.live)
        pk = os.path.join(self.t, "rp")
        os.chmod(self.live + "/physical", 0o755)
        LT.write_new(os.path.join(self.live, "physical/plan.json"), json.dumps({"f": self.pub + "/physical/keep.v"}))
        LT.write_new(os.path.join(self.live, "physical/source_sidecar.json"), "{}")
        LT.write_new(os.path.join(self.live, "physical/wave_prepare.json"), "{}")
        m = json.load(open(os.path.join(self.live, SM.MANIFEST)))
        for r in ("physical/plan.json", "physical/source_sidecar.json", "physical/wave_prepare.json"):
            m["files"][r] = LT.sha256_file(os.path.join(self.live, r))
        m["manifest_hash"] = SM.manifest_hash(m)
        LT.write_new(os.path.join(self.live, SM.MANIFEST), json.dumps(m))
        new = os.path.join(self.snaps, "s1")
        add = LT.reloc_pack(self.live, self.pub, new, ["physical/plan.json"], pk, "physical/plan.json:physical/wave_prepare.json")
        LT.host_apply(self.live, pk, self.snaps, "s1")
        self.assertEqual(json.load(open(os.path.join(new, "physical/plan.json")))["f"], new + "/physical/keep.v")
        w = json.load(open(os.path.join(new, "physical/wave_prepare.json")))
        self.assertEqual(w["prepared_plan_sha256"], add["physical/plan.json"]["sha256"])
        m1 = json.load(open(os.path.join(new, SM.MANIFEST)))
        self.assertEqual(SM.verify(new, expect=m1["manifest_hash"], ro=True, full=True)[0], [])

    def test_rewrite_candidate(self):
        old = {"tree": "/k/src_r3c", "manifest_hash": "x", "src_manifest_sha": "x", "plan": "/k/src_r3c/physical/p.json",
               "config": {"event": "e3", "gen_args": ["--c", "/k/src_r3c/s.json"], "gen_hosts": ["h1", "h2"], "gen_host": "h1"}}
        c = LT.rewrite_candidate(old, "/k/src_r3c", "/k/snap_d/s1", "H", "e4")
        self.assertEqual((c["tree"], c["plan"], c["config"]["gen_args"][1], c["manifest_hash"], c["config"]["event"]),
                         ("/k/snap_d/s1", "/k/snap_d/s1/physical/p.json", "/k/snap_d/s1/s.json", "H", "e4"))


if __name__ == "__main__":
    unittest.main()
