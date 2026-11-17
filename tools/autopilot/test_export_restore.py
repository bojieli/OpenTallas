import hashlib, json, os, shutil, tempfile, unittest
import export_restore as E


def mk_export():
    r = tempfile.mkdtemp(); e = r + "/s81/elemA"; os.makedirs(e)
    odb = b"ODBDATA"; open(e + "/6_final.odb", "wb").write(odb)
    so = b'{"verdict": "SIGNED"}\n'; open(e + "/signoff.json", "wb").write(so)
    rid = hashlib.sha256(so).hexdigest()
    open(r + "/INDEX.tsv", "w").write("die\telement\tkind\trecord\tdb\trtx_db\tsize\tsha256\n" +
        "s81\telemA\tt\t%s\t/archive/opentallas-signed-1114/s81/elemA/6_final.odb\t-\t7\t%s\n" % (rid, hashlib.sha256(odb).hexdigest()))
    return r, rid


class Restore(unittest.TestCase):
    def setUp(self):
        self.root, self.rid = mk_export(); self.t = tempfile.mkdtemp()
        self.prov = {"export": {"signoff_sha256": self.rid, "odb": "/x/arch/elemA/xbase/6_final.odb", "signoff": "/x/arch/elemA/signoff/signoff.json", "base": "/x/arch/elemA/xbase"}}

    def run_(self, paths, fetch=None):
        rows = E.load_index(self.root)
        items, bad = E.plan([(p, "by.json") for p in paths], lambda b: self.prov, rows, self.root)
        tmp = tempfile.mkdtemp()
        return E.restore([(self.t + i[0], *i[1:]) for i in items], fetch or (lambda s, d: shutil.copyfile(s, d)), tmp), bad

    def test_odb_signoff_and_dir_are_restored_with_the_hash_checked(self):
        (done, fail), bad = self.run_(["/x/arch/elemA/xbase/6_final.odb", "/x/arch/elemA/signoff/signoff.json", "/x/arch/elemA/xbase"])
        self.assertEqual((len(done), fail, bad), (3, [], []))
        self.assertEqual(open(self.t + "/x/arch/elemA/xbase/6_final.odb", "rb").read(), b"ODBDATA")

    def test_a_corrupt_export_file_is_never_placed(self):
        def evil(s, d): open(d, "wb").write(b"CORRUPT")
        (done, fail), _ = self.run_(["/x/arch/elemA/xbase/6_final.odb"], evil)
        self.assertEqual(done, []); self.assertIn("does not match the signed record", fail[0][1])
        self.assertFalse(os.path.exists(self.t + "/x/arch/elemA/xbase/6_final.odb"))

    def test_unknown_record_and_foreign_paths_are_reported_not_invented(self):
        self.prov["export"]["signoff_sha256"] = "f" * 64
        _, bad = self.run_(["/x/arch/elemA/xbase/6_final.odb"]); self.assertIn("no signed export row", bad[0][1])
        self.prov["export"]["signoff_sha256"] = self.rid
        _, bad = self.run_(["/somewhere/else.json"]); self.assertIn("not an export/* path", bad[0][1])


class WaveHook(unittest.TestCase):
    def test_signed_export_restore_places_the_verified_file_on_the_gen_host(self):
        import kit_wave as KW
        root, rid = mk_export(); t = tempfile.mkdtemp(); target = t + "/orig/xbase/6_final.odb"
        prov = {"export": {"signoff_sha256": rid, "odb": target}}
        def run(name, argv, idempotent=False):
            return 0, json.dumps(prov)
        placed = KW.signed_export_restore({"root": root, "ssh": ""}, [{"path": target, "by": "by.json"}], run, lambda c: c, "localhost", E)
        self.assertEqual(placed, [target]); self.assertEqual(open(target, "rb").read(), b"ODBDATA")

    def test_without_the_option_the_stage_is_off(self):
        import kit_wave as KW, inspect
        self.assertIn('sp.get("signed_export")', inspect.getsource(KW.kit_snap_stage))
