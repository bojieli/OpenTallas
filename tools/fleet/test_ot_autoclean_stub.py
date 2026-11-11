"""ot-autoclean class s: stub-trim of a SIGNED unit whose ARCHIVED.json is a verified copy on AGIdock (COORD 11-11, KW-FIX-46).
Deletes only files that are not the unit's own records / cited files, older than 12 h, after a receipt and marker; refuses on every
safety hold, including the 11-07 incidents (symlinked scratch2<->scratch3 aliases, protected rows, counted rows, live use).
    python3 -I tools/fleet/test_ot_autoclean_stub.py"""
import hashlib
import json
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_ot_autoclean_auto as T   # noqa: E402

ac = T.ac
OLD = time.time() - 30 * 3600   # class s needs every deleted file older than 12 h


def write(p, data="x" * 3000):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(data)
    os.utime(p, (OLD, OLD))
    return p


class Stub(T.Base):
    def unit(self, rel="lane/u1", archived=True, verify="OK files 5 sha256 all match", extra=None):
        u = os.path.join(self.root, rel)
        write(os.path.join(u, "signoff.json"), json.dumps({"verdict": "SIGNED"}))
        write(os.path.join(u, "PROVENANCE.json"), json.dumps({"verdict": "SIGNED"}))
        write(os.path.join(u, "6_final.odb"), "o" * 5000)
        write(os.path.join(u, "6_final.spef"), "s" * 5000)
        for n in (extra or ["junk/a.log", "junk/b.tcl", "run/big.dat", "results/x/y.odb", "logs/z.log"]):
            write(os.path.join(u, n))
        T.age_tree(u, OLD)
        if archived:
            self.archive(u, verify)
        return u

    def archive(self, u, verify="OK files 5 sha256 all match"):
        files = ac.unit_files(u, ac.dedupe_roots([self.root]))
        rec = {"schema": "opentallas.archived.v2", "archive": "/archive/opentallas-signed-1106/hx" + u, "verify": verify,
               "nfiles": len(files), "bytes": sum(s for _, s, _ in files),
               "files": [{"path": p, "size": s, "mtime": m, "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
                         for p, s, m in files]}
        with open(os.path.join(u, "ARCHIVED.json"), "w") as f:
            json.dump(rec, f)
        os.utime(os.path.join(u, "ARCHIVED.json"), (OLD, OLD))

    def s(self, *extra, apply=True):
        return self.run_job("--classes", "s", *extra, apply=apply)

    def test_default_classes_never_stub(self):
        u = self.unit()
        self.assertEqual(self.run_job(), 0)
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_stubs_a_verified_unit_and_keeps_records(self):
        u = self.unit()
        self.assertEqual(self.s(), 0)
        # kept: the records, the final views, the archived tree (junk/ is in ARCHIVED.json), the marker pair
        for kept in ("signoff.json", "PROVENANCE.json", "6_final.odb", "6_final.spef", "ARCHIVED.json", "STUBBED.json",
                     "junk/a.log", "junk/b.tcl"):
            self.assertTrue(os.path.exists(os.path.join(u, kept)), kept)
        # deleted: the heavy run trees that the archive does not copy
        for gone in ("run/big.dat", "results/x/y.odb", "logs/z.log"):
            self.assertFalse(os.path.exists(os.path.join(u, gone)), gone)
        r = self.row(u)
        self.assertEqual(r[2:4], ["s", "STUBBED"])
        self.assertEqual(len(os.listdir(os.path.join(self.state, "stub-receipts"))), 1)

    def test_dry_run_deletes_nothing(self):
        u = self.unit()
        self.s(apply=False)
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))
        self.assertEqual(self.row(u)[3], "WOULD")

    def test_no_archived_json_is_untouched(self):
        u = self.unit(archived=False)
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_unverified_archive_is_untouched(self):
        u = self.unit(verify="FAIL hash mismatch")
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))
        self.assertEqual(self.row(u)[3], "SKIP")

    def test_unit_changed_since_archive_is_untouched(self):
        u = self.unit()
        write(os.path.join(u, "junk/new_after_archive.log"))
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_young_file_blocks_the_whole_unit(self):
        u = self.unit()
        young = os.path.join(u, "run/big.dat")
        os.utime(young, (time.time(), time.time()))
        self.archive(u)
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "junk/b.tcl")))

    def test_protected_unit_is_untouched(self):
        u = self.unit()
        self.prot.append((u, "lanes/PROTECTED-DBS.txt"))
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_protected_file_inside_is_kept_others_go(self):
        u = self.unit()
        keep = os.path.join(u, "run/big.dat")
        self.prot.append((keep, "lanes/PROTECTED-DBS.txt"))
        self.s("--stub-protected-units")
        self.assertTrue(os.path.exists(keep))

    def test_kitwave_keep_unit_is_untouched(self):
        u = self.unit()
        self.kw = {"attempts": {}, "latest": {}, "keep": ["hx:" + u], "current_di": {}}
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_symlink_inside_is_not_followed_or_removed(self):
        u = self.unit()
        outside = write(os.path.join(self.t, "outside/precious.dat"))
        os.symlink(os.path.dirname(outside), os.path.join(u, "junk/link"))
        self.archive(u)
        self.s()
        self.assertTrue(os.path.exists(outside))
        self.assertTrue(os.path.islink(os.path.join(u, "junk/link")))

    def test_protected_row_given_through_a_symlink_alias_still_protects(self):
        # 11-07 incident: scratch2 <-> scratch3 symlinks hid kept attempts from path-string checks; protection must be by realpath
        u = self.unit()
        alias = os.path.join(self.t, "alias_lane")
        os.symlink(os.path.dirname(u), alias)
        self.prot.append((os.path.join(alias, os.path.basename(u)), "lanes/PROTECTED-DBS.txt"))
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_root_reached_through_an_alias_is_stubbed_at_its_real_path_only(self):
        u = self.unit()
        alias = os.path.join(self.t, "aliasroot")
        os.symlink(self.root, alias)
        outside = write(os.path.join(self.t, "outside/precious.dat"))
        self.root = alias
        self.s()
        self.assertTrue(os.path.exists(outside))
        self.assertTrue(os.path.exists(os.path.join(u, "signoff.json")))
        self.assertTrue(os.path.islink(alias))

    def test_hardlinked_file_is_kept(self):
        u = self.unit()
        os.link(os.path.join(u, "run/big.dat"), os.path.join(self.t, "hl.log"))
        self.archive(u)
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_git_checkout_unit_is_untouched(self):
        u = self.unit("lane/gitwt/u1")
        os.makedirs(os.path.join(self.root, "lane/gitwt/.git"))
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_live_use_blocks(self):
        u = self.unit()
        self.spawn(["sleep", "30"], cwd=u)
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "run/big.dat")))

    def test_second_run_is_idempotent(self):
        u = self.unit()
        self.s()
        self.s()
        self.assertTrue(os.path.exists(os.path.join(u, "signoff.json")))


if __name__ == "__main__":
    unittest.main()
