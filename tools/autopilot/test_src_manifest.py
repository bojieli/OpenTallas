"""SRC-TREE-1115: die src tree = main sha + overlay manifest; read-only publish; kit gen refuses a drifted tree."""
import json, os, shutil, stat, subprocess, tempfile, unittest
import src_manifest as SM
import kit_wave as KW


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), check=True,
                          capture_output=True, text=True).stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.addCleanup(self._rm)
        self.repo = os.path.join(self.t, "repo")
        os.makedirs(self.repo + "/tools/die_plan")
        git(self.repo, "init", "-q")
        for f, c in (("tools/die_plan/a.py", "A=1\n"), ("tools/die_plan/b.py", "B=1\n"), ("tools/x.sh", "echo x\n")):
            open(os.path.join(self.repo, f), "w").write(c)
        git(self.repo, "add", "tools")
        git(self.repo, "commit", "-qm", "m")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        os.makedirs(self.t + "/ov")
        open(self.t + "/ov/b.py", "w").write("B=2\n")
        open(self.t + "/ov/new.json", "w").write("{}\n")
        self.ovj = self.t + "/ov/overlay.json"
        json.dump({"files": {"tools/die_plan/b.py": {"from": "b.py", "sha256": SM.sha256_file(self.t + "/ov/b.py")},
                             "tools/die_plan/new.json": {"from": "new.json", "sha256": SM.sha256_file(self.t + "/ov/new.json")}}},
                  open(self.ovj, "w"))
        SM.CACHE_DIR = self.t + "/cache"
        self.out = self.t + "/tree1"

    def _rm(self):
        for dp, dn, fn in os.walk(self.t):
            os.chmod(dp, 0o755)
        shutil.rmtree(self.t, ignore_errors=True)

    def allow(self, hours=6):
        import datetime
        f = self.t + "/allow.json"
        exp = (datetime.datetime.now() + datetime.timedelta(hours=hours)).isoformat()
        json.dump({"kv": {"tools/die_plan/*": {"branch_sha": "abc", "expires": exp, "why": "test"}}}, open(f, "w"))
        return f

    def build(self):
        # these fixtures overlay tools/ files: legal only with a live allowlist entry (TOOLS-CONVERGE-1115)
        return SM.build(self.repo, self.sha, self.ovj, ["tools"], self.out, die="kv", allow_file=self.allow(), main_ref="")


class Build(Base):
    def test_build_verify_and_content(self):
        m = self.build()
        self.assertEqual(open(self.out + "/tools/die_plan/b.py").read(), "B=2\n")     # overlay wins
        self.assertEqual(open(self.out + "/tools/die_plan/a.py").read(), "A=1\n")     # main
        self.assertEqual(m["main_sha"], self.sha)
        self.assertEqual(open(self.out + "/" + SM.HASHFILE).read().strip(), m["manifest_hash"])
        self.assertEqual(SM.verify(self.out, expect=m["manifest_hash"])[0], [])

    def test_overlay_sha_mismatch_refused_before_copy(self):
        open(self.t + "/ov/b.py", "w").write("B=3\n")                                  # source changed after declaration
        with self.assertRaises(SystemExit) as c:
            self.build()
        self.assertIn("sha256", str(c.exception))
        self.assertFalse(os.path.exists(self.out))

    def test_no_rebuild_in_place(self):
        self.build()
        with self.assertRaises(SystemExit):
            self.build()

    def test_files_are_fresh_inodes_not_links(self):
        src = self.t + "/ov/b.py"
        self.build()
        self.assertNotEqual(os.stat(src).st_ino, os.stat(self.out + "/tools/die_plan/b.py").st_ino)
        self.assertEqual(os.stat(self.out + "/tools/die_plan/b.py").st_nlink, 1)


