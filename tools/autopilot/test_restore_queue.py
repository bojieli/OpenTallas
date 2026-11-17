import hashlib, json, os, tempfile, unittest
import export_restore as E
from test_export_restore import mk_export


class Queue(unittest.TestCase):
    def setUp(self):
        self.root, self.rid = mk_export(); self.t = tempfile.mkdtemp(); self.q = self.t + "/restore_needed.jsonl"
        self.prov = {"kit": {"module": "elemA"}, "export": {"signoff_sha256": self.rid, "odb": "/x/xbase/6_final.odb", "signoff": "/x/signoff/signoff.json", "base": "/x/xbase"}}

    def rows(self, paths, host="epyc10"):
        return E.restore_rows([(p, "by.json") for p in paths], lambda b: self.prov, host, now=1.0)

    def test_rows_carry_module_record_path_host_and_skip_foreign_paths(self):
        rows = self.rows(["/x/xbase/6_final.odb", "/not/an/export/path"])
        self.assertEqual([(r["module"], r["key"], r["host"], r["status"]) for r in rows], [("elemA", "odb", "epyc10", "NEEDED")])

    def test_queue_append_dedups_per_host_and_path_and_skips_done(self):
        r = self.rows(["/x/xbase/6_final.odb"])
        self.assertEqual(E.queue_append(self.q, r), 1); self.assertEqual(E.queue_append(self.q, r), 0)
        self.assertEqual(E.queue_append(self.q, self.rows(["/x/xbase/6_final.odb"], "epyc8")), 1)           # another host is another request
        self.assertEqual(E.queue_append(self.q, self.rows(["/x/signoff/signoff.json"]), done=[dict(r[0], status="DONE")]), 1)
        self.assertEqual(len(E.read_jsonl(self.q)), 3)

    def test_worker_pushes_verified_files_marks_done_and_is_idempotent(self):
        rows = self.rows(["/x/xbase/6_final.odb", "/x/signoff/signoff.json", "/x/xbase"]); pushed = []
        done = E.work(rows, [], E.load_index(self.root), self.root, lambda h, s, d: pushed.append((h, s and os.path.basename(s), d)))
        self.assertEqual(sorted(r["status"] for r in done), ["DONE"] * 3)
        self.assertIn(("epyc10", "6_final.odb", "/x/xbase/6_final.odb"), pushed); self.assertIn(("epyc10", None, "/x/xbase"), pushed)
        self.assertEqual(E.work(rows, done, E.load_index(self.root), self.root, lambda *a: pushed.append(a)), [])        # nothing pending twice

    def test_a_corrupt_export_file_is_never_pushed_and_an_unknown_record_is_unrestorable(self):
        rows = self.rows(["/x/xbase/6_final.odb"]); pushed = []
        open(self.root + "/s81/elemA/6_final.odb", "wb").write(b"CORRUPT")
        done = E.work(rows, [], E.load_index(self.root), self.root, lambda *a: pushed.append(a))
        self.assertEqual((pushed, done[0]["status"]), ([], "UNRESTORABLE")); self.assertIn("does not match", done[0]["why"])
        rows[0]["record"] = "f" * 64
        self.assertIn("no signed export row", E.work(rows, [], E.load_index(self.root), self.root, lambda *a: 0)[0]["why"])

    def test_a_down_host_stays_pending(self):
        rows = self.rows(["/x/xbase/6_final.odb"])
        def push(h, s, d): raise OSError("host down")
        self.assertEqual(E.work(rows, [], E.load_index(self.root), self.root, push), [])
