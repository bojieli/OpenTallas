"""STAGE A: D-step as hardlinks of the published base + the delta (COORD 11-17 safeguards)."""
import json, os, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

import src_manifest as SM

HERE = os.path.dirname(os.path.abspath(__file__))


def mk_base(root, files):
    os.makedirs(root)
    m = {}
    for rel, txt in files.items():
        p = os.path.join(root, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(txt); m[rel] = SM.sha256_file(p)
    nm = {"version": 1, "main_sha": "a" * 40, "scope": ["tools"], "overlay": {}, "files": m}
    nm["manifest_hash"] = SM.manifest_hash(nm)
    json.dump(nm, open(os.path.join(root, SM.MANIFEST), "w"), sort_keys=True); open(os.path.join(root, SM.HASHFILE), "w").write(nm["manifest_hash"] + "\n")
    SM.make_ro(root)
    return nm


def mk_pack(d, base_hash, add, delete=()):
    os.makedirs(os.path.join(d, "files"))
    ent = {}
    for rel, txt in add.items():
        p = os.path.join(d, "files", rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(txt)
        ent[rel] = {"sha256": SM.sha256_file(p), "exec": False}
    json.dump({"old_manifest_hash": base_hash, "new_main": "b" * 40, "add": ent, "delete": list(delete), "overlay_add": {}, "overlay_drop": []}, open(os.path.join(d, "delta.json"), "w"))


class Link(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(); self.addCleanup(lambda: (subprocess.run(["find", self.t, "-type", "d", "-exec", "chmod", "u+w", "{}", "+"]), shutil.rmtree(self.t, ignore_errors=True)))
        cache = patch.object(SM, "CACHE_DIR", self.t + "/cache")
        cache.start()
        self.addCleanup(cache.stop)
        self.base = self.t + "/base"
        self.bm = mk_base(self.base, {"tools/a.py": "A=1\n", "tools/b.py": "B=1\n", "tools/c.py": "C=1\n"})

    def apply(self, **kw):
        mk_pack(self.t + "/pack", self.bm["manifest_hash"], {"tools/b.py": "B=2\n", "tools/new.py": "N=1\n"}, ["tools/c.py"])
        return SM.delta_apply(self.t + "/pack", self.base, self.t + "/d1", link=True, **kw)

    def test_unchanged_files_are_links_changed_files_are_fresh_and_base_is_untouched(self):
        nm = self.apply()
        a_base, a_new = os.lstat(self.base + "/tools/a.py"), os.lstat(self.t + "/d1/tools/a.py")
        self.assertEqual(a_base.st_ino, a_new.st_ino); self.assertEqual(a_base.st_nlink, 2)
        self.assertNotEqual(os.lstat(self.base + "/tools/b.py").st_ino, os.lstat(self.t + "/d1/tools/b.py").st_ino)
        self.assertEqual(open(self.base + "/tools/b.py").read(), "B=1\n"); self.assertTrue(os.path.exists(self.base + "/tools/c.py"))
        self.assertEqual(stat.S_IMODE(os.lstat(self.base + "/tools/b.py").st_mode), 0o444)      # (1) base stays a-w
        self.assertEqual(open(self.t + "/d1/" + SM.LINKBASE).read().strip(), os.path.realpath(self.base))
        self.assertEqual(SM.verify(self.t + "/d1", expect=nm["manifest_hash"], full=True)[0], [])

    def test_published_link_tree_passes_ro_verify_and_a_foreign_link_still_fails(self):
        nm = self.apply(); SM.publish(self.t + "/d1")                                           # (1) a-w files and dirs at publish
        self.assertEqual(SM.verify(self.t + "/d1", expect=nm["manifest_hash"], ro=True, full=True)[0], [])
        self.assertEqual(SM.shared_inodes(self.t + "/d1"), [])
        os.link(self.t + "/d1/tools/new.py", self.t + "/stray_copy.py")                         # a cp -al copy of a file THIS tree owns is still a violation
        self.assertTrue(any("NOT-READY" in e for e in SM.verify(self.t + "/d1", ro=True, full=True)[0]))
        self.assertEqual(SM.shared_inodes(self.t + "/d1"), [("tools/new.py", 2)])

    def test_expect_mismatch_is_refused_and_leaves_no_tree(self):
        with self.assertRaises(SystemExit):
            self.apply(expect="0" * 64)
        self.assertFalse(os.path.exists(self.t + "/d1")); self.assertFalse(os.path.exists(self.t + "/d1.building"))
        self.assertEqual(oct(stat.S_IMODE(os.lstat(self.base + "/tools/a.py").st_mode)), oct(0o444))

    def test_link_delta_reuses_exact_receipt_over_inherited_snapshot_metadata(self):
        base = Path(self.base)
        base.chmod(0o755)
        (base / SM.SNAPDELTA).write_text(json.dumps({"parent_manifest_hash": "0" * 64, "changed": []}))
        SM.make_ro(self.base)
        self.assertEqual(SM.verify(self.base, ro=True, full=True)[0], [])
        with patch.object(SM, "sha256_file", wraps=SM.sha256_file) as hashed:
            self.apply()
        building = Path(self.t) / "d1.building"
        self.assertEqual(
            {Path(call.args[0]).relative_to(building).as_posix() for call in hashed.call_args_list
             if Path(call.args[0]).is_relative_to(building)},
            {"tools/b.py", "tools/new.py"},
        )
        errors, info = SM.verify(self.t + "/d1", full=True)
        self.assertEqual(errors, [])
        self.assertEqual(info["inherited_from"], self.base)

    def test_same_inode_cannot_satisfy_a_different_advertised_digest(self):
        self.assertEqual(SM.verify(self.base, ro=True, full=True)[0], [])
        manifest = self.apply()
        child = Path(self.t) / "d1"
        manifest["files"]["tools/a.py"] = manifest["files"]["tools/b.py"]
        manifest["manifest_hash"] = SM.manifest_hash(manifest)
        (child / SM.MANIFEST).write_text(json.dumps(manifest))
        (child / SM.HASHFILE).write_text(manifest["manifest_hash"] + "\n")
        errors, info = SM.verify(str(child), expect=manifest["manifest_hash"], full=True)
        self.assertEqual(info["inherited_from"], self.base)
        self.assertEqual(errors, ["SRC_MANIFEST DRIFT tools/a.py (modified: not the manifest content)"])

    def test_fresh_inode_is_hashed_even_when_digest_matches_parent(self):
        self.assertEqual(SM.verify(self.base, ro=True, full=True)[0], [])
        self.apply()
        child = Path(self.t) / "d1"
        payload = child / "tools/a.py"
        payload.unlink()
        payload.write_text("A=1\n")
        payload.chmod(0o444)
        with patch.object(SM, "sha256_file", wraps=SM.sha256_file) as hashed:
            errors, _info = SM.verify(str(child), full=True)
        self.assertEqual(errors, [])
        self.assertIn(str(payload), [call.args[0] for call in hashed.call_args_list])

    def test_retiring_the_delta_never_changes_the_bases_file_modes(self):                       # (2)
        self.apply(); SM.publish(self.t + "/d1")
        before = {r: (stat.S_IMODE(os.lstat(os.path.join(self.base, r)).st_mode), os.lstat(os.path.join(self.base, r)).st_ino) for r in ("tools/a.py", "tools/b.py", "tools/c.py")}
        ot_delete = os.path.join(HERE, "..", "fleet", "ot-delete")
        spec = __import__("importlib.util").util.spec_from_loader("od", __import__("importlib.machinery").machinery.SourceFileLoader("od", ot_delete))
        od = __import__("importlib.util").util.module_from_spec(spec); spec.loader.exec_module(od)
        class G:
            def refuse(self, t, protected=None): return None
        self.assertEqual(od.main([self.t + "/d1"], guard=G()), 0)
        self.assertFalse(os.path.exists(self.t + "/d1"))
        after = {r: (stat.S_IMODE(os.lstat(os.path.join(self.base, r)).st_mode), os.lstat(os.path.join(self.base, r)).st_ino) for r in before}
        self.assertEqual(before, after); self.assertEqual(before["tools/a.py"][0], 0o444)
        self.assertEqual(os.lstat(self.base + "/tools/a.py").st_nlink, 1)
        self.assertEqual(SM.verify(self.base, ro=True, full=True)[0], [])

    def test_no_retire_path_chmods_files(self):
        import re
        for rel in ("autopilot/retire_superseded.py", "fleet/ot_disk_autoprune.py", "fleet/auto_retire.py", "fleet/ot-delete", "fleet/ot-tools-sync"):
            txt = open(os.path.join(HERE, "..", rel)).read()
            self.assertIsNone(re.search(r"chmod[\"', ]+-R[\"', ]+u\+w", txt), rel)                         # no recursive chmod (it reaches shared file inodes)