class ToolOverlayRule(Base):
    def test_tool_overlay_refused_without_allowlist(self):
        with self.assertRaises(SystemExit) as c:
            SM.build(self.repo, self.sha, self.ovj, ["tools"], self.out, die="kv", main_ref="")
        self.assertIn("is a TOOL", str(c.exception))
        self.assertFalse(os.path.exists(self.out))

    def test_allowlist_wrong_die_or_over_12h_or_no_branch_refused(self):
        for die, hours in (("s81", 6), ("kv", 20), ("kv", -1)):
            with self.assertRaises(SystemExit, msg=(die, hours)):
                SM.build(self.repo, self.sha, self.ovj, ["tools"], self.out, die=die, allow_file=self.allow(hours), main_ref="")

    def test_data_overlay_is_fine(self):
        json.dump({"files": {"physical/die_plan/kv/plan.json": {"from": "new.json", "sha256": SM.sha256_file(self.t + "/ov/new.json")}}},
                  open(self.ovj, "w"))
        m = SM.build(self.repo, self.sha, self.ovj, ["tools", "physical"], self.out, die="kv", main_ref="")
        self.assertIn("physical/die_plan/kv/plan.json", m["files"])

    def test_pin_must_be_ancestor_of_main(self):
        git(self.repo, "checkout", "-q", "-b", "lane")
        open(self.repo + "/tools/die_plan/a.py", "w").write("A=2\n")
        git(self.repo, "commit", "-qam", "lane")
        lane = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "branch", "-f", "origin_main", self.sha)
        with self.assertRaises(SystemExit) as c:
            SM.build(self.repo, lane, None, ["tools"], self.out, main_ref="origin_main")
        self.assertIn("not an ancestor", str(c.exception))
        SM.build(self.repo, self.sha, None, ["tools"], self.out, main_ref="origin_main")

    def test_rt_tree_must_exist(self):
        with self.assertRaises(SystemExit) as c:
            SM.build(self.repo, self.sha, None, ["tools"], self.out, main_ref="", rt_root=self.t + "/rt")
        self.assertIn("manifest.json", str(c.exception))


class Drift(Base):
    def test_names_modified_missing_extra(self):
        self.build()
        open(self.out + "/tools/die_plan/a.py", "a").write("A=9\n")                    # hand patch (class 5)
        os.unlink(self.out + "/tools/x.sh")
        open(self.out + "/tools/die_plan/stray.py", "w").write("\n")
        errs, _ = SM.verify(self.out, full=True)
        txt = "\n".join(errs)
        self.assertIn("tools/die_plan/a.py (modified", txt)
        self.assertIn("tools/x.sh (missing)", txt)
        self.assertIn("tools/die_plan/stray.py (extra", txt)

    def test_wrong_adopted_hash(self):
        self.build()
        errs, _ = SM.verify(self.out, expect="0" * 64)
        self.assertIn("is not the adopted", errs[0])

    def test_forged_manifest(self):
        self.build()
        mp = self.out + "/" + SM.MANIFEST
        m = json.load(open(mp))
        m["main_sha"] = "f" * 40
        json.dump(m, open(mp, "w"))
        self.assertIn("own hash", SM.verify(self.out, full=True)[0][0])

    def test_no_manifest(self):
        os.makedirs(self.t + "/plain")
        self.assertIn("SRC_MANIFEST MISSING", SM.verify(self.t + "/plain")[0][0])

    def test_cache_does_not_hide_edit(self):
        self.build()
        self.assertEqual(SM.verify(self.out)[0], [])
        self.assertTrue(SM.verify(self.out)[1].get("cached"))
        p = self.out + "/tools/die_plan/a.py"
        os.chmod(p, 0o644)
        open(p, "a").write("#\n")
        self.assertTrue(SM.verify(self.out)[0])


class Publish(Base):
    def test_publish_readonly_and_pointer_switch(self):
        self.build()
        ptr = self.t + "/current"
        SM.publish(self.out, ptr)
        self.assertEqual(os.path.realpath(ptr), os.path.realpath(self.out))
        with self.assertRaises(PermissionError) if os.geteuid() else self.assertRaises(AssertionError):
            if not os.geteuid():
                raise AssertionError                                                    # root bypasses modes
            open(self.out + "/tools/die_plan/a.py", "a").write("x")
        self.assertEqual(SM.verify(self.out, ro=True, full=True)[0], [])
        # second tree, pointer moves, first tree untouched
        out2 = self.t + "/tree2"
        SM.build(self.repo, self.sha, None, ["tools"], out2, main_ref="")
        SM.publish(out2, ptr)
        self.assertEqual(os.path.realpath(ptr), os.path.realpath(out2))
        self.assertEqual(SM.verify(self.out, ro=True, full=True)[0], [])

    def test_writable_file_is_drift_under_ro(self):
        self.build()
        errs, _ = SM.verify(self.out, ro=True, full=True)
        self.assertTrue(any("writable" in e for e in errs))

    def test_pointer_must_be_symlink(self):
        self.build()
        os.makedirs(self.t + "/real")
        with self.assertRaises(SystemExit):
            SM.publish(self.out, self.t + "/real")

    def test_hardlink_write_cannot_reach_tree(self):
        """class 4: a lane hardlinks (cp -al) a published tree and writes: the write fails at the read-only file"""
        if not os.geteuid():
            self.skipTest("root ignores file modes")
        self.build()
        SM.publish(self.out, "")
        link = self.t + "/lane"
        os.makedirs(link)
        os.link(self.out + "/tools/die_plan/a.py", link + "/a.py")
        with self.assertRaises(PermissionError):
            open(link + "/a.py", "a")


    def test_hardlinked_copy_is_drift_under_ro(self):
        self.build()
        SM.publish(self.out, "")
        os.makedirs(self.t + "/lane")
        os.link(self.out + "/tools/die_plan/a.py", self.t + "/lane/a.py")
        errs, _ = SM.verify(self.out, ro=True, full=True)
        self.assertTrue(any("tools/die_plan/a.py (hardlinked" in e for e in errs), errs)


class Derive(Base):
    def test_derive_lists_live_edits_with_sha(self):
        self.build()
        os.chmod(self.out + "/tools/die_plan/a.py", 0o644)
        open(self.out + "/tools/die_plan/a.py", "a").write("A=2\n")
        d = SM.derive(self.out, self.repo, self.sha, ["tools"])
        self.assertEqual(sorted(d["files"]), ["tools/die_plan/a.py", "tools/die_plan/b.py", "tools/die_plan/new.json"])
        self.assertEqual(d["files"]["tools/die_plan/new.json"]["main"], "absent")
        self.assertEqual(d["files"]["tools/die_plan/a.py"]["sha256"], SM.sha256_file(self.out + "/tools/die_plan/a.py"))


class KitWave(Base):
    def sp(self, **kw):
        return dict({"src": self.out, "src_sha": self.sha, "src_manifest": "verify", "src_manifest_hash": ""}, **kw)

    def test_cmd_modes(self):
        self.assertIsNone(KW.src_manifest_cmd(self.sp(src_manifest="off")))
        self.assertIsNone(KW.src_manifest_cmd(self.sp(src="rel/path")))
        c = KW.src_manifest_cmd(self.sp(src_manifest="require", src_manifest_hash="ab" * 32))
        self.assertIn("--ro", c)
        self.assertIn("--expect " + "ab" * 32, c)

    def test_old_spec_without_key_is_not_checked(self):
        self.assertIsNone(KW.src_manifest_cmd({"src": self.out}))

    def test_refusal_names_drifted_file(self):
        self.build()
        os.chmod(self.out + "/tools/die_plan/a.py", 0o644)
        open(self.out + "/tools/die_plan/a.py", "a").write("A=7\n")
        p = subprocess.run(KW.src_manifest_cmd(self.sp()), shell=True, capture_output=True, text=True)
        why, note = KW.src_manifest_verdict(self.sp(), p.returncode, p.stdout)
        self.assertTrue(why.startswith("SRC_MANIFEST FAIL"))
        self.assertIn("tools/die_plan/a.py", why)

    def test_clean_tree_passes(self):
        self.build()
        p = subprocess.run(KW.src_manifest_cmd(self.sp()), shell=True, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(KW.src_manifest_verdict(self.sp(), 0, p.stdout), ("", ""))

    def test_missing_manifest_policy(self):
        txt = "SRC_MANIFEST MISSING /x/.src-manifest.json (tree not built by src_manifest.py build)"
        self.assertEqual(KW.src_manifest_verdict(self.sp(), 1, txt)[0], "")          # verify mode: note only
        self.assertIn("no manifest", KW.src_manifest_verdict(self.sp(), 1, txt)[1])
        self.assertTrue(KW.src_manifest_verdict(self.sp(src_manifest="require"), 1, txt)[0])
        self.assertTrue(KW.src_manifest_verdict(self.sp(src_manifest_hash="a" * 64), 1, txt)[0])   # adopted hash pinned: required

    def test_spec_keys_do_not_change_input_hash(self):
        a = KW.input_hash(self.sp())
        b = KW.input_hash(self.sp(src_manifest="require", src_manifest_hash="c" * 64))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()


class AdoptGuard(Base):
    def test_manifest_check_blocks_before_any_copy(self):
        import adopt_guard as AG
        self.build()
        SM.publish(self.out, "")
        m = json.load(open(self.out + "/" + SM.MANIFEST))["manifest_hash"]
        cfg = {"dies": {"d": {"src": self.out, "src_manifest_hash": m}}}
        lines = []
        self.assertTrue(AG.manifest_check(cfg, "d", ["localhost"], log=lines.append))
        cfg["dies"]["d"]["src_manifest_hash"] = "0" * 64
        self.assertFalse(AG.manifest_check(cfg, "d", ["localhost"], log=lines.append))
        self.assertTrue(any("FAIL closed" in l for l in lines))
        cfg["dies"]["d"].pop("src_manifest_hash")
        self.assertTrue(AG.manifest_check(cfg, "d", ["localhost"], log=lines.append))        # no pin: not judged


class DefaultRequire(unittest.TestCase):
    """TOOLS-CONVERGE-1115 (r219): a tree without a manifest is refused unless the die opts down to verify"""
    def test_no_manifest_refused_by_default(self):
        sp = {"src": "/x/tree", "src_sha": "a" * 40}
        why, note = KW.src_manifest_verdict(sp, 1, "SRC_MANIFEST MISSING /x/tree/.src-manifest.json")
        self.assertIn("SRC_MANIFEST FAIL", why)
        why, note = KW.src_manifest_verdict(dict(sp, src_manifest="verify"), 1, "SRC_MANIFEST MISSING /x")
        self.assertEqual(why, "")

    def test_spec_default_is_require(self):
        cfg = {"dies": {"d": {"src": "/x", "src_sha": "a", "plan": "p", "gen_host": "h", "event": "e"}}}
        self.assertEqual(KW.opt_get(cfg, "d", "src_manifest") or "require", "require")


class SharedInodes(Base):
    def test_cp_al_copy_makes_tree_not_ready_and_is_named(self):
        self.build()
        SM.publish(self.out)
        self.assertEqual(SM.shared_inodes(self.out), [])
        self.assertEqual(SM.links_report(self.out)[0], [])
        other = self.t + "/lane_copy"
        os.makedirs(other + "/tools/die_plan")
        os.link(self.out + "/tools/die_plan/a.py", other + "/tools/die_plan/a.py")          # someone's cp -al
        bad = SM.shared_inodes(self.out)
        self.assertEqual([r for r, n in bad], ["tools/die_plan/a.py"])
        errs, n = SM.links_report(self.out, [other])
        self.assertEqual(n, 1)
        self.assertIn("also " + other + "/tools/die_plan/a.py", errs[0])
        v, _ = SM.verify(self.out, ro=True, full=True)
        self.assertIn("NOT-READY", v[0])
        self.assertTrue(any("tools/die_plan/a.py" in e for e in v))

    def test_publish_refuses_a_linked_tree(self):
        self.build()
        os.makedirs(self.t + "/lane_copy")
        os.link(self.out + "/tools/x.sh", self.t + "/lane_copy/x.sh")
        with self.assertRaises(SystemExit):
            SM.publish(self.out)

    def test_cli_links_exit_codes(self):
        self.build()
        self.assertEqual(SM.main(["links", self.out]), 0)
        os.makedirs(self.t + "/lc")
        os.link(self.out + "/tools/x.sh", self.t + "/lc/x.sh")
        self.assertEqual(SM.main(["links", self.out]), 1)


class Delta(Base):
    def test_delta_tree_equals_a_fresh_build_of_the_new_sha(self):
        old = self.t + "/old"
        m0 = SM.build(self.repo, self.sha, None, ["tools"], old, main_ref="")
        SM.publish(old)
        open(self.repo + "/tools/die_plan/a.py", "w").write("A=2\n")
        os.unlink(self.repo + "/tools/x.sh")
        open(self.repo + "/tools/die_plan/new.py", "w").write("N=1\n")
        git(self.repo, "add", "-A", "tools")
        git(self.repo, "commit", "-qm", "m2")
        sha2 = git(self.repo, "rev-parse", "HEAD")
        pack = self.t + "/pack"
        self.assertEqual(SM.delta_make(self.repo, old, sha2, pack), (2, 1))
        new = self.t + "/new"
        nm = SM.delta_apply(pack, old, new)
        fresh = self.t + "/fresh"
        fm = SM.build(self.repo, sha2, None, ["tools"], fresh, main_ref="")
        self.assertEqual(nm["files"], fm["files"])
        self.assertEqual(nm["manifest_hash"], fm["manifest_hash"])
        SM.publish(new)
        self.assertEqual(SM.verify(new, expect=fm["manifest_hash"], ro=True, full=True)[0], [])
        self.assertEqual(SM.shared_inodes(new), [])                      # real copy, not links
        self.assertEqual(open(old + "/tools/die_plan/a.py").read(), "A=1\n")   # the old tree is untouched

    def test_pack_for_another_tree_and_overlay_clash_refused(self):
        old = self.t + "/old"
        SM.build(self.repo, self.sha, None, ["tools"], old, main_ref="")
        other = self.t + "/other"
        SM.build(self.repo, self.sha, self.ovj, ["tools"], other, die="kv", allow_file=self.allow(), main_ref="")
        open(self.repo + "/tools/die_plan/b.py", "w").write("B=9\n")
        git(self.repo, "commit", "-qam", "m2")
        sha2 = git(self.repo, "rev-parse", "HEAD")
        with self.assertRaises(SystemExit) as c:
            SM.delta_make(self.repo, other, sha2, self.t + "/p2")                # b.py is overlaid in `other`
        self.assertIn("overlaid", str(c.exception))
        SM.delta_make(self.repo, old, sha2, self.t + "/p1")
        with self.assertRaises(SystemExit):
            SM.delta_apply(self.t + "/p1", other, self.t + "/n2")
